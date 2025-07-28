import dataclasses
import datetime
import logging
import os
import git
import requests

GRAFANA_URL = (
    "https://influx-prod-13-prod-us-east-0.grafana.net/api/v1/push/influx/write"
)
GITHUB_GRAPHQL_API_URL = "https://api.github.com/graphql"
REPOSITORY_URL = "https://github.com/llvm/llvm-project.git"

# How many commits to query the GitHub GraphQL API for at a time.
# Querying too many commits at once often leads to the call failing.
GITHUB_API_BATCH_SIZE = 50

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
    new_commits: list[git.Commit], github_token: str
) -> list[LLVMCommitInfo]:
  """Query GitHub GraphQL API for reviews of new commits.

  Args:
    new_commits: List of new commits to query for reviews.
    github_token: The access token to use with the GitHub GraphQL API.

  Returns:
    List of LLVMCommitInfo objects for each commit's review information.
  """
  # Create a map of commit sha to info
  new_commits = {
      commit.hexsha: LLVMCommitInfo(
          commit.hexsha, commit.committed_datetime, commit.committed_date
      )
      for commit in new_commits
  }

  # Create GraphQL subqueries for each commit
  commit_subqueries = []
  for commit_sha in new_commits:
    commit_subqueries.append(
        COMMIT_GRAPHQL_SUBQUERY_TEMPLATE.format(commit_sha=commit_sha)
    )

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

  for commit_sha, data in api_commit_data.items():
    # Verify that push commit has no pull requests
    commit_sha = commit_sha.removeprefix("commit_")

    # If commit has no pull requests, skip it. No data to update.
    if data["associatedPullRequests"]["totalCount"] == 0:
      continue

    pull_request = data["associatedPullRequests"]["pullRequest"][0]
    commit_info = new_commits[commit_sha]
    commit_info.has_pull_request = True
    commit_info.pr_number = pull_request["number"]
    commit_info.is_reviewed = pull_request["reviewDecision"] is not None
    commit_info.is_approved = pull_request["reviewDecision"] == "APPROVED"

  return list(new_commits.values())


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
  new_commit_info = query_for_reviews(new_commits, github_token)

  logging.info("Uploading metrics to Grafana.")
  upload_daily_metrics(grafana_api_key, grafana_metrics_userid, new_commit_info)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  main()
