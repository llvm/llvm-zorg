import dataclasses
import datetime
import logging
import math
from typing import Any, TypeAlias
from google.cloud import bigquery
import requests
import retry


GITHUB_GRAPHQL_API_URL = "https://api.github.com/graphql"

# How many subqueries to query the GitHub GraphQL API for at a time.
# Querying too many subqueries at once often leads to the call failing.
DEFAULT_GITHUB_API_BATCH_SIZE = 35

PULL_REQUEST_GRAPHQL_DATA = """
author {
  login
}
title
number
state
createdAt
updatedAt
mergedAt
label_events: timelineItems(last: 10, itemTypes: [LABELED_EVENT]) {
  nodes {
    ... on LabeledEvent {
      createdAt
      label {
        name
      }
    }
  }
}
reviewRequests(first: 10) {
  nodes {
    requestedReviewer {
      ... on User {
        login
      }
    }
  }
}
reviews(last: 100) {
  nodes {
    state
    reviewID: id
    createdAt
    reviewer: author {
      login
    }
  }
}
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
  pull_request_title: str
  pull_request_state: str
  pull_request_timestamp_seconds: int
  last_updated_at_timestamp_seconds: int
  merged_at_timestamp_seconds: int | None
  associated_commits: list[str]
  labels: list[dict[str, str]]
  requested_reviewers: list[str]
  is_stale_data: bool = False  # Used to avoid amending outdated data (>14 days)


@dataclasses.dataclass
class LLVMReviewData:
  review_id: str
  review_author: str
  review_timestamp_seconds: int
  review_state: str
  associated_pull_request: int


@dataclasses.dataclass
class LLVMRepositorySnapshot:
  snapshot_timestamp_seconds: int
  open_pull_request_count: int
  recent_unapproved_pull_request_count: int
  stale_unapproved_pull_request_count: int


LLVMData: TypeAlias = (
    LLVMCommitData
    | LLVMPullRequestData
    | LLVMReviewData
    | LLVMRepositorySnapshot
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
    variables: dict[str, str] | None = None,
) -> requests.Response:
  """Query GitHub GraphQL API, retrying on failure.

  Args:
    query: The GraphQL query to send to the GitHub API.
    github_token: The access token to use with the GitHub GraphQL API.
    variables: The variables to use with the GraphQL query.

  Returns:
    The response from the GitHub GraphQL API.
  """
  variables = variables or {}
  response = requests.post(
      url=GITHUB_GRAPHQL_API_URL,
      headers={
          "Authorization": f"bearer {github_token}",
      },
      json={"query": query, "variables": variables},
  )
  # Exit if API call fails
  # A failed API call means a large batch of data is missing and will not be
  # reflected in the dashboard. The dashboard will silently misrepresent
  # commit data if we continue execution, so it's better to fail loudly.
  response.raise_for_status()

  return response


def fetch_repository_data_from_github(
    github_token: str,
    subqueries: list[str],
    batch_size: int = DEFAULT_GITHUB_API_BATCH_SIZE,
) -> dict[str, dict[str, Any]]:
  """Fetch repository data from the GitHub API using provided subqueries.

  Args:
    github_token: The access token to use with the GitHub GraphQL API.
    subqueries: List of GraphQL subqueries to fetch data for.
    batch_size: The number of commits to query the GitHub GraphQL API for at a
      time.

  Returns:
    A dictionary of commit hash to commit data from the GitHub GraphQL API.
  """
  api_subquery_results = {}
  query_template = """
    query {
      repository(owner:"llvm", name:"llvm-project"){
          %s
      }
    }
  """
  num_batches = math.ceil(len(subqueries) / batch_size)
  logging.info("Querying GitHub GraphQL API in %d batches", num_batches)
  for i in range(num_batches):
    subquery_batch = subqueries[i * batch_size : (i + 1) * batch_size]
    query = query_template % "".join(subquery_batch)

    logging.info(
        "Querying batch %d of %d (%d subqueries)",
        i + 1,
        num_batches,
        len(subquery_batch),
    )
    response = query_github_graphql_api(query, github_token)

    api_subquery_results.update(response.json()["data"]["repository"])

  return api_subquery_results


def parse_pull_request_data(
    pull_request: dict[str, Any],
    associated_commits: list[str] | None = None,
) -> LLVMPullRequestData:
  """Parse pull requests from the GitHub GraphQL API response.

  Args:
    pull_request: The JSON response for a single pull request from the GitHub
      GraphQL API.
    associated_commits: The commit hashes associated with this pull request.

  Returns:
    An LLVMPullRequestData object containing the parsed data.
  """
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
  updated_unix_timestamp = int(
      datetime.datetime.fromisoformat(pull_request["updatedAt"]).timestamp()
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
          "name": label_event["label"]["name"],
          "labeled_at_timestamp_seconds": int(
              datetime.datetime.fromisoformat(
                  label_event["createdAt"]
              ).timestamp()
          ),
      }
      for label_event in pull_request["label_events"]["nodes"]
  ]

  requested_reviewers = []
  for request in pull_request["reviewRequests"]["nodes"]:
    if request["requestedReviewer"] is not None:
      requested_reviewers.append(request["requestedReviewer"]["login"])
    else:
      logging.warning(
          "No login found for requested reviewer associated with pull"
          " request %d",
          pull_request["number"],
      )

  return LLVMPullRequestData(
      pull_request_number=pull_request["number"],
      pull_request_author=author_login,
      pull_request_title=pull_request["title"],
      pull_request_state=pull_request["state"],
      pull_request_timestamp_seconds=create_unix_timestamp,
      last_updated_at_timestamp_seconds=updated_unix_timestamp,
      merged_at_timestamp_seconds=merge_unix_timestamp,
      associated_commits=associated_commits or [],  # Avoid None values
      labels=labels,
      requested_reviewers=requested_reviewers,
  )


def parse_review_data(
    pull_request: dict[str, Any],
) -> list[LLVMReviewData]:
  """Extract review data from GitHub API data.

  Args:
    pull_request: JSON response for a single pull request from Github API.

  Returns:
    List of LLVMReviewData objects for each review found.
  """
  associated_pull_request = pull_request["number"]
  pull_request_author = (
      pull_request["author"]["login"] if pull_request["author"] else None
  )

  review_data = []
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
            review_id=review["reviewID"],
            review_author=reviewer_login,
            review_timestamp_seconds=unix_timestamp,
            review_state=review["state"].upper(),
            associated_pull_request=associated_pull_request,
        )
    )

  return review_data


def upload_to_bigquery(
    bq_client: bigquery.Client,
    bq_dataset: str,
    bq_table: str,
    llvm_data: list[LLVMData],
    primary_key: str,
) -> None:
  """Upload processed LLVM metrics to a BigQuery dataset.

  Args:
    bq_client: The BigQuery client to use.
    bq_dataset: The name of the BigQuery dataset to upload to.
    bq_table: The name of the BigQuery table to upload to.
    llvm_data: List of LLVM data to process & upload to BigQuery.
    primary_key: The name of the field to use as a primary key when merging
      pending data with existing records.
  """

  if not llvm_data:
    logging.info("No data to upload to BigQuery.")
    return

  target_table_id = f"{bq_dataset}.{bq_table}"
  staging_table_id = f"{target_table_id}_staging"

  records = [dataclasses.asdict(record) for record in llvm_data]
  fields = [field for field in records[0].keys()]

  update_values = ", ".join([f"dest.{field} = src.{field}" for field in fields])
  insert_values = ", ".join([f"src.{field}" for field in fields])

  query = f"""
  MERGE {target_table_id} AS dest
  USING {staging_table_id} AS src
  ON dest.{primary_key} = src.{primary_key}
  WHEN MATCHED THEN
    UPDATE SET {update_values}
  WHEN NOT MATCHED THEN
    INSERT ({", ".join(fields)}) VALUES ({insert_values})
  """

  try:
    bq_client.load_table_from_json(
        json_rows=records,
        destination=staging_table_id,
        job_config=bigquery.LoadJobConfig(
            schema=bq_client.get_table(target_table_id).schema,
            write_disposition="WRITE_TRUNCATE",
        ),
    ).result()

    bq_client.query(query).result()
  except Exception as e:
    logging.error("Failed to upload LLVM data to BigQuery: %s", e)
    exit(1)
  finally:
    bq_client.delete_table(staging_table_id, not_found_ok=True)
