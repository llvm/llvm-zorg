# RUN: lnt convert --to=json %S/Inputs/test.nightlytest %t
# RUN: FileCheck %s < %t

# We are just checking the conversion, not validating the format.
# CHECK: "Machine":
# CHECK: "Tests": [
