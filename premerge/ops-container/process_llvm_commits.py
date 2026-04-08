import datetime
import logging
import os
import re
from typing import Any, Optional
import git
from google.cloud import bigquery
import operational_metrics_lib

REPOSITORY_URL = "https://github.com/llvm/llvm-project.git"

# BigQuery dataset and tables to write metrics to.
OPERATIONAL_METRICS_DATASET = "operational_metrics"
LLVM_COMMITS_TABLE = "llvm_commits"
LLVM_PULL_REQUESTS_TABLE = "llvm_pull_requests"
LLVM_REVIEWS_TABLE = "llvm_reviews"

# How many commits to query the GitHub GraphQL API for at a time.
# Querying too many commits at once often leads to the call failing.
GITHUB_API_BATCH_SIZE = 35

# Number of days to look back for new commits
# We allow some buffer time between when a commit is made and when it is queried
# for reviews. This is to allow time for any new GitHub events to propogate.
LOOKBACK_DAYS = 2

# Template GraphQL subquery to check if a commit has an associated pull request
# and whether that pull request has been reviewed and approved.
COMMIT_GRAPHQL_SUBQUERY_TEMPLATE = """
commit_{commit_sha}:
  object(oid:"{commit_sha}") {{
    ... on Commit {{
      author {{
        user {{
          login
        }}
      }}
      associatedPullRequests(first: 1) {{
        totalCount
        pullRequest: nodes {{
          {requested_pull_request_data}
        }}
      }}
    }}
  }}
"""


def scrape_commits_by_date(
    repo: git.Repo,
    target_datetime: datetime.datetime,
) -> list[git.Commit]:
  """Scrape commits from a given dates.

  Args:
    repo: The git repository to scrape.
    target_datetime: The date to scrape for new commits.

  Returns:
    List of new commits made on the given date.
  """
  # Scrape for new commits
  # iter_commits() yields commits in reverse chronological order
  commits = []
  for commit in repo.iter_commits():
    # Skip commits that don't match the target date
    committed_datetime = commit.committed_datetime.astimezone(
        datetime.timezone.utc
    )
    if committed_datetime.date() != target_datetime.date():
      continue

    commits.append(commit)

  logging.info("Found %d new commits", len(commits))
  return commits


def parse_commit_revert_info(
    commit_message: str,
) -> tuple[bool, Optional[int], Optional[str]]:
  """Parse a commit message for revert information.

  Args:
    commit_message: The commit message to parse.

  Returns:
    A tuple containing:
    - Whether the commit is a revert.
    - The pull request number that is being reverted (if any).
    - The commit hash that is being reverted (if any).
  """
  # Determine if this commit is a revert
  is_revert = (
      re.match(
          r"^Revert \".*\"( \(#\d+\))?", commit_message, flags=re.IGNORECASE
      )
      is not None
  )
  if not is_revert:
    return False, None, None

  # Check which pull request or commit is being reverted (if any)
  pull_request_match = re.search(
      r"Reverts? (?:llvm\/llvm-project)?#(\d+)",
      commit_message,
      flags=re.IGNORECASE,
  )
  commit_match = re.search(
      r"This reverts commit (\w+)", commit_message, flags=re.IGNORECASE
  )

  pull_request_reverted = (
      int(pull_request_match.group(1)) if pull_request_match else None
  )
  commit_reverted = commit_match.group(1) if commit_match else None

  return is_revert, pull_request_reverted, commit_reverted


def extract_initial_commit_data(
    commit: git.Commit,
) -> operational_metrics_lib.LLVMCommitData:
  # Parse commit message for revert information
  is_revert, pull_request_reverted, commit_reverted = parse_commit_revert_info(
      commit.message
  )

  # Add entry
  return operational_metrics_lib.LLVMCommitData(
      commit_sha=commit.hexsha,
      commit_timestamp_seconds=commit.committed_date,
      diff=[
          {
              "file": file,
              "additions": line_stats["insertions"],
              "deletions": line_stats["deletions"],
              "total": line_stats["lines"],
          }
          for file, line_stats in commit.stats.files.items()
      ],
      is_revert=is_revert,
      pull_request_reverted=pull_request_reverted,
      commit_reverted=commit_reverted,
  )


def extract_commit_data(
    scraped_commits: list[git.Commit],
    api_data: dict[str, Any],
) -> list[operational_metrics_lib.LLVMCommitData]:
  """Extract commit data from scraped Git commits and GitHub API data.

  Args:
    scraped_commits: List of commits scraped from cloned LLVM repository.
    api_data: JSON response from GitHub API.

  Returns:
    List of LLVMCommitData objects for each commit found.
  """
  commit_map = {
      commit.hexsha: extract_initial_commit_data(commit)
      for commit in scraped_commits
  }
  for commit_sha, commit_data in api_data.items():
    commit = commit_map[commit_sha.removeprefix("commit_")]

    # Some commits have no author, possible when an account is deleted or
    # email address is changed.
    if commit_data["author"]["user"]:
      commit.commit_author = commit_data["author"]["user"]["login"]
    else:
      logging.warning("No author found for commit %s", commit.commit_sha)
      commit.commit_author = None

    # If commit has no pull requests, skip it. No data to update.
    if commit_data["associatedPullRequests"]["totalCount"] == 0:
      commit.associated_pull_request = None
      continue
    else:
      pull_request = commit_data["associatedPullRequests"]["pullRequest"][0]
      commit.associated_pull_request = pull_request["number"]

  return list(commit_map.values())


