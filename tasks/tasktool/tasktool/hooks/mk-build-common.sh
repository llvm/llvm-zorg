RELATIVE_TASKSCRIPT="$(git ls-tree --full-name --name-only HEAD "${TASKSCRIPT}")"
TASKDIR="$(dirname "${RELATIVE_TASKSCRIPT}")"

echo "config_url='${CONFIG_URL}'"
echo "config_rev='${CONFIG_REV}'"
echo "TASKDIR=\"\${WORKSPACE}/config/${TASKDIR}\""
tail -n +4 header
echo "cat > buildconfig.json <<'BUILDCONFIGEOF'"
cat "${BUILDCONFIG}"
echo "BUILDCONFIGEOF"
echo ""
cat "${TASKSCRIPT}"
