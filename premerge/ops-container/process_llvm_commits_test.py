import dataclasses
import datetime
from typing import Any
import unittest
import unittest.mock

import parameterized
import process_llvm_commits
import requests


class TestProcessLLVMCommits(unittest.TestCase):

  def _create_mock_commit(
      self,
      hexsha: str = 'abcdef',
      message: str = 'Commit message.',
      committed_date: int = 10000000,
      stats: dict[str, dict[str, int]] | None = None,
  ) -> unittest.mock.MagicMock:
    """Creates a mock repository commit."""
    commit = unittest.mock.MagicMock()
    commit.hexsha = hexsha
    commit.committed_date = committed_date
    commit.stats.files = stats or {
        'foo.c': {'insertions': 1, 'deletions': 2, 'lines': 3}
    }
    commit.message = message
    return commit

  def _create_llvm_commit_data(
      self, commit_sha: str = 'abcdef'
  ) -> process_llvm_commits.LLVMCommitData:
    """Creates a basic LLVMCommitData object."""
    return process_llvm_commits.LLVMCommitData(
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

  def _create_commit_api_data(
      self,
      commit_author: str | None = None,
      has_pull_request: bool = False,
      pull_request_number: int = 0,
      reviews: list[dict[str, Any]] | None = None,
  ) -> dict[str, Any]:
    """Create a GitHub API response for a commit."""
    api_data = {
        'author': {'user': None},
        'associatedPullRequests': {'totalCount': 0},
    }

    if commit_author:
      api_data['author']['user'] = {'login': commit_author}

    if has_pull_request:
      api_data['associatedPullRequests']['totalCount'] = 1
      api_data['associatedPullRequests']['pullRequest'] = [{
          'number': pull_request_number,
          'reviews': {'nodes': reviews or []},
      }]

    return api_data

  @parameterized.parameterized.expand([
      ('Foo', False, None, None),
      ('Revert "Foo"', True, None, None),
      ('Revert "Foo" (#123)\nRevert llvm/llvm-project#123', True, 123, None),
      ('Revert "Foo" (#456)\nReverts #456', True, 456, None),
      ('Revert "Foo"\nThis reverts commit abcdef', True, None, 'abcdef'),
      (
          'Revert "Foo"\nRevert #678\nThis reverts commit abcdef',
          True,
          678,
          'abcdef',
      ),
  ])
  def test_parse_commit_revert_info(
      self,
      msg: str,
      expected_is_revert: bool,
      expected_pr_reverted: int | None,
      expected_commit_reverted: str | None,
  ):
    """Test parsing of commit revert information based on commit messages."""
    is_revert, pr_reverted, commit_reverted = (
        process_llvm_commits.parse_commit_revert_info(msg)
    )
    self.assertEqual(is_revert, expected_is_revert)
    self.assertEqual(pr_reverted, expected_pr_reverted)
    self.assertEqual(commit_reverted, expected_commit_reverted)

  def test_scrape_commits_by_date(self):
    """Testing scraping of commits by date in different timezones."""
    # Target date is 10/10/23 00:00 UTC
    target_datetime = datetime.datetime(
        year=2023, month=10, day=10, tzinfo=datetime.timezone.utc
    )

    # 10/10/23 07:00 UTC, should be included
    commit_utc = unittest.mock.MagicMock()
    commit_utc.committed_datetime = datetime.datetime(
        year=2023, month=10, day=10, hour=7, tzinfo=datetime.timezone.utc
    )

    # Different timezone, same commit date
    # This commit is on 10/10/23 07:00 EST, which is 10/10/23 12:00 UTC, so it
    # should be included.
    est_tz = datetime.timezone(datetime.timedelta(hours=-5), name='EST')
    commit_est = unittest.mock.MagicMock()
    commit_est.committed_datetime = datetime.datetime(
        year=2023, month=10, day=10, hour=7, tzinfo=est_tz
    )

    # Different timezone, different commit date
    # This commit is on 10/10/23 23:00 PST, which is 10/11/23 07:00 UTC, so it
    # should be filtered out.
    pst_tz = datetime.timezone(datetime.timedelta(hours=-8), name='PST')
    commit_pst = unittest.mock.MagicMock()
    commit_pst.committed_datetime = datetime.datetime(
        year=2023, month=10, day=10, hour=23, tzinfo=pst_tz
    )

    repo = unittest.mock.MagicMock()
    repo.iter_commits.return_value = [commit_utc, commit_est, commit_pst]

    commits = process_llvm_commits.scrape_commits_by_date(repo, target_datetime)

    self.assertEqual(len(commits), 2)
    self.assertIn(commit_utc, commits)
    self.assertIn(commit_est, commits)
    self.assertNotIn(commit_pst, commits)

  def test_extract_initial_commit_data(self):
    """Test that initial commit data is being extracted from scraped commits."""
    commit = self._create_mock_commit(
        hexsha='abcdef',
        message='Change to foo.c',
        committed_date=100,
        stats={'foo.c': {'insertions': 1, 'deletions': 2, 'lines': 3}},
    )

    commit_data = process_llvm_commits.extract_initial_commit_data(commit)

    self.assertEqual(commit_data.commit_sha, 'abcdef')
    self.assertEqual(commit_data.commit_timestamp_seconds, 100)
    self.assertEqual(
        commit_data.diff,
        [{
            'file': 'foo.c',
            'additions': 1,
            'deletions': 2,
            'total': 3,
        }],
    )
    self.assertFalse(commit_data.is_revert)
    self.assertIsNone(commit_data.pull_request_reverted)
    self.assertIsNone(commit_data.commit_reverted)

  def test_extract_initial_commit_data_with_revert_data(self):
    """Test that initial commit data includes revert data when present."""
    commit = self._create_mock_commit(
        hexsha='abcdef',
        message='Revert "Foo" (#123)\nRevert llvm/llvm-project#123',
        committed_date=100,
        stats={'foo.c': {'insertions': 1, 'deletions': 2, 'lines': 3}},
    )

    commit_data = process_llvm_commits.extract_initial_commit_data(commit)

    self.assertTrue(commit_data.is_revert)
    self.assertEqual(commit_data.pull_request_reverted, 123)
    self.assertIsNone(commit_data.commit_reverted)

  @unittest.mock.patch.object(requests, 'post', autospec=True)
  def test_query_github_graphql_api_success(self, mock_post):
    """Test querying against the GitHub GraphQL API."""
    mock_post.return_value = self._create_mock_api_response()

    _ = process_llvm_commits.query_github_graphql_api(
        'dummy_query', 'dummy_token'
    )

    _, mock_kwargs = mock_post.call_args
    mock_post.assert_called_once()
    self.assertEqual(mock_kwargs['json'], {'query': 'dummy_query'})
    self.assertEqual(
        mock_kwargs['headers'], {'Authorization': 'bearer dummy_token'}
    )

  @unittest.mock.patch.object(requests, 'post', autospec=True)
  def test_query_github_graphql_api_with_http_error_retries(self, mock_post):
    """Test querying against the GitHub GraphQL API resulting in an HTTP error."""
    mock_post.return_value = self._create_mock_api_response(status_code=404)

    with self.assertLogs(level='WARNING'):
      with self.assertRaises(requests.exceptions.HTTPError):
        with unittest.mock.patch('time.sleep'):  # Avoid sleep in unit test
          _ = process_llvm_commits.query_github_graphql_api(
              'dummy_query', 'dummy_token'
          )

    # Assert that the post was retried at least once
    self.assertGreater(mock_post.call_count, 1)

  @unittest.mock.patch.object(requests, 'post', autospec=True)
  def test_fetch_github_api_data(self, mock_post):
    """Test fetching GitHub API data for a list of commits."""
    response_payload = {
        'data': {'repository': {'commit_abcdef': {}, 'commit_ghijkl': {}}}
    }
    mock_post.return_value = self._create_mock_api_response(
        payload=response_payload
    )

    api_data = process_llvm_commits.fetch_github_api_data(
        github_token='dummy_token',
        commit_hashes=['abcdef', 'ghijkl'],
    )

    _, mock_kwargs = mock_post.call_args
    mock_post.assert_called_once()
    self.assertEqual(len(api_data), 2)
    self.assertIn('commit_abcdef', mock_kwargs['json']['query'])
    self.assertIn('commit_ghijkl', mock_kwargs['json']['query'])

  @unittest.mock.patch.object(requests, 'post', autospec=True)
  def test_fetch_github_api_data_batching(self, mock_post):
    """Test fetching GitHub API data in batches at a time."""
    response_payload = {'data': {'repository': {}}}
    mock_post.return_value = self._create_mock_api_response(
        payload=response_payload
    )

    # Require 3 batches to query 50 commits
    commit_hashes = [str(i) for i in range(50)]
    batch_size = 24

    _ = process_llvm_commits.fetch_github_api_data(
        github_token='dummy_token',
        commit_hashes=commit_hashes,
        batch_size=batch_size,
    )

    self.assertEqual(mock_post.call_count, 3)

  def test_amend_commit_data_captures_author(self):
    """Test that author is captured when amending commit data."""
    commit_data = self._create_llvm_commit_data(commit_sha='abcdef')
    api_data = self._create_commit_api_data(commit_author='commit_author')

    process_llvm_commits.amend_commit_data(commit_data, api_data)

    self.assertEqual(commit_data.commit_author, 'commit_author')

  def test_amend_commit_data_with_missing_author(self):
    """Test that missing author in API commit data is handled gracefully."""
    commit_data = self._create_llvm_commit_data(commit_sha='abcdef')
    api_data = self._create_commit_api_data(commit_author=None)

    with self.assertLogs(level='WARNING'):
      process_llvm_commits.amend_commit_data(commit_data, api_data)
    self.assertIsNone(commit_data.commit_author)

  def test_amend_commit_data_captures_pull_request(self):
    """Test that pull request data is captured when amending commit data."""
    commit_data = self._create_llvm_commit_data(commit_sha='abcdef')
    api_data = self._create_commit_api_data(
        commit_author='commit_author',
        has_pull_request=True,
        pull_request_number=12345,
    )

    process_llvm_commits.amend_commit_data(commit_data, api_data)

    self.assertTrue(commit_data.has_pull_request)
    self.assertEqual(commit_data.pull_request_number, 12345)

  def test_amend_commit_data_captures_reviews(self):
    """Test that review data is captured when amending commit data."""
    commit_data = self._create_llvm_commit_data(commit_sha='abcdef')
    api_data = self._create_commit_api_data(
        commit_author='commit_author',
        has_pull_request=True,
        pull_request_number=12345,
        reviews=[
            {'state': 'APPROVED', 'reviewer': {'login': 'reviewer_1'}},
            {'state': 'COMMENTED', 'reviewer': {'login': 'commit_author'}},
        ],
    )

    process_llvm_commits.amend_commit_data(commit_data, api_data)

    self.assertTrue(commit_data.is_reviewed)
    self.assertTrue(commit_data.is_approved)
    self.assertNotIn('commit_author', commit_data.reviewers)

  @unittest.mock.patch.object(requests, 'post', autospec=True)
  def test_build_commit_data(self, mock_post):
    """Test building complete commit data for a list of commits."""
    commit_one = self._create_mock_commit(hexsha='abcdef')
    commit_two = self._create_mock_commit(hexsha='ghijkl')
    commit_one_api_data = self._create_commit_api_data(
        commit_author='commit_author'
    )
    commit_two_api_data = self._create_commit_api_data(
        commit_author='commit_author'
    )
    response_payload = {
        'data': {
            'repository': {
                'commit_abcdef': commit_one_api_data,
                'commit_ghijkl': commit_two_api_data,
            }
        }
    }
    mock_post.return_value = self._create_mock_api_response(
        payload=response_payload
    )

    commit_data = process_llvm_commits.build_commit_data(
        commits=[commit_one, commit_two], github_token='dummy_token'
    )

    self.assertEqual(len(commit_data), 2)
    self.assertIsInstance(commit_data[0], process_llvm_commits.LLVMCommitData)
    self.assertIsInstance(commit_data[1], process_llvm_commits.LLVMCommitData)
    self.assertIn(
        commit_one.hexsha, [commit.commit_sha for commit in commit_data]
    )
    self.assertIn(
        commit_two.hexsha, [commit.commit_sha for commit in commit_data]
    )

  def test_upload_daily_metrics_to_bigquery(self):
    """Test uploading commit data to BigQuery."""
    mock_bq_client = unittest.mock.MagicMock()
    mock_table = unittest.mock.MagicMock()

    mock_bq_client.get_table.return_value = mock_table
    mock_bq_client.insert_rows.return_value = []  # No errors

    commit_data = self._create_llvm_commit_data(commit_sha='abcdef')
    expected_commit_record = dataclasses.asdict(commit_data)

    process_llvm_commits.upload_daily_metrics_to_bigquery(
        mock_bq_client,
        [commit_data],
    )

    mock_bq_client.insert_rows.assert_called_once_with(
        table=mock_table, rows=[expected_commit_record]
    )

  def test_upload_daily_metrics_to_bigquery_exits_on_error(self):
    """Test uploading commit data to BigQuery resulting in errors."""
    mock_bq_client = unittest.mock.MagicMock()
    mock_bq_client.insert_rows.return_value = ['Error']

    with self.assertLogs(level='ERROR'):
      with self.assertRaises(SystemExit):
        process_llvm_commits.upload_daily_metrics_to_bigquery(
            mock_bq_client,
            commits_data=[self._create_llvm_commit_data(commit_sha='abcdef')],
        )


if __name__ == '__main__':
  unittest.main()
