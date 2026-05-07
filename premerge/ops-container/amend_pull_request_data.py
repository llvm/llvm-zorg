import datetime
import logging
import os
from typing import Any

from google.cloud import bigquery
import operational_metrics_lib

# Twice the frequency of cronjobs/amend_pull_request_data_cronjob.yaml
LOOKBACK_HOURS = 4

# BigQuery dataset and tables to write metrics to.
OPERATIONAL_METRICS_DATASET = "operational_metrics"
LLVM_PULL_REQUESTS_TABLE = "llvm_pull_requests"
LLVM_REVIEWS_TABLE = "llvm_reviews"
LLVM_REPOSITORY_SNAPSHOT_TABLE = "llvm_repository_snapshots"

OPEN_PULL_REQUEST_PREDICATE = (
    "LLVMPull.pull_request_state = 'OPEN' AND NOT LLVMPull.is_stale_data"
)

UNAPPROVED_PULL_REQUEST_PREDICATE = f"""
LLVMPull.pull_request_state = 'MERGED'
AND 'reviewed-post-commit' NOT IN UNNEST(LLVMPull.labels.name)
AND NOT EXISTS(
  SELECT 1
  FROM {OPERATIONAL_METRICS_DATASET}.{LLVM_REVIEWS_TABLE} AS LLVMReview
  WHERE
    LLVMReview.review_state = 'APPROVED'
    AND LLVMReview.associated_pull_request = LLVMPull.pull_request_number
)
"""


def fetch_open_pull_requests_from_github(
    github_token: str,
    cutoff_timestamp: datetime.datetime,
) -> list[dict[str, Any]]:
  """Fetch open pull requests from the GitHub GraphQL API.

  Args:
    github_token: The GitHub API token to use for authentication.
    cutoff_timestamp: The cutoff timestamp to use for the query.

  Returns:
    A list of open pull requests from the GitHub GraphQL API.
  """

  search_query = """
  query($cursor: String) {{
    search(
      query: "repo:llvm/llvm-project is:pr is:open base:main created:>{cutoff_timestamp}",
      type: ISSUE,
      first: 100,
      after: $cursor
    ) {{
      issueCount
      pageInfo {{
        hasNextPage
        endCursor
      }}
      nodes {{
        ... on PullRequest {{
          {requested_pull_request_data}
        }}
      }}
    }}
  }}
  """.format(
      cutoff_timestamp=cutoff_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
      requested_pull_request_data=operational_metrics_lib.PULL_REQUEST_GRAPHQL_DATA,
  )

  has_next_page = True
  cursor = None
  pull_requests = []
  while has_next_page:
    variables = {
        "cursor": cursor,
    }
    response = operational_metrics_lib.query_github_graphql_api(
        query=search_query,
        variables=variables,
        github_token=github_token,
    )

    response_data = response.json()["data"]["search"]
    pull_requests.extend(response_data["nodes"])
    has_next_page = response_data["pageInfo"]["hasNextPage"]
    cursor = response_data["pageInfo"]["endCursor"]

  return pull_requests


def get_pull_requests_by_age_from_bigquery(
    bq_client: bigquery.Client,
    predicate: str,
    timestamp_column: str,
    minimum_age_days: int,
    maximum_age_days: int,
) -> dict[int, list[int]]:
  """Get pull requests from BigQuery, filtered by predicate and grouped by age.

  Args:
    bq_client: The BigQuery client to use for querying.
    predicate: The predicate to use for filtering pull requests.
    timestamp_column: The column to use for the timestamp.
    minimum_age_days: The minimum age in days to filter by.
    maximum_age_days: The maximum age in days to filter by.

  Returns:
    A dictionary of pull requests grouped by age in days.
  """

  query = f"""
  SELECT
    ARRAY_AGG(DISTINCT pull_request_number) AS pull_request_numbers,
    TIMESTAMP_DIFF(
        CURRENT_TIMESTAMP(),
        TIMESTAMP_SECONDS(LLVMPull.{timestamp_column}),
        DAY
    ) AS age_in_days
  FROM {OPERATIONAL_METRICS_DATASET}.{LLVM_PULL_REQUESTS_TABLE} AS LLVMPull
  WHERE
    {predicate}
  GROUP BY age_in_days
  HAVING
    age_in_days >= @minimum_age_days
    AND age_in_days < @maximum_age_days
  """
  job_config = bigquery.QueryJobConfig(
      query_parameters=[
          bigquery.ScalarQueryParameter(
              "minimum_age_days", "INT64", minimum_age_days
          ),
          bigquery.ScalarQueryParameter(
              "maximum_age_days", "INT64", maximum_age_days
          ),
      ],
  )
  return {
      row.age_in_days: row.pull_request_numbers
      for row in bq_client.query(query, job_config=job_config).result()
  }


