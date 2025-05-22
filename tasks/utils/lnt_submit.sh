echo "@@@ LNT Submit @@@"

echo "Skipping LNT submission temporarily until a permanent LNT server is configured"

#if [ -n "${SUBMIT_URL:=}" -a -n "${SUBMIT_NAME:=}" ]; then
#    LNT_RESULT_URL="$(lnt submit "${SUBMIT_URL}" "${WORKSPACE}/lnt-sandbox/report.json")"
#    # Jenkins builds look for this message:
#    echo "Results available at: ${LNT_RESULT_URL}"
#else
#    echo 1>&2 "Skipping submission: SUBMIT_URL/SUBMIT_NAME not defined"
#fi

echo "@@@@@@@"
