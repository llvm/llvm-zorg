import dataclasses
import datetime
import logging
import os
import git
from google.cloud import bigquery
import requests

GRAFANA_URL = (
    "https://influx-prod-13-prod-us-east-0.grafana.net/api/v1/push/influx/write"
)
GITHUB_GRAPHQL_API_URL = "https://api.github.com/graphql"
REPOSITORY_URL = "https://github.com/llvm/llvm-project.git"

# How many commits to query the GitHub GraphQL API for at a time.
# Querying too many commits at once often leads to the call failing.
GITHUB_API_BATCH_SIZE = 75

# Number of days to look back for new commits
# We allow some buffer time between when a commit is made and when it is queried
# for reviews. This is allow time for any events to propogate in the GitHub
# Archive BigQuery tables.
LOOKBACK_DAYS = 2

# Template query to find pull requests associated with commits on a given day.
# Searches for pull requests within a lower and upper bound of Github Archive
# event dates.
GITHUB_ARCHIVE_REVIEW_QUERY = """
WITH PullRequestReviews AS (
  SELECT DISTINCT
    JSON_VALUE(payload, '$.pull_request.id') AS pr_id,
    JSON_VALUE(payload, '$.review.state') as review_state,
  FROM `githubarchive.day.20*`
  WHERE
    repo.id = 75821432
    AND `type` = 'PullRequestReviewEvent'
    AND (_TABLE_SUFFIX BETWEEN '{lower_review_bound}' AND '{upper_review_bound}')
)
SELECT DISTINCT
  JSON_VALUE(pr_event.payload, '$.pull_request.merge_commit_sha') AS merge_commit_sha,
  JSON_VALUE(pr_event.payload, '$.pull_request.number') AS pull_request_number,
  pr_review.review_state as review_state
FROM `githubarchive.day.{commit_date}` AS pr_event
LEFT JOIN PullRequestReviews as pr_review ON
  JSON_VALUE(pr_event.payload, '$.pull_request.id') = pr_review.pr_id # PR ID should match the review events
WHERE
  pr_event.repo.id = 75821432
  AND pr_event.`type` = 'PullRequestEvent'
  AND JSON_VALUE(pr_event.payload, '$.pull_request.merge_commit_sha') IS NOT NULL
"""

# Template GraphQL subquery to check if a commit has an associated pull request
# and whether that pull request has been reviewed and approved.
COMMIT_GRAPHQL_SUBQUERY_TEMPLATE = """
commit_{commit_sha}:
  object(oid:"{commit_sha}") {{
    ... on Commit {{
      associatedPullRequests(first: 1) {{
        totalCount
        pullRequest: nodes {{
          number
          reviewDecision
        }}
      }}
    }}
  }}
"""


@dataclasses.dataclass
class LLVMCommitInfo:
  commit_sha: str
  commit_datetime: datetime.datetime
  commit_timestamp_seconds: int
  has_pull_request: bool = False
  pr_number: int = 0
  is_reviewed: bool = False
  is_approved: bool = False


def scrape_new_commits_by_date(
    target_datetime: datetime.datetime,
) -> list[git.Commit]:
  """Scrape new commits from a given dates.

  Args:
    target_datetime: The date to scrape for new commits.

  Returns:
    List of new commits made on the given date.
  """
  # Clone repository to current working directory
  repo = git.Repo.clone_from(
      url=REPOSITORY_URL,
      to_path="./llvm-project",
  )

  # Scrape for new commits
  # iter_commits() yields commits in reverse chronological order
  new_commits = []
  for commit in repo.iter_commits():
    # Skip commits that don't match the target date
    committed_datetime = commit.committed_datetime.astimezone(
        datetime.timezone.utc
    )
    if committed_datetime.date() != target_datetime.date():
      continue

    new_commits.append(commit)

  logging.info("Found %d new commits", len(new_commits))
  return new_commits


def query_for_reviews(
    new_commits: list[git.Commit], commit_datetime: datetime.datetime
) -> list[LLVMCommitInfo]:
  """Query GitHub Archive BigQuery for reviews of new commits.

  Args:
    new_commits: List of new commits to query for reviews.
    commit_datetime: The date that the new commits were made on.

  Returns:
    List of LLVMCommitInfo objects for each commit's review information.
  """

  # Search for reviews in the last 4 weeks
  earliest_review_date = (
      commit_datetime - datetime.timedelta(weeks=4)
  ).strftime("%Y%m%d")
  latest_review_date = datetime.datetime.now(datetime.timezone.utc).strftime(
      "%Y%m%d"
  )

  # Create a map of commit sha to info
  new_commits = {
      commit.hexsha: LLVMCommitInfo(
          commit.hexsha, commit.committed_datetime, commit.committed_date
      )
      for commit in new_commits
  }

  # Query each relevant daily GitHub Archive table
  query = GITHUB_ARCHIVE_REVIEW_QUERY.format(
      commit_date=commit_datetime.strftime("%Y%m%d"),
      lower_review_bound=earliest_review_date.removeprefix("20"),
      upper_review_bound=latest_review_date.removeprefix("20"),
  )
  bq_client = bigquery.Client()
  query_job = bq_client.query(query)
  results = query_job.result()

  # Process each found merge commit
  for row in results:
    # If this commit is irrelevant, skip it
    # Not every merge_commit_sha makes it into main, a "merge commit" can mean
    # different things depending on the state of the pull request.
    # docs.github.com/en/rest/pulls/pulls#get-a-pull-request for more details.
    merge_commit_sha = row["merge_commit_sha"]
    if merge_commit_sha not in new_commits:
      continue

    commit_info = new_commits[merge_commit_sha]
    commit_info.has_pull_request = True
    commit_info.pr_number = row["pull_request_number"]
    commit_info.is_reviewed = row["review_state"] is not None
    commit_info.is_approved = row["review_state"] == "approved"

  logging.info(
      "Total gigabytes processed: %d GB",
      query_job.total_bytes_processed / (1024**3),
  )

  return list(new_commits.values())


