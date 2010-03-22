# RUN: curl -s %base_url/nightlytest/1/ | FileCheck --check-prefix=BRIEF %s
# BRIEF: <h1>LLVM Nightly Test Results</h1>
# BRIEF: See Full Test Results
# BRIEF: Render Time:

# RUN: curl -s %base_url/nightlytest/1/?full=1 | FileCheck --check-prefix=FULL %s
# FULL: <h1>LLVM Nightly Test Results</h1>
# FULL: See Brief Test Results
# FULL: Render Time:

