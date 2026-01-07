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
          number
          reviewDecision
          reviews(first: 25) {{
            nodes {{
              state
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
  commit_author: str = ""  # GitHub username of author is unknown until API call
  has_pull_request: bool = False
  pull_request_number: int = 0
  is_reviewed: bool = False
  is_approved: bool = False
  reviewers: set[str] = dataclasses.field(default_factory=set)
  is_revert: bool = False
  pull_request_reverted: int | None = None
  commit_reverted: str | None = None


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
    github_token: str, commit_hashes: list[str]
) -> dict[str, dict[str, Any]]:
  """Fetch commit data from the GitHub GraphQL API.

  Args:
    github_token: The access token to use with the GitHub GraphQL API.
    commit_hashes: List of commit hashes to fetch data for.

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
  num_batches = math.ceil(len(commit_subqueries) / GITHUB_API_BATCH_SIZE)
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
    response = query_github_graphql_api(query, github_token)

    api_commit_data.update(response.json()["data"]["repository"])

  return api_commit_data


def amend_commit_data(
    commit_data: LLVMCommitData, api_data: dict[str, Any]
) -> None:
  """Amend commit information with data from GitHub API.

  Args:
    commit_data: The LLVMCommitData object to modify.
    api_data: The GitHub API data to amend the commit information with.
  """
  commit_data.commit_author = api_data["author"]["user"]["login"]

  # If commit has no pull requests, skip it. No data to update.
  if api_data["associatedPullRequests"]["totalCount"] == 0:
    return

  pull_request = api_data["associatedPullRequests"]["pullRequest"][0]
  commit_data.has_pull_request = True
  commit_data.pull_request_number = pull_request["number"]

  # Check the state of reviews to determine if this commit was reviewed and
  # approved.
  review_states = set([
      review["state"].upper()
      for review in pull_request["reviews"]["nodes"]
      if review["reviewer"]["login"] != commit_data.commit_author
  ])
  commit_data.is_reviewed = bool(review_states)
  commit_data.is_approved = "APPROVED" in review_states

  commit_data.reviewers = set([
      review["reviewer"]["login"] for review in pull_request["reviews"]["nodes"]
  ])

  # There are cases where the commit author is counted as a reviewer. This is
  # against what we want to measure, so remove them from the set of reviewers.
  commit_data.reviewers.discard(commit_data.commit_author)


def build_commit_data(
    commits: list[git.Commit], github_token: str
) -> list[LLVMCommitData]:
  """Query GitHub GraphQL API for reviews of commits.

  Args:
    commits: List of commits to query for reviews.
    github_token: The access token to use with the GitHub GraphQL API.

  Returns:
    List of LLVMCommitData objects for each commit's review information.
  """
  # Create a map of commit sha to info
  commits_data = {
      commit.hexsha: extract_initial_commit_data(commit) for commit in commits
  }

  # Fetch data for each commit from the GitHub GraphQL API
  api_commit_data = fetch_github_api_data(github_token, commits_data.keys())

  # Amend commit information with GitHub data
  for commit_sha, api_data in api_commit_data.items():
    commit_sha = commit_sha.removeprefix("commit_")
    amend_commit_data(commits_data[commit_sha], api_data)

  return list(commits_data.values())


def upload_daily_metrics_to_bigquery(
    bq_client: bigquery.Client, commits_data: list[LLVMCommitData]
) -> None:
  """Upload processed commit metrics to a BigQuery dataset.

  Args:
    bq_client: The BigQuery client to use.
    commits_data: List of commits to process & upload to BigQuery.
  """
  table_ref = bq_client.dataset(OPERATIONAL_METRICS_DATASET).table(
      LLVM_COMMITS_TABLE
  )
  table = bq_client.get_table(table_ref)
  commit_records = [dataclasses.asdict(commit) for commit in commits_data]
  errors = bq_client.insert_rows(table, commit_records)
  if errors:
    logging.error("Failed to upload commit info to BigQuery: %s", errors)
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

  logging.info("Querying for reviews of new commits.")
  commit_data = build_commit_data(commits, github_token)

  logging.info("Uploading metrics to BigQuery.")
  bq_client = bigquery.Client()
  upload_daily_metrics_to_bigquery(bq_client, commit_data)
  bq_client.close()


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  main()
