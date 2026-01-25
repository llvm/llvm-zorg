#!/usr/bin/env python3
"""
Artifact management for Jenkins CI builds.
Handles fetching artifacts with fallback patterns and state information triggering stage 1 builds.
This is to be used by CI jobs.
"""

import os
import sys
import subprocess
import argparse
import logging
import shutil
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArtifactManager:
    def __init__(self, workspace, s3_bucket):
        self.workspace = Path(workspace)
        self.s3_bucket = s3_bucket

    def run_cmd(self, cwd, cmd):
        """Run a command in the specified directory."""
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Command failed with return code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        return result

    def get_git_info(self):
        """Extract git distance and SHA from the llvm-project directory."""
        try:
            llvm_project_dir = self.workspace / "llvm-project"
            os.chdir(llvm_project_dir)

            # Create first_commit tag if it doesn't exist
            subprocess.run([
                "git", "tag", "-a", "-m", "First Commit", "first_commit",
                "97724f18c79c7cc81ced24239eb5e883bf1398ef"
            ], capture_output=True)  # Ignore errors if tag exists

            # Get git description
            result = subprocess.run([
                "git", "describe", "--match", "first_commit"
            ], capture_output=True, text=True, check=True)

            git_desc = result.stdout.strip()
            parts = git_desc.split("-")

            git_distance = parts[1]
            git_sha = parts[2][1:]  # Remove 'g' prefix

            os.chdir(self.workspace)

            logger.info(f"Git info: distance={git_distance}, sha={git_sha}")
            return git_distance, git_sha

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git info: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting git info: {e}")
            raise

    @staticmethod
    def construct_artifact_names(job_name, git_distance, git_sha):
        """Construct mainline and bisection artifact names. In the case of
        a bisection job the artifact can come from either the mainline stage 1 job or the
        bisection version of the stage 1 job, so we return two artifact names to check."""
        tar_name = f"clang-d{git_distance}-g{git_sha}.tar.gz"

        if "/bisect/" in job_name:
            mainline_job_name = job_name.replace("/bisect/", "/")
            bisection_artifact = f"{job_name}/{tar_name}"
            mainline_artifact = f"{mainline_job_name}/{tar_name}"
            return mainline_artifact, bisection_artifact
        else:
            # Not a bisection job, so just return the mainline artifact name
            return f"{job_name}/{tar_name}", None

    def fetch_artifact(self, artifact_name):
        """Attempt to fetch a specific artifact."""
        try:
            logger.info(f"Attempting to fetch artifact: {artifact_name}")

            local_name = "host-compiler.tar.gz"

            # Download the artifact from S3
            download_cmd = ["aws", "s3", "cp", f"{self.s3_bucket}/clangci/{artifact_name}", local_name]
            try:
                self.run_cmd(self.workspace, download_cmd)
            except subprocess.CalledProcessError:
                logger.warning(f"Failed to fetch artifact: {artifact_name}")
                return False

            # Determine if the compiler package is actually a pointer to another file stored.
            # If so, download the file at the pointer
            if Path(local_name).stat().st_size < 1000:
                logger.info("Artifact is a pointer file, following to actual artifact...")
                with open(local_name, "r") as pointer:
                    package = pointer.read().strip()
                    download_cmd = ["aws", "s3", "cp", f"{self.s3_bucket}/clangci/{package}", local_name]
                    self.run_cmd(self.workspace, download_cmd)

            logger.info("Decompressing artifact...")
            host_compiler_dir = self.workspace / "host-compiler"

            if host_compiler_dir.exists():
                shutil.rmtree(host_compiler_dir)

            host_compiler_dir.mkdir()
            self.run_cmd(host_compiler_dir, ['tar', 'zxf', f"../{local_name}"])
            os.unlink(local_name)

            logger.info(f"Successfully fetched and extracted artifact: {artifact_name}")
            return True

        except Exception as e:
            logger.error(f"Error fetching artifact {artifact_name}: {e}")
            return False

    def fetch_with_fallback(self, job_name, provided_artifact=None):
        """
        Main method to fetch artifacts with fallback logic.

        Args:
            job_name: Jenkins job name responsible for producing the artifact to download
            provided_artifact: Explicit artifact name (for non-bisection jobs)

        Returns:
            tuple: (success, used_artifact, needs_stage1)
        """
        # If explicit artifact is provided, use it directly. Non bisection jobs
        # will specify the artifact they want to use i.e. llvm.org/clang-stage1-RA/latest
        if provided_artifact:
            logger.info(f"Using provided artifact: {provided_artifact}")
            success = self.fetch_artifact(provided_artifact)
            if success:
                return True, provided_artifact, False
            else:
                logger.info("Provided artifact not found, stage 1 build needed")
                return False, provided_artifact, True
        else:
            # In the case that a job name was provided and not a specific artifact
            # Try to download the artifact using the associated job name to find the artifact.
            # If it's a bisection job, we can check both the mainline build and the bisection build
            git_distance, git_sha = self.get_git_info()
            mainline_artifact, bisection_artifact = ArtifactManager.construct_artifact_names(
                job_name, git_distance, git_sha
            )

            # Try primary artifact first
            if self.fetch_artifact(mainline_artifact):
                return True, mainline_artifact, False

            # No primary artifact found and we're not checking for a bisection job, so return
            if bisection_artifact is None:
                return False, mainline_artifact, True

            # Try bisection artifact as fallback
            logger.info("Primary artifact not found, trying to find bisection job artifact...")
            if self.fetch_artifact(bisection_artifact):
                return True, bisection_artifact, False

            # Neither found, we need stage 1 build
            logger.info("No artifacts found, stage 1 build needed")
            return False, bisection_artifact, True


def main():
    parser = argparse.ArgumentParser(description='Download CI build artifacts')
    parser.add_argument('--workspace', default=os.getcwd(), help='Jenkins workspace directory')
    parser.add_argument('--s3-bucket', help='S3 bucket name (from environment if not provided)')
    parser.add_argument('--output-file', default='artifact_result.properties',
                        help='File to write results to')

    # Create a mutually exclusive group
    exclusive_group = parser.add_mutually_exclusive_group(required=True)
    exclusive_group.add_argument('--job-name', help='Jenkins job responsible for producing the artifact to download')
    exclusive_group.add_argument('--artifact', help='Specific artifact name to download')

    args = parser.parse_args()

    # Get S3 bucket from environment if not provided
    s3_bucket = args.s3_bucket or os.environ.get('S3_BUCKET')
    if not s3_bucket:
        logger.error("S3_BUCKET must be provided via --s3-bucket or S3_BUCKET environment variable")
        sys.exit(1)

    try:
        manager = ArtifactManager(args.workspace, s3_bucket)
        success, used_artifact, needs_stage1 = manager.fetch_with_fallback(
            args.job_name, args.artifact
        )

        # Write results to properties file for Jenkins to read
        with open(args.output_file, 'w') as f:
            f.write(f"ARTIFACT_FOUND={str(success).lower()}\n")
            f.write(f"USED_ARTIFACT={used_artifact}\n")
            f.write(f"NEEDS_STAGE1={str(needs_stage1).lower()}\n")

        logger.info(f"Results written to {args.output_file}")

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