def validate_push_commits(
    new_commits: list[LLVMCommitInfo], github_token: str
) -> None:
  """Validate that push commits don't have a pull request.

  To address lossiness of data from GitHub Archive BigQuery, we check each
  commit to see if it actually has an associated pull request.

  Args:
    new_commits: List of commits to validate.
    github_token: The access token to use with the GitHub GraphQL API.
  """

  # Get all push commits from new commits and form their subqueries
  commit_subqueries = []
  potential_push_commits = {}
  for commit in new_commits:
    if commit.has_pull_request:
      continue
    potential_push_commits[commit.commit_sha] = commit
    commit_subqueries.append(
        COMMIT_GRAPHQL_SUBQUERY_TEMPLATE.format(commit_sha=commit.commit_sha)
    )
  logging.info("Found %d potential push commits", len(potential_push_commits))

  # Query GitHub GraphQL API for pull requests associated with push commits
  # We query in batches as large queries often fail
  api_commit_data = {}
  query_template = """
    query {
      repository(owner:"llvm", name:"llvm-project"){
          %s
      }
    }
  """
  num_batches = len(commit_subqueries) // GITHUB_API_BATCH_SIZE + 1
  logging.info("Querying GitHub GraphQL API in %d batches", num_batches)
  for i in range(num_batches):
    subquery_batch = commit_subqueries[
        i * GITHUB_API_BATCH_SIZE : (i + 1) * GITHUB_API_BATCH_SIZE
    ]
    query = query_template % "".join(subquery_batch)

    logging.info(
        "Querying batch %d of %d (%d commits)",
        i + 1,
        num_batches,
        len(subquery_batch),
    )
    response = requests.post(
        url=GITHUB_GRAPHQL_API_URL,
        headers={
            "Authorization": f"bearer {github_token}",
        },
        json={"query": query},
    )
    if response.status_code < 200 or response.status_code >= 300:
      logging.error("Failed to query GitHub GraphQL API: %s", response.text)
    api_commit_data.update(response.json()["data"]["repository"])

  amend_count = 0
  for commit_sha, data in api_commit_data.items():
    # Verify that push commit has no pull requests
    commit_sha = commit_sha.removeprefix("commit_")
    if data["associatedPullRequests"]["totalCount"] == 0:
      continue

    # Amend fields with new data from API
    pull_request = data["associatedPullRequests"]["pullRequest"][0]
    commit_info = potential_push_commits[commit_sha]
    commit_info.has_pull_request = True
    commit_info.pr_number = pull_request["number"]
    commit_info.is_reviewed = pull_request["reviewDecision"] is not None
    commit_info.is_approved = pull_request["reviewDecision"] == "APPROVED"
    amend_count += 1

  logging.info("Amended %d commits", amend_count)


def upload_daily_metrics(
    grafana_api_key: str,
    grafana_metrics_userid: str,
    new_commits: list[LLVMCommitInfo],
) -> None:
  """Upload daily commit metrics to Grafana.

  Args:
    grafana_api_key: The key to make API requests with.
    grafana_metrics_userid: The user to make API requests with.
    new_commits: List of commits to process & upload to Grafana.
  """
  # Count each type of commit made
  approval_count = 0
  review_count = 0
  pull_request_count = 0
  push_count = 0
  for commit in new_commits:
    if commit.is_approved:
      approval_count += 1
    elif commit.is_reviewed:
      review_count += 1
    elif commit.has_pull_request:
      pull_request_count += 1
    else:
      push_count += 1

  # Post data via InfluxDB API call
  request_data = (
      "llvm_project_main_daily_commits"
      " approval_count={},review_count={},pull_request_count={},push_count={}"
  ).format(approval_count, review_count, pull_request_count, push_count)
  response = requests.post(
      GRAFANA_URL,  # Set timestamp precision to seconds
      headers={"Content-Type": "text/plain"},
      data=request_data,
      auth=(grafana_metrics_userid, grafana_api_key),
  )

  if response.status_code < 200 or response.status_code >= 300:
    logging.error("Failed to submit data to Grafana: %s", response.text)


def main() -> None:
  github_token = os.environ["GITHUB_TOKEN"]
  grafana_api_key = os.environ["GRAFANA_API_KEY"]
  grafana_metrics_userid = os.environ["GRAFANA_METRICS_USERID"]

  # Scrape new commits
  date_to_scrape = datetime.datetime.now(
      datetime.timezone.utc
  ) - datetime.timedelta(days=LOOKBACK_DAYS)
  logging.info(
      "Cloning and scraping llvm/llvm-project for new commits on %s",
      date_to_scrape.strftime("%Y-%m-%d"),
  )
  new_commits = scrape_new_commits_by_date(date_to_scrape)
  if not new_commits:
    logging.info("No new commits found. Exiting.")
    return

  logging.info("Querying for reviews of new commits.")
  new_commit_info = query_for_reviews(new_commits, date_to_scrape)

  logging.info("Validating push commits.")
  validate_push_commits(new_commit_info, github_token)

  logging.info("Uploading metrics to Grafana.")
  upload_daily_metrics(grafana_api_key, grafana_metrics_userid, new_commit_info)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  main()
