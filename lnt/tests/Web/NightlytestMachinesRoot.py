# RUN: curl -s %base_url/nightlytest/machines/1/ | FileCheck %s
# CHECK: <h2>{{.*}}LNT{{.*}} : {{.*}}nightlytest{{.*}}</h2>
# CHECK: Render Time:

