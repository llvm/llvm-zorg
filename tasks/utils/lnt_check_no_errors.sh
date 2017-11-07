echo "@@@ LNT Check No Erros @@@"

# Usually the LNT steps do not report errors with an exitcode because we want
# to continue running, sending mails, etc. even if some of the benchmarks
# failed. However putting this at the end of a job ensure we do report a
# problem after all and mark the build as failed.

lnt check-no-errors "${WORKSPACE}/lnt-sandbox/report.json"

echo "@@@@@@@"
