# RUN: curl -s %base_url/nightlytest/ | FileCheck %s
# CHECK: <h2>{{.*}}LNT{{.*}} : {{.*}}nightlytest{{.*}}</h2>
# CHECK: Render Time:
