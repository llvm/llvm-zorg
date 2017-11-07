echo "@@@ Move LNT Results @@@"

mkdir -p result
test -e lnt-sandbox/build/test.log && cp -p lnt-sandbox/build/test.log result/
test -e lnt-sandbox/build/report.json && cp -p lnt-sandbox/build/report.json result/
test -e lnt-sandbox/build/test-results.xunit.xml && cp -p lnt-sandbox/build/test-results.xunit.xml result/

echo "@@@@@@@"
