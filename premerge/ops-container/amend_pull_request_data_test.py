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

  def test_get_open_pull_requests_from_bigquery(self):
    """Test getting open pull requests from BigQuery."""
    mock_bq_client = unittest.mock.MagicMock()
    mock_bq_query_job = unittest.mock.MagicMock()
    mock_bq_query_job.result.return_value = [
        self._create_mock_bq_row(1234),
        self._create_mock_bq_row(5678),
    ]
    mock_bq_client.query.return_value = mock_bq_query_job

    result = amend_pull_request_data.get_open_pull_requests_from_bigquery(
        mock_bq_client
    )
    mock_bq_client.query.assert_called_once()
    executed_query = mock_bq_client.query.call_args.args[0]
    self.assertIn("SELECT pull_request_number", executed_query)
    self.assertRegex(executed_query, r"WHERE\s+pull_request_state = 'OPEN'")
    self.assertEqual(result, [1234, 5678])

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

  def test_get_unapproved_pull_requests_from_bigquery(self):
    """Test getting unapproved pull requests from BigQuery."""
    mock_bq_client = unittest.mock.MagicMock()
    mock_bq_query_job = unittest.mock.MagicMock()
    mock_bq_query_job.result.return_value = [
        self._create_mock_bq_row(1234),
        self._create_mock_bq_row(5678),
    ]
    mock_bq_client.query.return_value = mock_bq_query_job

    result = amend_pull_request_data.get_unapproved_pull_requests_from_bigquery(
        mock_bq_client,
        minimum_age_days=0,
        maximum_age_days=14,
    )
    job_config = mock_bq_client.query.call_args.kwargs["job_config"]
    min_parameter, max_parameter = job_config.query_parameters

    mock_bq_client.query.assert_called_once()
    executed_query = mock_bq_client.query.call_args.args[0]
    self.assertRegex(executed_query, r"SELECT\s+(.+.)?pull_request_number")
    self.assertRegex(
        executed_query, r"WHERE\s+(.+.)?pull_request_state = 'MERGED'"
    )
    self.assertEqual(min_parameter.name, "minimum_age_days")
    self.assertEqual(min_parameter.value, 0)
    self.assertEqual(max_parameter.name, "maximum_age_days")
    self.assertEqual(max_parameter.value, 14)
    self.assertEqual(result, [1234, 5678])

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
