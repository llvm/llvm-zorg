# RUN: lnt convert --to=json %S/Inputs/test.plist | FileCheck %s
# RUN: lnt convert --to=json < %S/Inputs/test.plist | FileCheck %s

# CHECK: {"a": 1}
