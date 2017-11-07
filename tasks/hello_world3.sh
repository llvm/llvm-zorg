# Tasks can also produce result files. The task runner will check if
# `${WORKSPACE}/result` exists after the task is finished.
#
# The contents will be packed into an archive. Depending on the mode:
# - `task try` and `task sshrun` will place the archive into the results folder
#    of the llvm-ci-tasks checkout
# - `task submit` will upload the archive to the A2 server
# - `task jenkinsrun` does nothing; jenkins is responsible for archiving
#    the results folder.

# Get the compiler as usual.
build get compiler --from=clang-stag1-configure-RA
. ${TASKDIR}/utils/normalize_compiler.sh

# Compile an example program.
compiler/bin/clang ${TASKDIR}/hello_world.c -o hello

# Place the resuling executable into the results folder.
# You should get an archive containing the "hello" executable when the task is
# finished.
mkdir result
mv hello result
