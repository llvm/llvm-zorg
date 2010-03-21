# RUN: curl -s http://localhost/zorg/nightlytest/ | FileCheck %s
# CHECK: <h2>LLVM Nightly Test</h2>
# CHECK: Render Time:
