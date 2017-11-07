# One of the most common errors is to forget to add files/changes to the config
# repository. So we stop the process if the git repository shows any untracked
# files or non-comitted changes.
# TODO: Add a commandline flag or similar to override/ignore the checks?

# Check that repo is clean
if ! git diff-index --quiet HEAD --; then
    echo 1>&2 "Found uncommitted changes, the build probably won't work."
    echo 1>&2 "Note: Use `git status` to view them."
    exit 1
fi

# Check that the taskscript is actually part of the repo
if ! git ls-files "${TASKSCRIPT}" --error-unmatch > /dev/null; then
    echo 1>&2 "Task '${TASKSCRIPT}' is not tracked by git."
    echo 1>&2 "Note: Add and commit the file to the git repository."
    exit 1
fi

# Check for untracked files
if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo 1>&2 "Error: There are untracked files around, the build probably won't work."
    echo 1>&2 "Note: - Add the files and commit them"
    echo 1>&2 "Note: - Or add them to \`.gitignore\` or \`.git/info/exclude\`"
    exit 1
fi
