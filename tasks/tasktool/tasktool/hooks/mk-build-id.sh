# By convention produce a build id in the first line. For now use a uuid.
BUILDID="$(uuidgen | tr -d "-" | tr "[:upper:]" "[:lower:]")"
echo "buildid='${BUILDID}'"
