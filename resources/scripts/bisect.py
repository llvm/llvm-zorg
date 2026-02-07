#!/usr/bin/env python3
import json
import subprocess
import sys
import math
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class BisectionManager:
    def __init__(self, workspace_dir: str = ".", repo_path: str = "."):
        self.workspace_dir = Path(workspace_dir)
        self.repo_path = Path(repo_path)
        self.state_file = self.workspace_dir / "bisection_state.json"
        self.bisection_log = self.workspace_dir / "bisection.log"
        self.restart_log = self.workspace_dir / "restart_instructions.log"

    def _print(self, message: str) -> None:
        """Print non-JSON output to stderr so it appears in CI logs"""
        print(message, file=sys.stderr)

    def initialize_bisection(self, good_commit: str, bad_commit: str,
                             test_job: Optional[str] = None, session_id: Optional[str] = None,
                             verbose: bool = True) -> Dict[str, Any]:
        """Initialize a new bisection session"""

        # Get commit range
        commits = self._get_commit_range(good_commit, bad_commit)
        estimated_steps = math.ceil(math.log2(len(commits))) if len(commits) > 1 else 0

        state = {
            "session_id": session_id or f"bisect_{int(datetime.now().timestamp())}",
            "status": "initialized",
            "good_commit": good_commit,
            "bad_commit": bad_commit,
            "current_good": good_commit,
            "current_bad": bad_commit,
            "commits_to_test": commits[1:-1],  # Exclude the boundary commits
            "estimated_steps": estimated_steps,
            "completed_steps": 0,
            "test_results": {},
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "metadata": {
                "total_commits": len(commits),
                "repo_path": str(self.repo_path),
                "test_job": test_job
            },
            "next_action": None
        }

        # Add continuation info if session_id was provided
        if session_id:
            state['continued_at'] = datetime.now().isoformat()

        # Determine first commit to test
        self._update_next_action(state)
        self._save_state(state)

        if verbose:
            session_type = "CONTINUED" if session_id else "STARTED"
            self._print(f"Initializing bisection...")
            if session_id:
                self._print(f"Continuing session: {session_id}")
            self._print(f"Session ID: {state['session_id']}")
            self._print(f"Total commits in range: {len(commits)}, estimated {estimated_steps} steps")

            # Initialize log files
            self._initialize_logs(state, test_job, session_type)

        return state

    def get_next_step_info(self) -> Dict[str, Any]:
        """Get information about the next step to execute"""
        state = self._load_state()

        if state['next_action']['type'] == 'complete':
            return {
                'type': 'complete',
                'failing_commit': state['next_action']['failing_commit'],
                'state': state
            }
        elif state['next_action']['type'] == 'test_commit':
            return {
                'type': 'test_commit',
                'commit': state['next_action']['commit'],
                'commit_info': state['next_action']['commit_info'],
                'progress': state['next_action']['progress'],
                'bisection_range': state['next_action']['bisection_range'],
                'session_id': state['session_id'],
                'state': state
            }
        else:
            raise ValueError(f"Unknown next action type: {state['next_action']['type']}")

    def log_step_start(self, step_number: int) -> Dict[str, Any]:
        """Log the start of a bisection step and return step info"""
        step_info = self.get_next_step_info()

        self._print(f"\n{'=' * 60}")
        self._print(f"🔍 BISECTION STEP {step_number}")
        self._print(f"{'=' * 60}")

        if step_info['type'] == 'complete':
            self._print("🎉 BISECTION COMPLETE!")
            self._print(f"First bad commit: {step_info['failing_commit']}")

            log_entry = f"""
STEP {step_number}: BISECTION COMPLETE
First bad commit: {step_info['failing_commit']}
Total steps completed: {step_info['state']['completed_steps']}
Completed at: {datetime.now().isoformat()}

"""
            self._append_to_log(self.bisection_log, log_entry)
            return step_info

        commit = step_info['commit']
        commit_info = step_info['commit_info']
        progress = step_info['progress']

        self._print(f"Testing commit: {commit}")
        self._print(f"Author: {commit_info['author']}")
        self._print(f"Date: {commit_info['date']}")
        self._print(f"Subject: {commit_info['subject']}")
        self._print(f"Progress: {progress['completed_steps']}/{progress['total_steps']} ({progress['percentage']}%)")
        self._print(f"Remaining: {progress['remaining_commits']} commits, ~{progress['remaining_steps']} steps")

        # Log this step
        log_entry = f"""
STEP {step_number}: Testing commit {commit}
Author: {commit_info['author']}
Date: {commit_info['date']}
Subject: {commit_info['subject']}
Progress: {progress['completed_steps']}/{progress['total_steps']} ({progress['percentage']}%)
Range: {step_info['bisection_range']['current_good']}..{step_info['bisection_range']['current_bad']}

"""
        self._append_to_log(self.bisection_log, log_entry)

        return step_info

    def show_restart_instructions(self, step_number: int, test_job: str, platform: str = "jenkins") -> None:
        """Display and log restart instructions"""
        step_info = self.get_next_step_info()

        if step_info['type'] != 'test_commit':
            return

        current_good = step_info['bisection_range']['current_good']
        current_bad = step_info['bisection_range']['current_bad']
        session_id = step_info['session_id']
        commit = step_info['commit']
        commit_info = step_info['commit_info']

        self._print("\n🔄 RESTART INSTRUCTIONS:")
        self._print("┌─────────────────────────────────────────────────────────────────────────────┐")
        self._print("│ 🔄 TO RESTART FROM THIS STEP IF JOB FAILS:                                  │")
        self._print("│                                                                             │")

        if platform == "jenkins":
            self._print("│ Run this job again with parameters:                                         │")
            self._print(f"│   GOOD_COMMIT: {current_good:<50} │")
            self._print(f"│   BAD_COMMIT: {current_bad:<51} │")
            self._print(f"│   SESSION_ID: {session_id:<52} │")
            self._print(f"│   TEST_JOB_NAME: {test_job:<48} │")
        else:  # github actions
            self._print("│ Run this workflow again with parameters:                                   │")
            self._print(f"│   good_commit: {current_good:<50} │")
            self._print(f"│   bad_commit: {current_bad:<51} │")
            self._print(f"│   session_id: {session_id:<52} │")
            self._print(f"│   test_workflow: {test_job:<48} │")

        self._print("│                                                                             │")
        self._print(f"│ This will continue testing from commit: {commit[:20]:<20}          │")
        self._print(f"│ ({commit_info['subject'][:50]:<50})                                          │")
        self._print("└─────────────────────────────────────────────────────────────────────────────┘")

        # Log restart instructions
        self._log_restart_instructions(step_number, current_good, current_bad,
                                       session_id, commit, commit_info, test_job, platform)

    def log_job_execution(self, job_name: str, result: str, duration: float,
                          job_url: Optional[str] = None, build_number: Optional[str] = None) -> None:
        """Log job execution results"""

        self._print(f"📊 Job result: {result}")
        self._print(f"⏱️  Duration: {duration:.1f}s")
        if job_url:
            self._print(f"🔗 Job URL: {job_url}")

        log_entry = f"   Job: {job_name}"
        if build_number:
            log_entry += f" #{build_number}"
        log_entry += f"\n   Result: {result}\n   Duration: {duration:.1f}s\n"
        if job_url:
            log_entry += f"   URL: {job_url}\n"
        log_entry += "\n"

        self._append_to_log(self.bisection_log, log_entry)

    def record_test_result(self, commit: str, result: str) -> Dict[str, Any]:
        """Record the result of testing a commit and update bisection state"""

        state = self._load_state()

        if not state.get("next_action") or state["next_action"].get("commit") != commit:
            raise ValueError(f"Unexpected commit {commit}. Expected {state.get('next_action', {}).get('commit')}")

        # Normalize result to boolean (True = good, False = bad)
        is_good = result.upper() in ["SUCCESS", "PASSED", "STABLE", "GOOD", "TRUE"]

        # Record the result
        state["test_results"][commit] = {
            "result": result,
            "is_good": is_good,
            "timestamp": datetime.now().isoformat(),
            "step_number": state["completed_steps"] + 1
        }

        state["completed_steps"] += 1
        state["last_updated"] = datetime.now().isoformat()

        # Update bisection boundaries based on result
        if is_good:
            # This commit is good, so the failure is in later commits
            state["current_good"] = commit
            self._print(f"✅ Commit {commit} is GOOD - failure is in later commits")
        else:
            # This commit is bad, so the failure is in earlier commits
            state["current_bad"] = commit
            self._print(f"❌ Commit {commit} is BAD - failure is in earlier commits")

        # Update what to test next
        self._update_next_action(state)
        self._save_state(state)

        return state

    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report"""

        self._print(f"\n{'=' * 60}")
        self._print("GENERATING FINAL REPORT")
        self._print(f"{'=' * 60}")

        step_info = self.get_next_step_info()

        if step_info['type'] != 'complete':
            self._print("⚠️  Bisection did not complete successfully")
            report_text = "Bisection did not complete successfully. See bisection.log for details."
            with open(self.workspace_dir / "bisection_final_report.txt", 'w') as f:
                f.write(report_text)
            return step_info

        state = step_info['state']
        failing_commit = step_info['failing_commit']

        # Get detailed commit information
        try:
            result = subprocess.run([
                "git", "show", "--stat", failing_commit
            ], cwd=self.repo_path, capture_output=True, text=True, check=True)
            commit_details = result.stdout.strip()
        except subprocess.CalledProcessError:
            commit_details = f"Could not retrieve details for commit {failing_commit}"

        # Create comprehensive report
        report = f"""
