#!/bin/sh

set -eu

if [ $# != 2 ]; then
    echo "Usage: $0 <sqlite3-database> <output file>"

    echo "  Dumps the sqlite3 database to the output file "
    echo "  in SQL syntax that MySQL can understand."

    exit 1
fi

in=$1
out=$2

sqlite3 $in .dump |  \
  sed -e 's#CREATE INDEX.*##g' \
      -e 's#ANALYZE sqlite_master.*##g' \
      -e 's#INSERT INTO "sqlite_stat1" VALUES.*##g' \
      -e 's# Key    \([ ]*\)TEXT# `Key`\1TEXT#g' \
      -e 's#BEGIN TRANSACTION#START TRANSACTION#g' \
      -e 's#INSERT INTO "\(.*\)"#INSERT INTO \1#g' > $out