def mark_stale_pull_request_data_in_bigquery(
    bq_client: bigquery.Client,
    cutoff_age_days: int,
) -> None:
  """Mark stale pull requests in BigQuery once they exceed the cutoff age.

  Args:
    bq_client: The BigQuery client to use for querying.
    cutoff_age_days: The number of days to look back for outdated pull requests.
  """
  query = f"""
  UPDATE {OPERATIONAL_METRICS_DATASET}.{LLVM_PULL_REQUESTS_TABLE}
  SET is_stale_data = true
  WHERE
    pull_request_state = 'OPEN'
    AND TIMESTAMP_DIFF(
        CURRENT_TIMESTAMP(),
        TIMESTAMP_SECONDS(last_updated_at_timestamp_seconds),
        DAY
    ) > @cutoff_age_days
  """
  job_config = bigquery.QueryJobConfig(
      query_parameters=[
          bigquery.ScalarQueryParameter(
              "cutoff_age_days", "INT64", cutoff_age_days
          ),
      ],
  )
  bq_client.query(query, job_config=job_config).result()


def query_pull_request_data_from_github(
    pull_request_numbers: list[int],
    github_token: str,
) -> list[dict[str, Any]]:
  """Query the GitHub GraphQL API for pull request data.

  Args:
    pull_request_numbers: List of pull request numbers to query.
    github_token: The GitHub API token to use for authentication.

  Returns:
    List of pull request data from the GitHub GraphQL API.
  """
  # Build subqueries for each pull request.
  pull_request_subqueries = []
  for pull_request_number in pull_request_numbers:
    subquery = """
    pull_request_{pull_request_number}:
      pullRequest(number:{pull_request_number}) {{
        ... on PullRequest {{
          {pull_request_graphql_data}
        }}
      }}
    """.format(
        pull_request_number=pull_request_number,
        pull_request_graphql_data=operational_metrics_lib.PULL_REQUEST_GRAPHQL_DATA,
    )
    pull_request_subqueries.append(subquery)

  # Query the Github GraphQL API
  pull_request_data = operational_metrics_lib.fetch_repository_data_from_github(
      github_token=github_token,
      subqueries=pull_request_subqueries,
  )

  return [pull_request for _, pull_request in pull_request_data.items()]


def upload_github_data_to_bigquery(
    bq_client: bigquery.Client,
    pull_request_data: list[dict[str, Any]],
) -> None:
  """Parse and upload GitHub API data to BigQuery.

  Duplicate data will not be uploaded, existing records will instead be updated
  with any new information contained pull_request_data.

  Args:
    bq_client: The BigQuery client to use for querying.
    pull_request_data: The pull request data to be uploaded.
  """
  parsed_pull_requests = [
      operational_metrics_lib.parse_pull_request_data(pull_request)
      for pull_request in pull_request_data
  ]
  parsed_reviews = []
  for pull_request in pull_request_data:
    parsed_reviews.extend(
        operational_metrics_lib.parse_review_data(pull_request)
    )

  operational_metrics_lib.upload_to_bigquery(
      bq_client,
      OPERATIONAL_METRICS_DATASET,
      LLVM_PULL_REQUESTS_TABLE,
      parsed_pull_requests,
      "pull_request_number",
  )
  operational_metrics_lib.upload_to_bigquery(
      bq_client,
      OPERATIONAL_METRICS_DATASET,
      LLVM_REVIEWS_TABLE,
      parsed_reviews,
      "review_id",
  )


def sync_recent_pull_requests_to_bigquery(
    bq_client: bigquery.Client,
    github_token: str,
) -> None:
  """Sync recent, not-yet-recorded pull requests with BigQuery.

  Args:
    bq_client: The BigQuery client to use for querying.
    github_token: The GitHub API token to use for authentication.
  """
  # Fetch open pull requests that have not been recorded yet.
  time_now = datetime.datetime.now(datetime.timezone.utc)
  cutoff_timestamp = time_now - datetime.timedelta(hours=LOOKBACK_HOURS)
  logging.info("Fetching open pull requests created after %s", cutoff_timestamp)
  pull_request_data = fetch_open_pull_requests_from_github(
      github_token=github_token,
      cutoff_timestamp=cutoff_timestamp,
  )

  if not pull_request_data:
    logging.info(
        "No new pull requests within the last %d hours found.", LOOKBACK_HOURS
    )
    return

  # Upload fetched pull requests and reviews to BigQuery.
  logging.info(
      "Uploading %d open pull requests to BigQuery.", len(pull_request_data)
  )
  upload_github_data_to_bigquery(
      bq_client,
      pull_request_data,
  )


