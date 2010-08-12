# RUN: lnt submit %base_url/submitRun %S/../DB/Inputs/sample-a-small.plist > %t
# RUN: FileCheck %s < %t

# CHECK: Importing u'{{.*}}.plist'
# CHECK: Import succeeded.