def extract_pull_request_data(
    api_data: dict[str, Any],
) -> list[operational_metrics_lib.LLVMPullRequestData]:
  """Extract pull request data from GitHub API data.

  Args:
    api_data: JSON response from GitHub API.

  Returns:
    List of LLVMPullRequestData objects for each pull request found.
  """
  pull_requests_by_number = {}
  commits_by_pull_request_number = {}

  for commit_sha, commit_data in api_data.items():
    if commit_data["associatedPullRequests"]["totalCount"] == 0:
      continue

    pull_request = commit_data["associatedPullRequests"]["pullRequest"][0]
    pull_request_number = pull_request["number"]
    commit_hash = commit_sha.removeprefix("commit_")

    if pull_request_number not in pull_requests_by_number:
      pull_requests_by_number[pull_request_number] = pull_request
      commits_by_pull_request_number[pull_request_number] = []

    commits_by_pull_request_number[pull_request_number].append(commit_hash)

  return [
      operational_metrics_lib.parse_pull_request_data(
          pull_request=pull_request,
          associated_commits=commits_by_pull_request_number[
              pull_request_number
          ],
      )
      for pull_request_number, pull_request in pull_requests_by_number.items()
  ]


def extract_review_data(
    api_data: dict[str, Any],
) -> list[operational_metrics_lib.LLVMReviewData]:
  """Extract review data from GitHub API data.

  Args:
    api_data: JSON response from Github API.

  Returns:
    List of LLVMReviewData objects for each review found.
  """
  review_data = []
  for _, commit_data in api_data.items():
    if commit_data["associatedPullRequests"]["totalCount"] == 0:
      continue
    pull_request = commit_data["associatedPullRequests"]["pullRequest"][0]
    review_data.extend(operational_metrics_lib.parse_review_data(pull_request))

  return review_data


def fetch_commit_data_from_github(
    github_token: str,
    commit_hashes: list[str],
):
  commit_subqueries = [
      COMMIT_GRAPHQL_SUBQUERY_TEMPLATE.format(
          commit_sha=commit_sha,
          requested_pull_request_data=operational_metrics_lib.PULL_REQUEST_GRAPHQL_DATA,
      )
      for commit_sha in commit_hashes
  ]
  return operational_metrics_lib.fetch_repository_data_from_github(
      github_token=github_token,
      subqueries=commit_subqueries,
  )


def main() -> None:
  github_token = os.environ["GITHUB_TOKEN"]

  # Scrape new commits
  date_to_scrape = datetime.datetime.now(
      datetime.timezone.utc
  ) - datetime.timedelta(days=LOOKBACK_DAYS)
  logging.info(
      "Cloning and scraping llvm/llvm-project for new commits on %s",
      date_to_scrape.strftime("%Y-%m-%d"),
  )

  # Clone repository to current working directory
  repo = git.Repo.clone_from(
      url=REPOSITORY_URL,
      to_path="./llvm-project",
  )

  commits = scrape_commits_by_date(repo, date_to_scrape)
  if not commits:
    logging.info("No new commits found. Exiting.")
    return

  logging.info("Fetching GitHub API data for discovered commits.")
  api_data = fetch_commit_data_from_github(github_token, commits)
  commit_data = extract_commit_data(commits, api_data)
  pull_request_data = extract_pull_request_data(api_data)
  review_data = extract_review_data(api_data)

  logging.info("Uploading metrics to BigQuery.")
  bq_client = bigquery.Client()
  operational_metrics_lib.upload_to_bigquery(
      bq_client,
      bq_dataset=OPERATIONAL_METRICS_DATASET,
      bq_table=LLVM_COMMITS_TABLE,
      llvm_data=commit_data,
      primary_key="commit_sha",
  )
  operational_metrics_lib.upload_to_bigquery(
      bq_client,
      bq_dataset=OPERATIONAL_METRICS_DATASET,
      bq_table=LLVM_PULL_REQUESTS_TABLE,
      llvm_data=pull_request_data,
      primary_key="pull_request_number",
  )
  operational_metrics_lib.upload_to_bigquery(
      bq_client,
      bq_dataset=OPERATIONAL_METRICS_DATASET,
      bq_table=LLVM_REVIEWS_TABLE,
      llvm_data=review_data,
      primary_key="review_id",
  )
  bq_client.close()


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  main()
