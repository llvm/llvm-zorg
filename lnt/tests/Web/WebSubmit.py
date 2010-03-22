# RUN: lnt submit %base_url/submitRun %S/../DB/Inputs/sample-a-small.plist > %t
# RUN: FileCheck %s < %t

# CHECK: STATUS: 0

# CHECK: OUTPUT:
# CHECK: IMPORT: {{.*}}/lnt_tmp/{{.*}}.plist
# CHECK: LOAD TIME: {{.*}}
# CHECK: IMPORT TIME: {{.*}}
# CHECK: MACHINE: {{.*}}
# CHECK: START  : {{.*}}
# CHECK: END    : {{.*}}
# CHECK: INFO   : u'tag' = u'nightlytest'
# CHECK: MAILING RESULTS TO: {{.*}}
# CHECK: ADDED: {{[0-9]*}} machines
# CHECK: ADDED: {{[0-9]*}} runs
# CHECK: ADDED: {{[0-9]*}} tests
# CHECK: DISCARDING RESULT: DONE
