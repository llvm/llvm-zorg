# RUN: %src_root/lnt/import/SubmitData %base_url/submitRun \
# RUN:   ../DB/Inputs/sample-a-small.plist > %t.log
# RUN: FileCheck %s < %t.log

# CHECK: STATUS: 0

# CHECK: OUTPUT:
# CHECK: IMPORT: {{.*}}/lnt_tmp/{{.*}}.plist
# CHECK: LOAD TIME: 0.03s
# CHECK: IMPORT TIME: 0.03s
# CHECK: MACHINE: 107
# CHECK: START  : {{.*}}
# CHECK: END    : {{.*}}
# CHECK: INFO   : u'tag' = u'nightlytest'
# CHECK: MAILING RESULTS TO: {{.*}}
# CHECK: ADDED: {{[0-9]*}} machines
# CHECK: ADDED: {{[0-9]*}} runs
# CHECK: ADDED: {{[0-9]*}} tests
# CHECK: DISCARDING RESULT: DONE
