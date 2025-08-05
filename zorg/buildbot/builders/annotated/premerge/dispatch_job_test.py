"""Tests for the dispatch_job.py script."""

import unittest
import datetime
import dateutil

import dispatch_job


class TestDispatchJobs(unittest.TestCase):
    def test_get_logs_first_time(self):
        """Test we return the correct logs if we have not seen any before."""
        log_lines = [
            "2025-07-29T15:48:00.259595535Z test1",
            "2025-07-29T15:48:00.383251277Z test2",
        ]
        current_timestamp = datetime.datetime.min
        latest_timestamp, lines_to_print = dispatch_job.get_logs_to_print(
            log_lines, current_timestamp
        )
        self.assertSequenceEqual(
            lines_to_print,
            [
                "2025-07-29T15:48:00.259595535Z test1",
                "2025-07-29T15:48:00.383251277Z test2",
            ],
        )
        self.assertEqual(
            latest_timestamp, dateutil.parser.parse("2025-07-29T15:48:00.383251277")
        )

    def test_get_logs_nonoverlapping(self):
        """Test we return the correct logs for non-overlapping ranges.

        Test that if the timestamp of the last log that we have printed is
        less than the current set returned by kubernetes, we return the correct
        lines.
        """
        log_lines = [
            "2025-07-29T15:48:01.787177054Z test1",
            "2025-07-29T15:48:03.074715108Z test2",
        ]
        current_timestamp = dateutil.parser.parse("2025-07-29T15:48:00.383251277")
        latest_timestamp, lines_to_print = dispatch_job.get_logs_to_print(
            log_lines, current_timestamp
        )
        self.assertSequenceEqual(
            lines_to_print,
            [
                "2025-07-29T15:48:01.787177054Z test1",
                "2025-07-29T15:48:03.074715108Z test2",
            ],
        )
        self.assertEqual(
            latest_timestamp, dateutil.parser.parse("2025-07-29T15:48:03.074715108")
        )

    def test_get_logs_overlapping(self):
        """Test we return the correct logs for overlapping ranges.

        Test that if the last line to be printed is contained within the logs
        kubernetes returned, we skip the lines that have already been printed.
        """
        log_lines = [
            "2025-07-29T15:48:00.383251277Z test1",
            "2025-07-29T15:48:01.787177054Z test2",
            "2025-07-29T15:48:03.074715108Z test3",
        ]
        current_timestamp = dateutil.parser.parse("2025-07-29T15:48:00.383251277")
        latest_timestamp, lines_to_print = dispatch_job.get_logs_to_print(
            log_lines, current_timestamp
        )
        self.assertSequenceEqual(
            lines_to_print,
            [
                "2025-07-29T15:48:01.787177054Z test2",
                "2025-07-29T15:48:03.074715108Z test3",
            ],
        )
        self.assertEqual(
            latest_timestamp, dateutil.parser.parse("2025-07-29T15:48:03.074715108")
        )


if __name__ == "__main__":
    unittest.main()
