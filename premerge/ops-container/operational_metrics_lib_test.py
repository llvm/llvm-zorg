import dataclasses
from typing import Any
import unittest
import unittest.mock

import operational_metrics_lib
import requests


class TestOperationalMetricsLib(unittest.TestCase):

  def _create_llvm_commit_data(
      self, commit_sha: str = 'abcdef'
  ) -> operational_metrics_lib.LLVMCommitData:
    """Creates a basic LLVMCommitData object."""
    return operational_metrics_lib.LLVMCommitData(
        commit_sha=commit_sha,
        commit_timestamp_seconds=10000000,
        diff=[],
    )

  def _create_mock_api_response(
      self, status_code: int = 200, payload: dict[str, Any] | None = None
  ) -> requests.Response:
    """Creates a mock API response."""
    response = requests.Response()
    response.status_code = status_code
    response.json = unittest.mock.MagicMock(
        return_value=payload if payload else {}
    )
    return response

  @unittest.mock.patch.object(requests, 'post', autospec=True)
  def test_query_github_graphql_api_success(self, mock_post):
    """Test querying against the GitHub GraphQL API."""
    mock_post.return_value = self._create_mock_api_response()

    _ = operational_metrics_lib.query_github_graphql_api(
        'dummy_query', 'dummy_token', variables={'x': 'y'}
    )

    _, mock_kwargs = mock_post.call_args
    mock_post.assert_called_once()
    self.assertEqual(
        mock_kwargs['json'], {'query': 'dummy_query', 'variables': {'x': 'y'}}
    )
    self.assertEqual(
        mock_kwargs['headers'], {'Authorization': 'bearer dummy_token'}
    )

  @unittest.mock.patch.object(requests, 'post', autospec=True)
  def test_query_github_graphql_api_with_http_error_retries(self, mock_post):
    """Test querying against the GitHub GraphQL API with in an HTTP error."""
    mock_post.return_value = self._create_mock_api_response(status_code=404)

    with self.assertLogs(level='WARNING'):
      with self.assertRaises(requests.exceptions.HTTPError):
        with unittest.mock.patch('time.sleep'):  # Avoid sleep in unit test
          _ = operational_metrics_lib.query_github_graphql_api(
              'dummy_query', 'dummy_token'
          )

    # Assert that the post was retried at least once
    self.assertGreater(mock_post.call_count, 1)

  @unittest.mock.patch.object(requests, 'post', autospec=True)
  def test_fetch_repository_data_from_github(self, mock_post):
    """Test fetching GitHub API data for a list of commits."""
    response_payload = {
        'data': {'repository': {'commit_abcdef': {}, 'commit_ghijkl': {}}}
    }
    mock_post.return_value = self._create_mock_api_response(
        payload=response_payload
    )

    subqueries = ['commit_abcdef: ...', 'commit_ghijkl: ...']

    api_data = operational_metrics_lib.fetch_repository_data_from_github(
        github_token='dummy_token',
        subqueries=subqueries,
    )

    _, mock_kwargs = mock_post.call_args
    mock_post.assert_called_once()
    self.assertEqual(len(api_data), 2)
    self.assertIn('commit_abcdef', mock_kwargs['json']['query'])
    self.assertIn('commit_ghijkl', mock_kwargs['json']['query'])

  @unittest.mock.patch.object(requests, 'post', autospec=True)
  def test_fetch_repository_data_from_github_batching(self, mock_post):
    """Test fetching GitHub API data in batches at a time."""
    response_payload = {'data': {'repository': {}}}
    mock_post.return_value = self._create_mock_api_response(
        payload=response_payload
    )

    # Require 3 batches to make 50 subqueries
    subqueries = [str(i) for i in range(50)]
    batch_size = 24

    _ = operational_metrics_lib.fetch_repository_data_from_github(
        github_token='dummy_token',
        subqueries=subqueries,
        batch_size=batch_size,
    )

    self.assertEqual(mock_post.call_count, 3)

  @unittest.mock.patch('uuid.uuid4')
  def test_upload_to_bigquery(self, mock_uuid4):
    """Test uploading commit data to BigQuery."""
    mock_uuid4_instance = unittest.mock.MagicMock()
    mock_uuid4_instance.hex = 'abc123'
    mock_uuid4.return_value = mock_uuid4_instance

    mock_bq_client = unittest.mock.MagicMock()
    mock_bq_table = unittest.mock.MagicMock()

    mock_bq_client.get_table.return_value = mock_bq_table
    mock_bq_table.schema = []

    commit_data = self._create_llvm_commit_data(commit_sha='abcdef')
    expected_commit_record = dataclasses.asdict(commit_data)

    operational_metrics_lib.upload_to_bigquery(
        bq_client=mock_bq_client,
        bq_dataset='mock_dataset',
        bq_table='mock_table',
        llvm_data=[commit_data],
        primary_key='commit_sha',
    )

    # Staging table
    mock_bq_client.load_table_from_json.assert_called_once()
    mock_bq_client.load_table_from_json.assert_called_once_with(
        json_rows=[expected_commit_record],
        destination='mock_dataset.mock_table_staging_abc123',
        job_config=unittest.mock.ANY,
    )

    # Merging
    mock_bq_client.query.assert_called_once()
    executed_query = mock_bq_client.query.call_args.args[0]
    self.assertIn('MERGE mock_dataset.mock_table', executed_query)
    self.assertIn(
        'USING mock_dataset.mock_table_staging_abc123', executed_query
    )
    self.assertIn('ON dest.commit_sha = src.commit_sha', executed_query)

    # Cleanup
    mock_bq_client.delete_table.assert_called_once_with(
        'mock_dataset.mock_table_staging_abc123',
        not_found_ok=True,
    )

  def test_upload_to_bigquery_exits_on_error(self):
    """Test uploading commit data to BigQuery resulting in errors."""
    mock_bq_client = unittest.mock.MagicMock()
    mock_bq_client.load_table_from_json.side_effect = Exception('Mock BQ Error')

    with self.assertLogs(level='ERROR'):
      with self.assertRaises(SystemExit):
        operational_metrics_lib.upload_to_bigquery(
            bq_client=mock_bq_client,
            bq_dataset='mock_dataset',
            bq_table='mock_table',
            llvm_data=[self._create_llvm_commit_data(commit_sha='abcdef')],
            primary_key='commit_sha',
        )


if __name__ == '__main__':
  unittest.main()
