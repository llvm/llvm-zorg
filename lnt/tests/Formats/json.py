# RUN: lnt convert --to=json %S/Inputs/test.json | FileCheck %s
# RUN: lnt convert --to=json < %S/Inputs/test.json | FileCheck %s

# CHECK: {"a": 1}