=== BISECTION FINAL REPORT ===
Session ID: {state['session_id']}
Started: {state['start_time']}
Completed: {state['last_updated']}

RESULT:
First bad commit: {failing_commit}

COMMIT DETAILS:
{commit_details}

STATISTICS:
- Total steps: {state['completed_steps']}
- Commits in original range: {state['metadata']['total_commits']}

TEST RESULTS SUMMARY:
"""

        # Add test results to report
        for commit, result in state['test_results'].items():
            report += f"- {commit}: {result['result']} (step {result['step_number']})\n"

        report += "\n=== END REPORT ===\n"

        # Save report
        with open(self.workspace_dir / "bisection_final_report.txt", 'w') as f:
            f.write(report.strip())

        # Also append to the log
        self._append_to_log(self.bisection_log, report)

        self._print(report.strip())

        return {
            'type': 'complete',
            'failing_commit': failing_commit,
            'report': report.strip(),
            'state': state
        }

    def display_summary(self) -> None:
        """Display final bisection summary"""

        self._print(f"\n{'=' * 60}")
        self._print("BISECTION SUMMARY")
        self._print(f"{'=' * 60}")

        try:
            step_info = self.get_next_step_info()
            state = step_info['state']

            self._print(f"Status: {state['status']}")
            self._print(f"Steps completed: {state['completed_steps']}")

            if step_info['type'] == 'complete':
                self._print("✅ SUCCESS: First bad commit identified")
                self._print(f"Failing commit: {step_info['failing_commit']}")
            else:
                self._print("❌ Bisection incomplete")

        except Exception as e:
            self._print(f"Could not load bisection state: {e}")

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current bisection state"""
        return self._load_state()

    # Private helper methods
    def _get_commit_range(self, good_commit: str, bad_commit: str) -> List[str]:
        """Get the list of commits between good and bad (inclusive)"""
        try:
            result = subprocess.run([
                "git", "rev-list", "--reverse", f"{good_commit}..{bad_commit}"
            ], cwd=self.repo_path, capture_output=True, text=True, check=True)

            commits = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            return [good_commit] + commits + [bad_commit]

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get commit range {good_commit}..{bad_commit}: {e}")

    def _get_commit_info(self, commit: str) -> Dict[str, str]:
        """Get basic information about a commit"""
        try:
            result = subprocess.run([
                "git", "show", "-s", "--format=%an%x2C%ad%x2C%s", commit
            ], cwd=self.repo_path, capture_output=True, text=True, check=True)

            parts = result.stdout.strip().split(',', 2)
            return {
                "author": parts[0] if len(parts) > 0 else "Unknown",
                "date": parts[1] if len(parts) > 1 else "Unknown",
                "subject": parts[2] if len(parts) > 2 else "Unknown"
            }
        except subprocess.CalledProcessError:
            return {
                "author": "Unknown",
                "date": "Unknown",
                "subject": "Unknown"
            }

    def _update_next_action(self, state: Dict[str, Any]) -> None:
        """Update the next_action field based on current bisection state"""

        # Get commits between current good and bad
        commits_in_range = self._get_commit_range(
            state["current_good"],
            state["current_bad"]
        )

        # Remove boundary commits and already tested commits
        commits_to_test = []
        for commit in commits_in_range[1:-1]:  # Exclude boundaries
            if commit not in state["test_results"]:
                commits_to_test.append(commit)

        if len(commits_to_test) == 0:
            # Bisection is complete
            state["status"] = "complete"
            state["next_action"] = {
                "type": "complete",
                "failing_commit": state["current_bad"],
                "message": f"Bisection complete. First bad commit: {state['current_bad']}"
            }
            return

        # Find the midpoint commit to test next
        midpoint_index = len(commits_to_test) // 2
        next_commit = commits_to_test[midpoint_index]

        # Calculate progress information
        remaining_commits = len(commits_to_test)
        remaining_steps = math.ceil(math.log2(remaining_commits)) if remaining_commits > 1 else 1
        progress_percentage = (state["completed_steps"] / state["estimated_steps"] * 100) if state["estimated_steps"] > 0 else 0

        state["status"] = "testing"
        state["next_action"] = {
            "type": "test_commit",
            "commit": next_commit,
            "commit_info": self._get_commit_info(next_commit),
            "progress": {
                "remaining_commits": remaining_commits,
                "remaining_steps": remaining_steps,
                "completed_steps": state["completed_steps"],
                "total_steps": state["estimated_steps"],
                "percentage": round(progress_percentage, 1)
            },
            "bisection_range": {
                "current_good": state["current_good"],
                "current_bad": state["current_bad"],
                "commits_in_range": len(commits_in_range)
            }
        }

    def _initialize_logs(self, state: Dict[str, Any], test_job: Optional[str], session_type: str) -> None:
        """Initialize log files"""
        log_header = f"""
=== BISECTION {session_type} ===
Session ID: {state['session_id']}
Good commit: {state['good_commit']}
Bad commit: {state['bad_commit']}
Test job: {test_job or 'N/A'}
Total commits: {state['metadata']['total_commits']}
Estimated steps: {state['estimated_steps']}
{session_type.lower().capitalize()} at: {state['start_time']}

"""

        with open(self.bisection_log, 'w') as f:
            f.write(log_header)

        with open(self.restart_log, 'w') as f:
            f.write("=== RESTART INSTRUCTIONS LOG ===\n\n")

    def _log_restart_instructions(self, step_number: int, current_good: str, current_bad: str,
                                  session_id: str, commit: str, commit_info: Dict[str, str],
                                  test_job: str, platform: str) -> None:
        """Log restart instructions to file"""
        timestamp = datetime.now().isoformat()

        log_entry = f"""
=== RESTART POINT {step_number} ===
Timestamp: {timestamp}
Step: {step_number}
Current range: {current_good}..{current_bad}
Next commit to test: {commit}
Commit info: {commit_info['subject']} ({commit_info['author']})
Session ID: {session_id}

RESTART PARAMETERS:
{'GOOD_COMMIT' if platform == 'jenkins' else "good_commit"}={current_good}
{'BAD_COMMIT' if platform == 'jenkins' else 'bad_commit'}={current_bad}
{'SESSION_ID' if platform == 'jenkins' else 'session_id'}={session_id}
{'TEST_JOB_NAME' if platform == 'jenkins' else 'test_workflow'}={test_job}

"""

        self._append_to_log(self.restart_log, log_entry)

    def _save_state(self, state: Dict[str, Any]) -> None:
        """Save bisection state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> Dict[str, Any]:
        """Load bisection state from file"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"State file not found: {self.state_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in state file {self.state_file}: {e}")

    def _append_to_log(self, log_file: Path, content: str) -> None:
        """Append content to a log file"""
        with open(log_file, 'a') as f:
            f.write(content)


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='Git Bisection Manager - CI bisection management')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Common arguments
    def add_common_args(parser):
        parser.add_argument('--repo-path', default='.', help='Path to git repository')
        parser.add_argument('--workspace', default='.', help='Workspace directory')

    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize bisection session')
    init_parser.add_argument('good_commit', help='Known good commit SHA')
    init_parser.add_argument('bad_commit', help='Known bad commit SHA')
    init_parser.add_argument('--test-job', help='Test job/workflow name')
    init_parser.add_argument('--session-id', help='Session ID for restart')
    add_common_args(init_parser)

    # Record result command (original interface)
    record_parser = subparsers.add_parser('record', help='Record test result for a commit')
    record_parser.add_argument('commit', help='Commit SHA that was tested')
    record_parser.add_argument('result', help='Test result (SUCCESS/FAILURE/GOOD/BAD/etc)')
    add_common_args(record_parser)

    log_parser = subparsers.add_parser('log-step', help='Log step start')
    log_parser.add_argument('step_number', type=int, help='Step number')
    add_common_args(log_parser)

    restart_parser = subparsers.add_parser('show-restart', help='Show restart instructions')
    restart_parser.add_argument('step_number', type=int, help='Step number')
    restart_parser.add_argument('test_job', help='Test job/workflow name')
    restart_parser.add_argument('--platform', choices=['jenkins', 'github'], default='jenkins')
    add_common_args(restart_parser)

    job_parser = subparsers.add_parser('log-job', help='Log job execution result')
    job_parser.add_argument('job_name', help='Job name')
    job_parser.add_argument('result', help='Job result')
    job_parser.add_argument('duration', type=float, help='Duration in seconds')
    job_parser.add_argument('--job-url', help='Job URL')
    job_parser.add_argument('--build-number', help='Build number')
    add_common_args(job_parser)

    report_parser = subparsers.add_parser('final-report', help='Generate final report')
    add_common_args(report_parser)

    summary_parser = subparsers.add_parser('summary', help='Display summary')
    add_common_args(summary_parser)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        manager = BisectionManager(args.workspace, args.repo_path)

        if args.command == 'init':
            state = manager.initialize_bisection(
                args.good_commit, args.bad_commit, args.test_job, args.session_id
            )
            print(json.dumps(state, indent=2))

        elif args.command == 'record':
            state = manager.record_test_result(args.commit, args.result)
            print(json.dumps(state, indent=2))

        elif args.command == 'log-step':
            step_info = manager.log_step_start(args.step_number)
            print(json.dumps(step_info, indent=2))

        elif args.command == 'show-restart':
            manager.show_restart_instructions(args.step_number, args.test_job, args.platform)

        elif args.command == 'log-job':
            manager.log_job_execution(
                args.job_name, args.result, args.duration,
                args.job_url, args.build_number
            )

        elif args.command == 'final-report':
            result = manager.generate_final_report()
            print(json.dumps(result, indent=2))

        elif args.command == 'summary':
            manager.display_summary()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