def update_open_pull_requests_in_bigquery(
    bq_client: bigquery.Client,
    github_token: str,
) -> None:
  """Update data for open pull requests already recorded in BigQuery.

  Args:
    bq_client: The BigQuery client to use for querying.
    github_token: The GitHub API token to use for authentication.
  """

  # Fetch potential updates for already recorded pull requests that are open.
  open_pull_requests_by_age = get_pull_requests_by_age_from_bigquery(
      bq_client,
      predicate=OPEN_PULL_REQUEST_PREDICATE,
      timestamp_column="pull_request_timestamp_seconds",
      minimum_age_days=0,
      maximum_age_days=180,  # Six months
  )
  recorded_open_pull_requests = []
  for _, pull_request_numbers in open_pull_requests_by_age.items():
    recorded_open_pull_requests.extend(pull_request_numbers)
  pull_request_data = query_pull_request_data_from_github(
      recorded_open_pull_requests, github_token
  )

  # Parse and upload amended pull request and review data to BigQuery.
  logging.info(
      "Uploading amendments for %d open pull requests.",
      len(recorded_open_pull_requests),
  )
  upload_github_data_to_bigquery(
      bq_client,
      pull_request_data,
  )


def update_post_commit_reviews_in_bigquery(
    bq_client: bigquery.Client,
    github_token: str,
) -> None:
  """Update data for pull requests requiring post-commit review.

  Args:
    bq_client: The BigQuery client to use for querying.
    github_token: The GitHub API token to use for authentication.
  """
  # After two weeks, a merged pull request is most likely not going to receive
  # any more reviews.
  unapproved_merged_pull_requests_by_age = (
      get_pull_requests_by_age_from_bigquery(
          bq_client,
          predicate=UNAPPROVED_PULL_REQUEST_PREDICATE,
          timestamp_column="merged_at_timestamp_seconds",
          minimum_age_days=0,
          maximum_age_days=14,
      )
  )
  unapproved_merged_pull_requests = []
  for _, pull_request_numbers in unapproved_merged_pull_requests_by_age.items():
    unapproved_merged_pull_requests.extend(pull_request_numbers)
  pull_request_data = query_pull_request_data_from_github(
      unapproved_merged_pull_requests, github_token
  )

  logging.info(
      "Uploading amended post-commit reviews for %d pull requests.",
      len(unapproved_merged_pull_requests),
  )
  upload_github_data_to_bigquery(
      bq_client,
      pull_request_data,
  )


def record_repository_snapshot_in_bigquery(
    bq_client: bigquery.Client,
) -> None:
  """Record a snapshot of the repository's current state in BigQuery.

  Args:
    bq_client: The BigQuery client to use for querying.
  """
  snapshot_timestamp_seconds = int(
      datetime.datetime.now(datetime.timezone.utc).timestamp()
  )
  open_pull_requests_by_age = get_pull_requests_by_age_from_bigquery(
      bq_client,
      predicate=OPEN_PULL_REQUEST_PREDICATE,
      timestamp_column="pull_request_timestamp_seconds",
      minimum_age_days=0,
      maximum_age_days=180,  # Six months
  )
  open_pull_request_count_by_age = [
      {"age_in_days": age, "pull_request_count": len(pull_request_numbers)}
      for age, pull_request_numbers in open_pull_requests_by_age.items()
  ]
  unapproved_pull_requests_by_age = get_pull_requests_by_age_from_bigquery(
      bq_client,
      predicate=UNAPPROVED_PULL_REQUEST_PREDICATE,
      timestamp_column="merged_at_timestamp_seconds",
      minimum_age_days=0,
      maximum_age_days=180,  # Six months
  )
  unapproved_pull_request_count_by_age = [
      {"age_in_days": age, "pull_request_count": len(pull_request_numbers)}
      for age, pull_request_numbers in unapproved_pull_requests_by_age.items()
  ]

  operational_metrics_lib.upload_to_bigquery(
      bq_client,
      OPERATIONAL_METRICS_DATASET,
      LLVM_REPOSITORY_SNAPSHOT_TABLE,
      [
          operational_metrics_lib.LLVMRepositorySnapshot(
              snapshot_timestamp_seconds=snapshot_timestamp_seconds,
              open_pull_request_count_by_age=open_pull_request_count_by_age,
              unapproved_pull_request_count_by_age=unapproved_pull_request_count_by_age,
          )
      ],
      "snapshot_timestamp_seconds",
  )


def main():
  github_token = os.environ["GITHUB_TOKEN"]
  bq_client = bigquery.Client()

  logging.info("Syncing recent pull requests to BigQuery.")
  sync_recent_pull_requests_to_bigquery(bq_client, github_token)

  # We don't want to amend data for pull requests that have been open for more
  # than two weeks.
  logging.info("Marking stale pull requests in BigQuery.")
  mark_stale_pull_request_data_in_bigquery(
      bq_client,
      cutoff_age_days=14,
  )

  logging.info("Updating open pull requests in BigQuery.")
  update_open_pull_requests_in_bigquery(bq_client, github_token)

  logging.info("Updating post-commit reviews in BigQuery.")
  update_post_commit_reviews_in_bigquery(bq_client, github_token)

  logging.info("Recording repository snapshot in BigQuery.")
  record_repository_snapshot_in_bigquery(bq_client)

  bq_client.close()


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  main()
