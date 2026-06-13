import datetime
from typing import Any
import unittest
import unittest.mock

import amend_pull_request_data
import operational_metrics_lib


class TestAmendPullRequestData(unittest.TestCase):

  def _create_mock_bq_row(
      self, pull_request_number: int
  ) -> unittest.mock.MagicMock:
    """Creates a mock row for BigQuery."""
    mock_row = unittest.mock.MagicMock()
    mock_row.pull_request_number = pull_request_number
    return mock_row

  def _create_mock_graphql_response(
      self,
      nodes: list[dict[str, Any]],
      has_next_page: bool = False,
      end_cursor: str | None = None,
  ) -> unittest.mock.MagicMock:
    """Creates a mock response for the GitHub GraphQL API."""
    mock_response = unittest.mock.MagicMock()
    mock_response.json.return_value = {
        "data": {
            "search": {
                "nodes": nodes,
                "pageInfo": {
                    "hasNextPage": has_next_page,
                    "endCursor": end_cursor,
                },
            }
        }
    }
    return mock_response

  @unittest.mock.patch.object(
      operational_metrics_lib, "query_github_graphql_api"
  )
  def test_fetch_open_pull_requests_from_github(
      self, mock_query_github_graphql_api
  ):
    """Test fetching open pull requests from GitHub, with pagination."""
    mock_response_1 = self._create_mock_graphql_response(
        nodes=[{"number": 1234}], has_next_page=True, end_cursor="cursor1"
    )
    mock_response_2 = self._create_mock_graphql_response(
        nodes=[{"number": 5678}], has_next_page=False, end_cursor=None
    )
    mock_query_github_graphql_api.side_effect = [
        mock_response_1,
        mock_response_2,
    ]

    cutoff_timestamp = datetime.datetime.now() - datetime.timedelta(hours=2)
    pull_requests = (
        amend_pull_request_data.fetch_open_pull_requests_from_github(
            github_token="dummy_token",
            cutoff_timestamp=cutoff_timestamp,
        )
    )
    self.assertEqual(pull_requests, [{"number": 1234}, {"number": 5678}])
    self.assertEqual(mock_query_github_graphql_api.call_count, 2)

  def test_mark_stale_pull_request_data_in_bigquery(self):
    """Test marking stale pull request data in BigQuery."""
    mock_bq_client = unittest.mock.MagicMock()
    mock_bq_query_job = unittest.mock.MagicMock()
    mock_bq_client.query.return_value = mock_bq_query_job

    amend_pull_request_data.mark_stale_pull_request_data_in_bigquery(
        mock_bq_client,
        cutoff_age_days=14,
    )
    job_config = mock_bq_client.query.call_args.kwargs["job_config"]
    query_parameters = job_config.query_parameters[0]

    mock_bq_client.query.assert_called_once()
    executed_query = mock_bq_client.query.call_args.args[0]
    self.assertIn("SET is_stale_data = true", executed_query)
    self.assertRegex(executed_query, r"WHERE\s+pull_request_state = 'OPEN'")
    self.assertEqual(query_parameters.name, "cutoff_age_days")
    self.assertEqual(query_parameters.value, 14)

  def test_get_pull_requests_by_age_from_bigquery(self):
    """Test getting pull requests grouped by age from BigQuery."""
    mock_bq_client = unittest.mock.MagicMock()
    mock_bq_query_job = unittest.mock.MagicMock()

    mock_row_1 = unittest.mock.MagicMock()
    mock_row_1.age_in_days = 2
    mock_row_1.pull_request_numbers = [1111, 2222]

    mock_row_2 = unittest.mock.MagicMock()
    mock_row_2.age_in_days = 5
    mock_row_2.pull_request_numbers = [3333]

    mock_bq_query_job.result.return_value = [mock_row_1, mock_row_2]
    mock_bq_client.query.return_value = mock_bq_query_job

    result = amend_pull_request_data.get_pull_requests_by_age_from_bigquery(
        bq_client=mock_bq_client,
        predicate="mock_column = 'MOCK_VALUE'",
        timestamp_column="mock_timestamp_seconds",
        minimum_age_days=0,
        maximum_age_days=14,
    )

    mock_bq_client.query.assert_called_once()

    # Check query string formatting
    executed_query = mock_bq_client.query.call_args.args[0]
    self.assertIn("mock_column = 'MOCK_VALUE'", executed_query)
    self.assertIn(
        "TIMESTAMP_SECONDS(LLVMPull.mock_timestamp_seconds)", executed_query
    )
    self.assertIn("ARRAY_AGG(DISTINCT pull_request_number)", executed_query)

    # Check query arguments
    job_config = mock_bq_client.query.call_args.kwargs["job_config"]
    query_parameters = {
        param.name: param.value for param in job_config.query_parameters
    }
    self.assertEqual(query_parameters["minimum_age_days"], 0)
    self.assertEqual(query_parameters["maximum_age_days"], 14)

    # Check results
    expected_result = {
        2: [1111, 2222],
        5: [3333],
    }
    self.assertEqual(result, expected_result)

  @unittest.mock.patch.object(
      operational_metrics_lib, "fetch_repository_data_from_github"
  )
  def test_query_pull_request_data_from_github(
      self, mock_fetch_repository_data_from_github
  ):
    """Test querying pull request data from GitHub."""
    mock_fetch_repository_data_from_github.return_value = {
        "pr_1234": {"number": 1234},
        "pr_5678": {"number": 5678},
    }

    result = amend_pull_request_data.query_pull_request_data_from_github(
        pull_request_numbers=[1234, 5678],
        github_token="dummy_token",
    )
    call_kwargs = mock_fetch_repository_data_from_github.call_args.kwargs

    self.assertEqual(mock_fetch_repository_data_from_github.call_count, 1)
    self.assertEqual(len(call_kwargs["subqueries"]), 2)
    self.assertEqual(result, [{"number": 1234}, {"number": 5678}])

  @unittest.mock.patch.object(
      operational_metrics_lib, "parse_pull_request_data"
  )
  @unittest.mock.patch.object(operational_metrics_lib, "parse_review_data")
  @unittest.mock.patch.object(operational_metrics_lib, "upload_to_bigquery")
  def test_upload_github_data_to_bigquery(
      self,
      mock_upload_to_bigquery,
      mock_parse_review_data,
      mock_parse_pull_request_data,
  ):
    """Test uploading GitHub data to BigQuery."""
    mock_bq_client = unittest.mock.MagicMock()
    mock_parse_pull_request_data.return_value = "parsed_pull_request_data"
    mock_parse_review_data.return_value = ["parsed_review_data"]

    amend_pull_request_data.upload_github_data_to_bigquery(
        mock_bq_client,
        pull_request_data=[{"number": 1234}],
    )

    mock_parse_pull_request_data.assert_called_once_with({"number": 1234})
    mock_parse_review_data.assert_called_once_with({"number": 1234})
    mock_upload_to_bigquery.assert_any_call(
        mock_bq_client,
        amend_pull_request_data.OPERATIONAL_METRICS_DATASET,
        amend_pull_request_data.LLVM_PULL_REQUESTS_TABLE,
        ["parsed_pull_request_data"],
        "pull_request_number",
    )
    mock_upload_to_bigquery.assert_any_call(
        mock_bq_client,
        amend_pull_request_data.OPERATIONAL_METRICS_DATASET,
        amend_pull_request_data.LLVM_REVIEWS_TABLE,
        ["parsed_review_data"],
        "review_id",
    )


if __name__ == "__main__":
  unittest.main()
