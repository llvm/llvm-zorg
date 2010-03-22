# RUN: rm -f %t.db
# RUN: sqlite3 %t.db ".read %src_root/db/CreateTables.sql"

# FIXME: Find a way to test email works, without being annoying.
# RUN: %src_root/lnt/import/ImportData \
# RUN:  --show-sample-count \
# RUN:  --commit=0 \
# RUN:  --email-on-import=1 --email-host=%email_host \
# RUN:  --email-from=lnt-test@llvm.org --email-to=%email_to \
# RUN:  --email-base-url=ZORG_TEST %t.db %S/Inputs/sample-a-small.plist > %t
# RUN: FileCheck %s < %t

# CHECK: ADDED: 1 machines
# CHECK: ADDED: 1 runs
# CHECK: ADDED: 90 tests
# CHECK: ADDED: 90 samples



