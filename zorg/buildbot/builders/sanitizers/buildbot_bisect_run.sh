#!/usr/bin/env bash
# This script uses BUILDBOT_REVISION to read bad and good patch for bisect.
# The format is: BUILDBOT_REVISION=good:bad

set -x
set -e
set -u


echo @@@BUILD_STEP bisecting ${BUILDBOT_REVISION}@@@
echo "@@@STEP_EXCEPTION@@@"  # Bisect is neither FAIL nor PASS.

# Try to get them out from the bisect string in BUILDBOT_REVISION first.
BAD="${BUILDBOT_REVISION/:*/}"
GOOD="${BUILDBOT_REVISION/*:/}"

# If not provided through BUILDBOT_REVISION, use some defaults.
if [[ "$BAD" == "" ]]; then
  BAD="origin/main"
fi
if [[ "$GOOD" == "" ]]; then
  GOOD="origin/main~100"
fi

cd llvm-project

git clean -fd
git reset --hard

(
  if git bisect start $BAD $GOOD; then
    git bisect run bash -c "cd .. && $*"
  fi

  echo @@@BUILD_STEP bisect result@@@
  git bisect log
) || true

git bisect reset
