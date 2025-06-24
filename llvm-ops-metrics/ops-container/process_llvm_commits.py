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

# Path to checked out llvm/llvm-project repository
REPOSITORY_PATH = "/data/llvm-project"

# Path to record of most recently processed commits
DATA_PATH = "/data/recent_commits.csv"

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


@dataclasses.dataclass
class LLVMCommitInfo:
  commit_sha: str
  commit_datetime: datetime.datetime
  commit_timestamp_seconds: int
  has_pull_request: bool = False
  pr_number: int = 0
  is_reviewed: bool = False
  is_approved: bool = False


def read_past_commits() -> list[list[str]]:
  """Read recently scraped commits from the data path.

  Returns:
    List of commits that have been scraped.
  """
  # If the data path doesn't exist, we haven't scraped any commits yet.
  if not os.path.exists(DATA_PATH):
    logging.warning(
        " Data path %s does not exist. No past commits found.", DATA_PATH
    )
    return []

  # Read the past commits from the data path
  with open(DATA_PATH, "r") as f:
    f.readline()  # Skip header
    rows = f.readlines()
  commit_history = [row.strip().split(",") for row in rows if row.strip()]
  return commit_history


def record_new_commits(new_commits: list[LLVMCommitInfo]) -> None:
  """Record newly scraped commits to the data path.

  Args:
    new_commits: List of commits to record.

  Returns:
    None
  """
  with open(DATA_PATH, "w") as f:

    # Write CSV header
    f.write(
        ",".join([
            "commit_sha",
            "commit_datetime",
            "has_pull_request",
            "pull_request_number",
            "is_reviewed",
            "is_approved",
        ])
        + "\n"
    )

    # We want the newest commit as the last entry, so iterate backwards
    for i in range(len(new_commits) - 1, -1, -1):
      commit_info = new_commits[i]
      record = ",".join([
          commit_info.commit_sha,
          commit_info.commit_datetime.astimezone(
              datetime.timezone.utc
          ).isoformat(),
          str(commit_info.has_pull_request),
          str(commit_info.pr_number),
          str(commit_info.is_reviewed),
          str(commit_info.is_approved),
      ])
      f.write(f"{record}\n")


def scrape_new_commits_by_date(
    last_known_commit: str, target_datetime: datetime.datetime
) -> list[git.Commit]:
  """Scrape new commits from a given dates.

  Args:
    last_known_commit: The last known scraped commit.
    target_datetime: The date to scrape for new commits.

  Returns:
    List of new commits made on the given date.
  """
  # Pull any new commits into local repository
  repo = git.Repo(REPOSITORY_PATH)
  repo.remotes.origin.pull()

  # Scrape for new commits
  # iter_commits() yields commits in reverse chronological order
  new_commits = []
  for commit in repo.iter_commits():
    # Skip commits that are too new
    committed_datetime = commit.committed_datetime.astimezone(
        datetime.timezone.utc
    )
    if committed_datetime.date() > target_datetime.date():
      continue
    # Stop scraping if the commit is older than the target date
    if committed_datetime.date() < target_datetime.date():
      break
    # Stop scraping if we've already recorded this commit
    if commit.hexsha == last_known_commit:
      break

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

  Returns:
    None
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
  grafana_api_key = os.environ["GRAFANA_API_KEY"]
  grafana_metrics_userid = os.environ["GRAFANA_METRICS_USERID"]

  logging.info("Reading recently processed commits.")
  recorded_commits = read_past_commits()

  last_known_commit = recorded_commits[-1][0] if recorded_commits else ""

  # Scrape new commits, if any
  date_to_scrape = datetime.datetime.now(
      datetime.timezone.utc
  ) - datetime.timedelta(days=LOOKBACK_DAYS)
  logging.info(
      "Scraping checked out llvm/llvm-project for new commits on %s",
      date_to_scrape.strftime("%Y-%m-%d"),
  )
  new_commits = scrape_new_commits_by_date(last_known_commit, date_to_scrape)
  if not new_commits:
    logging.info("No new commits found. Exiting.")
    return

  logging.info("Querying for reviews of new commits.")
  new_commit_info = query_for_reviews(new_commits, date_to_scrape)

  logging.info("Uploading metrics to Grafana.")
  upload_daily_metrics(grafana_api_key, grafana_metrics_userid, new_commit_info)

  logging.info("Recording new commits.")
  record_new_commits(new_commit_info)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  main()

