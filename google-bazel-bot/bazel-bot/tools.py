import os
import json
import requests
from pathlib import Path
from typing import Dict, Any

GITHUB_REPO = "llvm/llvm-project"


def path_to_dict(path: Path) -> Dict[str, Any]:
    """
    Recursively converts a pathlib.Path object into a dictionary.
    """
    # Base dictionary structure
    d: Dict[str, Any] = {"name": path.name}
    if path.is_symlink():
        d["type"] = "symlink"
        return d

    if path.is_dir():
        d["type"] = "directory"
        # Recursively map children; use sorted() for consistent output
        try:
            d["children"] = [
                path_to_dict(child)
                for child in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
            ]
        except PermissionError:
            d["error"] = "Permission Denied"
    else:
        d["type"] = "file"

    return d


def directory_structure(start_path: str) -> str:
    """
    Returns directory structure of a given path in JSON format
    """
    if not "utils/bazel/llvm-project-overlay" in start_path:
        return "Cannot return directory structure outside of utils/bazel/llvm-project-overlay"

    path = Path(start_path)
    if not path.exists():
        return json.dumps({"error": "Path does not exist"}, indent=4)

    tree_dict = path_to_dict(path)
    # Fix the root name to be the full path for clarity
    tree_dict["name"] = str(path)

    return json.dumps(tree_dict, indent=4)


def read_file(file_path: str) -> str:
    """
    Reads the content of a file from the filesystem.

    Args:
        file_path: The absolute path to the file to read.

    Returns:
        The content of the file as a string, or an error message if reading fails.
    """
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def search_and_replace(file_path: str, old_content: str, new_content: str) -> str:
    """
    Replaces a specific text segment in a file with new content.

    Args:
        file_path: The absolute path to the file.
        old_content: The exact string segment to be replaced.
        new_content: The string to replace the old content with.

    Returns:
        A success message or an error message.
    """
    file_path = os.path.abspath(file_path)
    if "utils/bazel/llvm-project-overlay" not in file_path:
        return "Error: Can only modify files within utils/bazel/llvm-project-overlay directory."

    try:
        content = read_file(file_path)
        if content.startswith("Error"):
            return content

        if old_content not in content:
            return f"Error: 'old_content' not found in {file_path}. No changes made."

        updated_content = content.replace(old_content, new_content)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

        return f"Success: Content replaced in {file_path}"
    except Exception as e:
        return f"Error modifying file: {str(e)}"


def get_diff(commit_sha: str) -> str:
    """
    Retrieves the git diff for a specific commit SHA using the GitHub API.

    Args:
        commit_sha: The SHA hash of the commit to analyze.

    Returns:
        The diff of the commit as a string, or an error message.
    """
    try:
        github_token = os.environ.get("GITHUB_API_TOKEN")
        if not github_token:
            return "Error: GITHUB_API_TOKEN environment variable not set."

        url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/{commit_sha}"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3.diff",
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error getting diff from GitHub API: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"
