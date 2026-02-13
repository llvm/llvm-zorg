import dataclasses
import datetime
import logging
import math
import os
import re
from typing import Any, Optional
import git
from google.cloud import bigquery
import requests
import retry

GITHUB_GRAPHQL_API_URL = "https://api.github.com/graphql"
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
          author {{ login }}
          number
          createdAt
          mergedAt
          labels(first: 25) {{
            nodes {{
              name
            }}
          }}
          reviews(last: 100) {{
            nodes {{
              state
              createdAt
              reviewer: author {{
                login
              }}
            }}
          }}
        }}
      }}
    }}
  }}
"""


@dataclasses.dataclass
class LLVMCommitData:
  commit_sha: str
  commit_timestamp_seconds: int
  diff: list[dict[str, int | str]]
  commit_author: str | None = (
      None  # Username of author is unknown until API call
  )
  associated_pull_request: int | None = None
  is_revert: bool = False
  pull_request_reverted: int | None = None
  commit_reverted: str | None = None


@dataclasses.dataclass
class LLVMPullRequestData:
  pull_request_number: int
  pull_request_author: str
  pull_request_timestamp_seconds: int
  merged_at_timestamp_seconds: int
  associated_commit: str
  labels: list[dict[str, str]]


@dataclasses.dataclass
class LLVMReviewData:
  review_author: str
  review_timestamp_seconds: int
  review_state: str
  associated_pull_request: int


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
) -> LLVMCommitData:
  # Parse commit message for revert information
  is_revert, pull_request_reverted, commit_reverted = parse_commit_revert_info(
      commit.message
  )

  # Add entry
  return LLVMCommitData(
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
) -> list[LLVMCommitData]:
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
) -> list[LLVMPullRequestData]:
  """Extract pull request data from GitHub API data.

  Args:
    api_data: JSON response from GitHub API.

  Returns:
    List of LLVMPullRequestData objects for each pull request found.
  """
  pull_request_data = []
  for commit_sha, commit_data in api_data.items():
    if commit_data["associatedPullRequests"]["totalCount"] == 0:
      continue
    pull_request = commit_data["associatedPullRequests"]["pullRequest"][0]

    # Some pull requests have no author, possible when an account is deleted or
    # email address is changed.
    if pull_request["author"] is not None:
      author_login = pull_request["author"]["login"]
    else:
      author_login = None
      logging.warning(
          "No author found for pull request %d", pull_request["number"]
      )

    # Convert ISO timestamp to Unix timestamp, in seconds
    create_unix_timestamp = int(
        datetime.datetime.fromisoformat(pull_request["createdAt"]).timestamp()
    )
    if pull_request["mergedAt"] is not None:
      merge_unix_timestamp = int(
          datetime.datetime.fromisoformat(pull_request["mergedAt"]).timestamp()
      )
    else:
      merge_unix_timestamp = None

    # Extract label names associated with the pull request
    labels = [
        {
            "name": label["name"],
        }
        for label in pull_request["labels"]["nodes"]
    ]

    pull_request_data.append(
        LLVMPullRequestData(
            pull_request_number=pull_request["number"],
            pull_request_author=author_login,
            pull_request_timestamp_seconds=create_unix_timestamp,
            merged_at_timestamp_seconds=merge_unix_timestamp,
            associated_commit=commit_sha.removeprefix("commit_"),
            labels=labels,
        )
    )

  return pull_request_data


def extract_review_data(
    api_data: dict[str, Any],
) -> list[LLVMReviewData]:
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
    associated_pull_request = pull_request["number"]
    pull_request_author = (
        pull_request["author"]["login"] if pull_request["author"] else None
    )

    for review in pull_request["reviews"]["nodes"]:
      # Some reviews have no author, possible when an account is deleted or
      # email address is changed.
      if review["reviewer"] is not None:
        reviewer_login = review["reviewer"]["login"]
      else:
        reviewer_login = None
        logging.warning(
            "No reviewer found for review associated with pull request %d",
            associated_pull_request,
        )

      # Skip 'reviews' that were made by the pull request author.
      if reviewer_login is not None and reviewer_login == pull_request_author:
        continue

      # Convert ISO timestamp to Unix timestamp, in seconds
      unix_timestamp = int(
          datetime.datetime.fromisoformat(review["createdAt"]).timestamp()
      )

      review_data.append(
          LLVMReviewData(
              review_author=reviewer_login,
              review_timestamp_seconds=unix_timestamp,
              review_state=review["state"].upper(),
              associated_pull_request=associated_pull_request,
          )
      )

  return review_data


@retry.retry(
    exceptions=(
        requests.exceptions.HTTPError,
        requests.exceptions.ChunkedEncodingError,
    ),
    tries=5,
    delay=1,
    backoff=2,
)
def query_github_graphql_api(
    query: str,
    github_token: str,
) -> requests.Response:
  """Query GitHub GraphQL API, retrying on failure.

  Args:
    query: The GraphQL query to send to the GitHub API.
    github_token: The access token to use with the GitHub GraphQL API.

  Returns:
    The response from the GitHub GraphQL API.
  """
  response = requests.post(
      url=GITHUB_GRAPHQL_API_URL,
      headers={
          "Authorization": f"bearer {github_token}",
      },
      json={"query": query},
  )
  # Exit if API call fails
  # A failed API call means a large batch of data is missing and will not be
  # reflected in the dashboard. The dashboard will silently misrepresent
  # commit data if we continue execution, so it's better to fail loudly.
  response.raise_for_status()

  return response


def fetch_github_api_data(
    github_token: str,
    commit_hashes: list[str],
    batch_size: int = GITHUB_API_BATCH_SIZE,
) -> dict[str, dict[str, Any]]:
  """Fetch commit data from the GitHub GraphQL API.

  Args:
    github_token: The access token to use with the GitHub GraphQL API.
    commit_hashes: List of commit hashes to fetch data for.
    batch_size: The number of commits to query the GitHub GraphQL API for at a
      time.

  Returns:
    A dictionary of commit hash to commit data from the GitHub GraphQL API.
  """
  # Create GraphQL subqueries for each commit
  commit_subqueries = [
      COMMIT_GRAPHQL_SUBQUERY_TEMPLATE.format(commit_sha=commit_sha)
      for commit_sha in commit_hashes
  ]
  api_commit_data = {}
  query_template = """
    query {
      repository(owner:"llvm", name:"llvm-project"){
          %s
      }
    }
  """
  num_batches = math.ceil(len(commit_subqueries) / batch_size)
  logging.info("Querying GitHub GraphQL API in %d batches", num_batches)
  for i in range(num_batches):
    subquery_batch = commit_subqueries[i * batch_size : (i + 1) * batch_size]
    query = query_template % "".join(subquery_batch)

    logging.info(
        "Querying batch %d of %d (%d commits)",
        i + 1,
        num_batches,
        len(subquery_batch),
    )
    response = query_github_graphql_api(query, github_token)

    api_commit_data.update(response.json()["data"]["repository"])

  return api_commit_data


def upload_daily_metrics_to_bigquery(
    bq_client: bigquery.Client,
    bq_dataset: str,
    bq_table: str,
    llvm_data: list[LLVMCommitData | LLVMPullRequestData | LLVMReviewData],
) -> None:
  """Upload processed LLVM metrics to a BigQuery dataset.

  Args:
    bq_client: The BigQuery client to use.
    bq_dataset: The name of the BigQuery dataset to upload to.
    bq_table: The name of the BigQuery table to upload to.
    llvm_data: List of LLVM data to process & upload to BigQuery.
  """
  table_ref = bq_client.dataset(bq_dataset).table(bq_table)
  table = bq_client.get_table(table_ref)
  llvm_records = [dataclasses.asdict(commit) for commit in llvm_data]
  errors = bq_client.insert_rows(table=table, rows=llvm_records)
  if errors:
    logging.error("Failed to upload LLVM data to BigQuery: %s", errors)
    exit(1)


def main() -> None:
  github_token = os.environ["GITHUB_TOKEN"]

  # Clone repository to current working directory
  repo = git.Repo.clone_from(
      url=REPOSITORY_URL,
      to_path="./llvm-project",
  )

  # Scrape new commits
  date_to_scrape = datetime.datetime.now(
      datetime.timezone.utc
  ) - datetime.timedelta(days=LOOKBACK_DAYS)
  logging.info(
      "Cloning and scraping llvm/llvm-project for new commits on %s",
      date_to_scrape.strftime("%Y-%m-%d"),
  )

  commits = scrape_commits_by_date(repo, date_to_scrape)
  if not commits:
    logging.info("No new commits found. Exiting.")
    return

  logging.info("Fetching GitHub API data for discovered commits.")
  api_data = fetch_github_api_data(github_token, commits)
  commit_data = extract_commit_data(commits, api_data)
  pull_request_data = extract_pull_request_data(api_data)
  review_data = extract_review_data(api_data)

  logging.info("Uploading metrics to BigQuery.")
  bq_client = bigquery.Client()
  upload_daily_metrics_to_bigquery(
      bq_client, OPERATIONAL_METRICS_DATASET, LLVM_COMMITS_TABLE, commit_data
  )
  upload_daily_metrics_to_bigquery(
      bq_client,
      OPERATIONAL_METRICS_DATASET,
      LLVM_PULL_REQUESTS_TABLE,
      pull_request_data,
  )
  upload_daily_metrics_to_bigquery(
      bq_client, OPERATIONAL_METRICS_DATASET, LLVM_REVIEWS_TABLE, review_data
  )
  bq_client.close()


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  main()
