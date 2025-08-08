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

# BigQuery dataset and tables to write metrics to.
OPERATIONAL_METRICS_DATASET = "operational_metrics"
LLVM_COMMITS_TABLE = "llvm_commits"

# How many commits to query the GitHub GraphQL API for at a time.
# Querying too many commits at once often leads to the call failing.
GITHUB_API_BATCH_SIZE = 50

# Number of days to look back for new commits
# We allow some buffer time between when a commit is made and when it is queried
# for reviews. This is allow time for any events to propogate in the GitHub
# Archive BigQuery tables.
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
          reviews(first: 10) {{
            nodes {{
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
class LLVMCommitInfo:
  commit_sha: str
  commit_timestamp_seconds: int
  files_modified: set[str]
  commit_author: str = ""  # GitHub username of author is unknown until API call
  has_pull_request: bool = False
  pull_request_number: int = 0
  is_reviewed: bool = False
  is_approved: bool = False
  reviewers: set[str] = dataclasses.field(default_factory=set)


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
          commit_sha=commit.hexsha,
          commit_timestamp_seconds=commit.committed_date,
          files_modified=set(commit.stats.files.keys()),
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

    # Exit if API call fails
    # A failed API call means a large batch of data is missing and will not be
    # reflected in the dashboard. The dashboard will silently misrepresent
    # commit data if we continue execution, so it's better to fail loudly.
    if response.status_code < 200 or response.status_code >= 300:
      logging.error("Failed to query GitHub GraphQL API: %s", response.text)
      exit(1)

    api_commit_data.update(response.json()["data"]["repository"])

  # Amend commit information with GitHub data
  for commit_sha, data in api_commit_data.items():
    commit_sha = commit_sha.removeprefix("commit_")
    commit_info = new_commits[commit_sha]
    commit_info.commit_author = data["author"]["user"]["login"]

    # If commit has no pull requests, skip it. No data to update.
    if data["associatedPullRequests"]["totalCount"] == 0:
      continue

    pull_request = data["associatedPullRequests"]["pullRequest"][0]
    commit_info.has_pull_request = True
    commit_info.pull_request_number = pull_request["number"]
    commit_info.is_reviewed = pull_request["reviewDecision"] is not None
    commit_info.is_approved = pull_request["reviewDecision"] == "APPROVED"
    commit_info.reviewers = set([
        review["reviewer"]["login"]
        for review in pull_request["reviews"]["nodes"]
    ])

    # There are cases where the commit author is counted as a reviewer. This is
    # against what we want to measure, so remove them from the set of reviewers.
    commit_info.reviewers.discard(commit_info.commit_author)

  return list(new_commits.values())


def get_past_contributors(bq_client: bigquery.Client) -> set[str]:
  """Get past contributors to LLVM from BigQuery dataset.

  Args:
    bq_client: The BigQuery client to use.

  Returns:
    Set of unique past contributors to LLVM.
  """
  results = bq_client.query("""
      SELECT
        DISTINCT commit_author
      FROM %s.%s
      WHERE commit_author IS NOT NULL
      """ % (OPERATIONAL_METRICS_DATASET, LLVM_COMMITS_TABLE)).result()
  return set(row.commit_author for row in results)


def upload_daily_metrics_to_grafana(
    grafana_api_key: str,
    grafana_metrics_userid: str,
    new_commits: list[LLVMCommitInfo],
    past_contributors: set[str],
) -> None:
  """Upload daily commit metrics to Grafana.

  Args:
    grafana_api_key: The key to make API requests with.
    grafana_metrics_userid: The user to make API requests with.
    new_commits: List of commits to process & upload to Grafana.
    past_contributors: Set of unique past contributors to LLVM.
  """

  def post_data(data: str) -> None:
    """Helper function to post data to Grafana."""
    response = requests.post(
        GRAFANA_URL,
        headers={"Content-Type": "text/plain"},
        data=data,
        auth=(grafana_metrics_userid, grafana_api_key),
    )
    if response.status_code < 200 or response.status_code >= 300:
      logging.error("Failed to submit data to Grafana: %s", response.text)

  # Count each type of commit made
  approval_count = 0
  review_count = 0
  pull_request_count = 0
  push_count = 0
  contributors = set()
  for commit in new_commits:
    if commit.is_approved:
      approval_count += 1
    elif commit.is_reviewed:
      review_count += 1
    elif commit.has_pull_request:
      pull_request_count += 1
    else:
      push_count += 1
    contributors.add(commit.commit_author)

  # Post data via InfluxDB API call
  # Commit data
  request_data = (
      "llvm_project_main_daily_commits"
      " approval_count={},review_count={},pull_request_count={},push_count={}"
  ).format(approval_count, review_count, pull_request_count, push_count)
  post_data(request_data)

  # Contributor data
  request_data = (
      "llvm_project_main"
      " daily_unique_contributor_count={},all_time_unique_contributor_count={}"
      .format(len(contributors), len(contributors | past_contributors))
  )
  post_data(request_data)


def upload_daily_metrics_to_bigquery(
    bq_client: bigquery.Client, new_commits: list[LLVMCommitInfo]
) -> None:
  """Upload processed commit metrics to a BigQuery dataset.

  Args:
    bq_client: The BigQuery client to use.
    new_commits: List of commits to process & upload to BigQuery.
  """
  table_ref = bq_client.dataset(OPERATIONAL_METRICS_DATASET).table(
      LLVM_COMMITS_TABLE
  )
  table = bq_client.get_table(table_ref)
  commit_records = [dataclasses.asdict(commit) for commit in new_commits]
  bq_client.insert_rows(table, commit_records)


def main() -> None:
  github_token = os.environ["GITHUB_TOKEN"]
  grafana_api_key = os.environ["GRAFANA_API_KEY"]
  grafana_metrics_userid = os.environ["GRAFANA_METRICS_USERID"]

  bq_client = bigquery.Client()

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

  logging.info("Getting set of past LLVM contributors.")
  past_contributors = get_past_contributors(bq_client)

  logging.info("Uploading metrics to Grafana.")
  upload_daily_metrics_to_grafana(
      grafana_api_key,
      grafana_metrics_userid,
      new_commit_info,
      past_contributors,
  )

  logging.info("Uploading metrics to BigQuery.")
  upload_daily_metrics_to_bigquery(bq_client, new_commit_info)

  bq_client.close()


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  main()
