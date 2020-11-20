# TODO: Rename workers with "slave" as a part of the name.
# TODO: Refactor to define a list of tuples, each of which describes a worker, then enumerate and create as data driven.

from buildbot.plugins import worker
import config

def create_worker(name, *args, **kwargs):
    password = config.options.get('Worker Passwords', name)
    return worker.Worker(name, password=password, *args, **kwargs)

def get_all():
    return [
        # FreeBSD
        create_worker("as-worker-4", properties={'jobs' : 24}, max_builds=2),

        # Linux Ubuntu
        create_worker("as-worker-5", properties={'jobs' : 16}),

        # Mac Pro 2.7 GHz 12-Core Intel Xeon E5, Maverick 10.9.2
        create_worker("as-worker-3", properties={'jobs' : 8}, max_builds=4),

        # ARMv7/ARMv8 Linaro workers
        create_worker("linaro-tk1-01", properties={'jobs' : 4}, max_builds=1),
        create_worker("linaro-tk1-02", properties={'jobs' : 4}, max_builds=1),
        create_worker("linaro-tk1-03", properties={'jobs' : 4}, max_builds=1),
        create_worker("linaro-tk1-04", properties={'jobs' : 4}, max_builds=1),
        create_worker("linaro-tk1-05", properties={'jobs' : 4}, max_builds=1),
        create_worker("linaro-tk1-06", properties={'jobs' : 4}, max_builds=1),
        create_worker("linaro-tk1-07", properties={'jobs' : 4}, max_builds=1),
        create_worker("linaro-tk1-08", properties={'jobs' : 4}, max_builds=1),
        create_worker("linaro-tk1-09", properties={'jobs' : 4}, max_builds=1),
        create_worker("linaro-armv7-lnt", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-armv7-selfhost", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-armv7-quick", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-armv7-global-isel", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-armv8-lld", properties={'jobs' : 32}, max_builds=1),
        # Libcxx testsuite has tests with timing assumptions.  Run single-threaded to make
        # sure we have plenty CPU cycle to satisfy timing assumptions.
        create_worker("linaro-armv8-libcxx", properties={'jobs' : 1}, max_builds=1),
        create_worker("linaro-arm-lldb", properties={'jobs' : 16}, max_builds=1),

        # AArch64 Linaro workers
        create_worker("linaro-aarch64-quick", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-aarch64-full", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-aarch64-global-isel", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-aarch64-lld", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-aarch64-flang-oot", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-aarch64-flang-dylib", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-aarch64-flang-sharedlibs", properties={'jobs' : 32}, max_builds=1),
        # Libcxx testsuite has tests with timing assumptions.  Run single-threaded to make
        # sure we have plenty CPU cycle to satisfy timing assumptions.
        create_worker("linaro-aarch64-libcxx", properties={'jobs' : 1}, max_builds=1),
        create_worker("linaro-aarch64-lldb", properties={'jobs': 16}, max_builds=1),

        # AArch64
        create_worker("linaro-armv8-windows-msvc-01", properties={'jobs' : 8}, max_builds=1),
        create_worker("linaro-armv8-windows-msvc-02", properties={'jobs' : 8}, max_builds=1),

        # ARMv7 build cache workers
        create_worker("packet-linux-armv7-slave-1", properties={'jobs' : 64}, max_builds=1),

        # AArch64 build cache worker
        create_worker("packet-linux-aarch64-slave-1", properties={'jobs' : 64}, max_builds=1),

        # Windows Server 2016 Intel Xeon(R) Quad 2.30 GHz, 56GB of RAM
        create_worker("win-py3-buildbot", properties={'jobs' : 64}, max_builds=1),

        # Windows Server 2016 Intel(R) Xeon(R) CPU @ 2.60GHz, 16 Core(s), 128 GB of RAM
        create_worker("win-mlir-buildbot", properties={'jobs' : 64}, max_builds=1),

        # POWER7 PowerPC big endian (powerpc64)
        create_worker("ppc64be-clang-test", properties={'jobs': 16}, max_builds=1),
        create_worker("ppc64be-clang-lnt-test", properties={'jobs': 16, 'vcs_protocol': 'https'}, max_builds=1),
        create_worker("ppc64be-clang-multistage-test", properties={'jobs': 16}, max_builds=1),
        create_worker("ppc64be-sanitizer", properties={'jobs': 16}, max_builds=1),

        # POWER 8 PowerPC little endian (powerpc64le)
        create_worker("ppc64le-clang-test", properties={'jobs': 4}, max_builds=1),
        create_worker("ppc64le-clang-lnt-test", properties={'jobs': 8}, max_builds=1),
        create_worker("ppc64le-clang-multistage-test", properties={'jobs': 8}, max_builds=1),
        create_worker("ppc64le-sanitizer", properties={'jobs': 4}, max_builds=1),
        create_worker("ppc64le-lld-multistage-test", max_builds=1),
        create_worker("ppc64le-clang-rhel-test", properties={'jobs': 4}, max_builds=1),
        create_worker("ppc64le-flang-mlir-rhel-test", max_builds=1),

        # SPARC 64-bit big endian (sparc64)
        create_worker("debian-stadler-sparc64", properties={'jobs': 4}, max_builds=1),

        # Ubuntu x86-64, Intel(R) Xeon(R) CPU E5-2680 0 @ 2.70GHz
        create_worker("hexagon-build-02", properties={'jobs': 12, 'loadaverage': 32},
            max_builds=1),

        # Ubuntu x86-64, Intel(R) Xeon(R) CPU E5-2680 0 @ 2.70GHz
        create_worker("hexagon-build-03", properties={'jobs': 16, 'loadaverage':32},
            max_builds=1),

        # Ubuntu x86-64
        create_worker("avr-build-01", properties={'jobs': 10}, max_builds=1),

        # Debian Jessie x86-64 GCE instance.
        create_worker("gribozavr3", properties={'jobs': 1}, max_builds=2),

        # Debian x86-64
        create_worker("gribozavr4", properties={'jobs': 96}, max_builds=2),
        create_worker("gribozavr5", properties={'jobs': 96}, max_builds=2,
                     missing_timeout=300, # notify after 5 minutes of missing
                     notify_on_missing=[
                         "gribozavr@gmail.com",
                         "gkistanova@gmail.com"]),

        # Debian 7.7 x86_64 GCE instance
        create_worker("sanitizer-buildbot1", properties={'jobs': 64}, max_builds=3),
        # Debian 7.7 x86_64 GCE instance
        create_worker("sanitizer-buildbot2", properties={'jobs': 64}, max_builds=3),
        # Debian 7.7 x86_64 GCE instance
        create_worker("sanitizer-buildbot3", properties={'jobs': 64}, max_builds=2),
        # Debian 7.7 x86_64 GCE instance
        create_worker("sanitizer-buildbot4", properties={'jobs': 64}, max_builds=2),
        # Ubuntu 14.04 x86_64 6-core z440 workstation
        create_worker("sanitizer-buildbot6", properties={'jobs': 6}, max_builds=1),
        # Debian 7.7 x86_64 GCE instance
        create_worker("sanitizer-buildbot7", properties={'jobs': 64}, max_builds=3),
        # Debian 7.7 x86_64 GCE instance
        create_worker("sanitizer-buildbot8", properties={'jobs': 64}, max_builds=3),

        # IBM z13 (s390x), Ubuntu 16.04.2
        create_worker("systemz-1", properties={'jobs': 4, 'vcs_protocol': 'https'}, max_builds=4),

        # Debian 9, Docker based build. See libcxx/utils/docker.
        create_worker('libcxx-cloud1', properties={'jobs': 64}, max_builds=1),
        create_worker('libcxx-cloud2', properties={'jobs': 64}, max_builds=1),
        create_worker('libcxx-cloud3', properties={'jobs': 64}, max_builds=1),
        create_worker('libcxx-cloud4', properties={'jobs': 64}, max_builds=1),
        create_worker('libcxx-cloud5', properties={'jobs': 64}, max_builds=1),


        # Windows Server 2012 x86_64 16-core GCE instance
        create_worker("sanitizer-windows", properties={'jobs': 16}, max_builds=1),
        # Windows Server 2012 x86_64 32-core GCE instance
        create_worker("windows-gcebot2", properties={'jobs': 32}, max_builds=1),

        # Ubuntu 14.04 x86_64-scei-ps4, 2 x Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
        create_worker("as-worker-91"),
        create_worker("as-worker-92"),

        # Windows 10 Pro x86_64-scei-ps4, 2 x Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
        create_worker("as-worker-93", properties={'jobs': 36}, max_builds=1),

        # WIP migration of the CUDA buildbot to GCE.
        create_worker("cuda-k80-0", max_builds=1),
        create_worker("cuda-p4-0", max_builds=1),
        create_worker("cuda-t4-0", max_builds=1),

        # X86_64 AVX2, Ubuntu 16.04.2, Intel(R) Xeon(R) CPU E5-2699 v4 @ 2.20GHz
        create_worker("avx2-intel64", properties={'jobs': 80}, max_builds=1),

        # X86_64 with SDE, Ubuntu 16.04.2, Intel(R) Xeon(R) CPU E5-2699 v4 @ 2.20GHz
        create_worker("sde-avx512-intel64", properties={'jobs': 80}, max_builds=1),

        # Debian 9.0 x86_64 64-core GCE instances
        create_worker("fuchsia-debian-64-us-central1-a-1", properties={'jobs': 64}, max_builds=1),
        create_worker("fuchsia-debian-64-us-central1-b-1", properties={'jobs': 64}, max_builds=1),

        # Fedora latest stable x86_64, Intel i5-2500, 4 cores, 12GB RAM
        create_worker("lldb-x86_64-fedora", properties={'jobs': 4}, max_builds=1),

        # Fedora latest stable, arch=x86_64, running on RedHat internal OpenShift PSI cluster
        create_worker("fedora-llvm-x86_64", properties={'jobs': 64}, max_builds=1),

        # Debian x86_64 Buster Xeon(R) Gold 6154 CPU @ 3.00GHz, 192GB RAM
        create_worker("lldb-x86_64-debian", properties={'jobs': 72}, max_builds=1),

        # Debian x86_64 Intel Broadwell 32 CPUs, 120 GB RAM
        create_worker("libc-x86_64-debian", properties={'jobs': 32}, max_builds=2),

        # Windows Server on Xeon Gold 6130 (2x2.1GHz), 128Gb of RAM
        create_worker("as-builder-1", properties={
                        'remote_test_host': 'jetson6.lab.llvm.org',
                        'remote_test_user': 'ubuntu'
                     },
                     max_builds=1),

        # Windows Server on Xeon Gold 6130 (2x2.1GHz), 128Gb of RAM
        create_worker("as-builder-2", properties={
                        'remote_test_host': 'jetson9.lab.llvm.org',
                        'remote_test_user': 'ubuntu'
                     },
                     max_builds=1),

        # Windows dellfx2-sled3
        create_worker("as-builder-3", max_builds=1),

        # Ubuntu 18.04.2 LTS x86_64 Intel(R) Xeon(R) Gold CPU @ 2.1GHz, 128GB RAM
        create_worker("as-builder-4", properties={'jobs': 64}, max_builds=1),

        # Solaris 11
        create_worker("solaris11-amd64", properties={'jobs' : 8}, max_builds=1),
        create_worker("solaris11-sparcv9", properties={'jobs' : 8}, max_builds=1),

        # Windows 7 Intel(R) Core(TM) CPU i7-4790K (4.00GHz), 16GB of RAM
        create_worker("windows7-buildbot", properties={'jobs': 2}, max_builds=1),

        # Windows 10, Visual Studio 2019, Google Cloud 16 cores
        create_worker("windows10-vs2019", properties={'jobs': 32}, max_builds=1),

        # CentOS 7.5.1804 on Intel(R) Xeon(R) Gold 6126 CPU @ 2.60GHz, 96GB RAM
        create_worker("nec-arrproto41", properties={'jobs': 12}, max_builds=1),

        # Ubuntu 18.04 amd64 on Google Cloud, 16 core, Nvidia Tesla T4
        create_worker("mlir-nvidia", properties={'jobs': 16}, max_builds=1),

        # Ubuntu 18.04 on Google Cloud, for machine configuration check
        # buildbot/google/terraform/main.tf
        create_worker("clangd-ubuntu-clang", max_builds=1),

        # Ubuntu 18.04.LTS x86_64, GCE instance
        create_worker("polly-x86_64-gce1", properties={'jobs': 2}, max_builds=1),
        create_worker("polly-x86_64-gce2", properties={'jobs': 2}, max_builds=1),

        # Ubuntu 18.04.LTS x86_64, Intel(R) Xeon(R) CPU X3460 @ 2.80GHz, 32 GiB RAM
        create_worker("polly-x86_64-fdcserver", properties={'jobs': 8, 'loadaverage': 8}, max_builds=1),

        create_worker("flang-aarch64-ubuntu-build"),
        create_worker("flang-aarch64-ubuntu-clang-build", properties={'jobs': 14}),
        create_worker("flang-aarch64-ubuntu-gcc10-build", properties={'jobs': 14}),
        create_worker("nersc-flang"),
        create_worker("alcf-theta-flang", properties={'jobs': 12}, max_builds=1),

        # ML-Driven Compiler Optimizations build workers (Ubuntu x86_64)
        create_worker("ml-opt-dev-x86-64-b1",
                     properties={'jobs': 64}, max_builds=1),
        create_worker("ml-opt-rel-x86-64-b1",
                     properties={'jobs': 64}, max_builds=1),
        create_worker("ml-opt-devrel-x86-64-b1",
                     properties={'jobs': 64}, max_builds=1),

        # Ubuntu x86_64
        create_worker("thinlto-x86-64-bot1", properties={'jobs': 64}, max_builds=1),
        ]
