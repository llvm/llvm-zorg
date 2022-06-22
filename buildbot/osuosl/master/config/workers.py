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
        create_worker("linaro-clang-armv7-lnt", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-clang-armv7-2stage", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-clang-armv7-quick", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-clang-armv7-global-isel", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-clang-armv7-vfpv3-2stage", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-clang-armv8-lld-2stage", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-lldb-arm-ubuntu", properties={'jobs' : 16}, max_builds=1),

        # AArch64 Linaro workers
        create_worker("linaro-clang-aarch64-quick", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-clang-aarch64-lld-2stage", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-clang-aarch64-global-isel", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-clang-aarch64-full-2stage", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-clang-aarch64-sve-vla", properties={'jobs' : 48}, max_builds=1),
        create_worker("linaro-clang-aarch64-sve-vla-2stage", properties={'jobs' : 48}, max_builds=1),
        create_worker("linaro-clang-aarch64-sve-vls", properties={'jobs' : 48}, max_builds=1),
        create_worker("linaro-clang-aarch64-sve-vls-2stage", properties={'jobs' : 48}, max_builds=1),
        create_worker("linaro-lldb-aarch64-ubuntu", properties={'jobs': 16}, max_builds=1),
        create_worker("linaro-flang-aarch64-dylib", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-flang-aarch64-sharedlibs", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-flang-aarch64-out-of-tree", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-flang-aarch64-debug", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-flang-aarch64-latest-clang", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-flang-aarch64-release", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-flang-aarch64-rel-assert", properties={'jobs' : 32}, max_builds=1),
        create_worker("linaro-flang-aarch64-latest-gcc", properties={'jobs' : 32}, max_builds=1),

        # AArch64 Windows Microsoft Surface X Pro
        create_worker("linaro-armv8-windows-msvc-01", properties={'jobs' : 8}, max_builds=1),
        create_worker("linaro-armv8-windows-msvc-02", properties={'jobs' : 8}, max_builds=1),
        create_worker("linaro-lldb-aarch64-windows", properties={'jobs' : 8}, max_builds=1),

        # Windows Server 2016 Intel Xeon(R) Quad 2.30 GHz, 56GB of RAM
        create_worker("win-py3-buildbot", properties={'jobs' : 64}, max_builds=1),

        # Windows Server 2016 Intel(R) Xeon(R) CPU @ 2.60GHz, 16 Core(s), 128 GB of RAM
        create_worker("win-mlir-buildbot", properties={'jobs' : 64}, max_builds=1),

        # MIPS Loongson-3A R4 (Loongson-3A4000) 64-bit little endian (mips64el)
        create_worker("debian-tritium-mips64el", properties={'jobs': 1}, max_builds=1),

        # Motorola 68k 32-bit big endian (m68k)
        create_worker("debian-akiko-m68k", properties={'jobs': 1}, max_builds=1),
        create_worker("suse-gary-m68k-cross", properties={'jobs': 4}, max_builds=1),

        # POWER7 PowerPC big endian (powerpc64)
        create_worker("ppc64be-clang-lnt-test", properties={'jobs': 16, 'vcs_protocol': 'https'}, max_builds=1),
        create_worker("ppc64be-clang-multistage-test", properties={'jobs': 16}, max_builds=1),
        create_worker("ppc64be-sanitizer", properties={'jobs': 16}, max_builds=1),

        # POWER 8 PowerPC little endian (powerpc64le)
        create_worker("ppc64le-clang-lnt-test", properties={'jobs': 8}, max_builds=1),
        create_worker("ppc64le-clang-multistage-test", properties={'jobs': 8}, max_builds=1),
        create_worker("ppc64le-sanitizer", properties={'jobs': 4}, max_builds=1),
        create_worker("ppc64le-lld-multistage-test", max_builds=1),
        create_worker("ppc64le-clang-rhel-test", properties={'jobs': 192}, max_builds=1),
        create_worker("ppc64le-flang-rhel-test", max_builds=1),
        create_worker("ppc64le-mlir-rhel-test", max_builds=1),

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

        # Debian x86_64 GCE instance
        create_worker("sanitizer-buildbot1", properties={'jobs': 64}, max_builds=2),
        # Debian x86_64 GCE instance
        create_worker("sanitizer-buildbot2", properties={'jobs': 64}, max_builds=2),
        # Debian x86_64 GCE instance
        create_worker("sanitizer-buildbot3", properties={'jobs': 64}, max_builds=2),
        # Debian x86_64 GCE instance
        create_worker("sanitizer-buildbot4", properties={'jobs': 64}, max_builds=2),
        # Ubuntu x86_64 6-core z440 workstation
        create_worker("sanitizer-buildbot6", properties={'jobs': 6}, max_builds=1),
        # Debian x86_64 GCE instance
        create_worker("sanitizer-buildbot7", properties={'jobs': 64}, max_builds=2),
        # Debian x86_64 GCE instance
        create_worker("sanitizer-buildbot8", properties={'jobs': 64}, max_builds=2),

        # POWER 8 PowerPC AIX 7.2
        create_worker("aix-ppc64", properties={'jobs': 10}, max_builds=1),
        create_worker("aix-ppc-libcxx", properties={'jobs': 4}, max_builds=1),

        # IBM z13 (s390x), Ubuntu 16.04.2
        create_worker("systemz-1", properties={'jobs': 4, 'vcs_protocol': 'https'}, max_builds=4),

        # Windows Server 2012 x86_64 16-core GCE instance
        create_worker("sanitizer-windows", properties={'jobs': 16}, max_builds=1),
        # Windows Server 2012 x86_64 32-core GCE instance
        create_worker("windows-gcebot2", properties={'jobs': 32}, max_builds=1),

        # Ubuntu 14.04 x86_64-scei-ps4, 2 x Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
        create_worker("as-worker-91", max_builds=1),
        create_worker("as-worker-92", max_builds=1),

        # Windows 10 Pro x86_64-scei-ps4, 2 x Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
        create_worker("as-worker-93", properties={'jobs': 36}, max_builds=1),

        # WIP migration of the CUDA buildbot to GCE.
        create_worker("cuda-k80-0", max_builds=1),
        create_worker("cuda-p4-0", max_builds=1),
        create_worker("cuda-t4-0", max_builds=1),

        # HIP on Ubuntu 18.04.5,  Intel(R) Xeon(R) Gold 5218 @ 2.30GHz, Vega20 GPU
        create_worker("hip-vega20-0", max_builds=1),

        # X86_64 AVX2, Ubuntu 16.04.2, Intel(R) Xeon(R) CPU E5-2699 v4 @ 2.20GHz
        create_worker("avx2-intel64", properties={'jobs': 80}, max_builds=1),

        # X86_64 with SDE, Ubuntu 16.04.2, Intel(R) Xeon(R) CPU E5-2699 v4 @ 2.20GHz
        create_worker("sde-avx512-intel64", properties={'jobs': 80}, max_builds=1),

        # Debian 9.0 x86_64 64-core GCE instances
        create_worker("fuchsia-debian-64-us-central1-a-1", properties={'jobs': 64}, max_builds=1),
        create_worker("fuchsia-debian-64-us-central1-b-1", properties={'jobs': 64}, max_builds=1),

        # Debian x86_64 Buster Xeon(R) Gold 6154 CPU @ 3.00GHz, 192GB RAM
        create_worker("lldb-x86_64-debian", properties={'jobs': 72}, max_builds=1),

        # Windows x86_64 32 CPUs, 125 GB RAM
        create_worker("libc-x86_64-windows", properties={'jobs': 32}, max_builds=2),

        # Debian arm32 single core, 512 MB RAM backed by 32 GB swap memory
        create_worker("libc-arm32-debian", properties={'jobs': 1}, max_builds=1),

        # Ubuntu aarch64 128 CPUs, 125 GB RAM
        create_worker("libc-aarch64-ubuntu", properties={'jobs': 32}, max_builds=2),

        # Debian x86_64 Intel Broadwell 32 CPUs, 120 GB RAM
        create_worker("libc-x86_64-debian", properties={'jobs': 32}, max_builds=2),

        # Debian x86_64 Intel Skylake 32 CPUs, 128 GB RAM
        create_worker("libc-x86_64-debian-fullbuild", properties={'jobs': 32}, max_builds=2),

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

        # Windows Server on Xeon Gold 6230 (2x2.1GHz), 256Gb of RAM
        create_worker("as-builder-5", properties={  # arm
                        'remote_test_host': 'jetson4.lab.llvm.org',
                        'remote_test_user': 'ubuntu'
                     },
                     max_builds=1),
        create_worker("as-builder-6", properties={  # aarch64
                        'remote_test_host': 'jetson8.lab.llvm.org',
                        'remote_test_user': 'ubuntu'
                     },
                     max_builds=1),

        # Solaris 11
        create_worker("solaris11-amd64", properties={'jobs' : 8}, max_builds=1),
        create_worker("solaris11-sparcv9", properties={'jobs' : 8}, max_builds=1),

        # CentOS 7.8.1127 on Intel(R) Xeon(R) Gold 6126 CPU @ 2.60GHz, 96GB RAM
        create_worker("hpce-aurora2", properties={'jobs': 8}, max_builds=1),
        create_worker("hpce-ve-main", properties={'jobs': 8}, max_builds=1),
        create_worker("hpce-ve-staging", properties={'jobs': 8}, max_builds=1),

        # Ubuntu 18.04 amd64 on Google Cloud, 16 core, Nvidia Tesla T4
        create_worker("mlir-nvidia", properties={'jobs': 16}, max_builds=1),

        # Ubuntu 18.04 pool of VMs on GCP
        create_worker("mlir-ubuntu-worker0", max_builds=1),
        create_worker("mlir-ubuntu-worker1", max_builds=1),
        create_worker("mlir-ubuntu-worker2", max_builds=1),
        create_worker("mlir-ubuntu-worker3", max_builds=1),
        create_worker("mlir-ubuntu-worker4", max_builds=1),

        # Ubuntu 18.04 on Google Cloud, for machine configuration check
        # buildbot/google/terraform/main.tf
        create_worker("clangd-ubuntu-clang", max_builds=1),

        # Ubuntu 18.04.LTS x86_64, GCE instance
        create_worker("polly-x86_64-gce1", properties={'jobs': 2}, max_builds=1),
        create_worker("polly-x86_64-gce2", properties={'jobs': 2}, max_builds=1),

        # Ubuntu 18.04.LTS x86_64, Intel(R) Xeon(R) CPU X3460 @ 2.80GHz, 32 GiB RAM
        create_worker("polly-x86_64-fdcserver", properties={'jobs': 8, 'loadaverage': 8}, max_builds=1),

        # Windows 10, AMD Ryzen 5 PRO 4650G, 16 GiB RAM
        create_worker("minipc-ryzen-win", properties={'jobs': 12}, max_builds=1),

        # Ubuntu 20.04.LTS x86_64, Intel(R) Core(TM) i5-9400F CPU @ 2.90Ghz, 16 GiB RAM, NVIDIA GeForce GTX 1050 Ti (Pascal, sm_61, 4GiB)
        create_worker("minipc-1050ti-linux", properties={'jobs': 6}, max_builds=1),

        create_worker("alcf-theta-flang", properties={'jobs': 12}, max_builds=1),

        # ML-Driven Compiler Optimizations build workers (Ubuntu x86_64)
        create_worker("ml-opt-dev-x86-64-b1",
                      properties={'jobs': 64}, max_builds=1,
                      notify_on_missing='mlcompileropt-buildbot@google.com'),
        create_worker("ml-opt-rel-x86-64-b1",
                      properties={'jobs': 64}, max_builds=1,
                      notify_on_missing='mlcompileropt-buildbot@google.com'),
        create_worker("ml-opt-devrel-x86-64-b1",
                      properties={'jobs': 64}, max_builds=1,
                      notify_on_missing='mlcompileropt-buildbot@google.com'),
        create_worker("ml-opt-dev-x86-64-b2",
                      properties={'jobs': 64}, max_builds=1,
                      notify_on_missing='mlcompileropt-buildbot@google.com'),
        create_worker("ml-opt-rel-x86-64-b2",
                      properties={'jobs': 64}, max_builds=1,
                      notify_on_missing='mlcompileropt-buildbot@google.com'),
        create_worker("ml-opt-devrel-x86-64-b2",
                      properties={'jobs': 64}, max_builds=1,
                      notify_on_missing='mlcompileropt-buildbot@google.com'),

        # Ubuntu x86_64
        create_worker("thinlto-x86-64-bot1", properties={'jobs': 64}, max_builds=1),
        create_worker("thinlto-x86-64-bot2", properties={'jobs': 64}, max_builds=1),

        # Ubuntu 20.04 on AWS, x86_64 PS4 target
        create_worker("sie-linux-worker", properties={'jobs': 40}, max_builds=1),

        # Windows Server 2019 on AWS, x86_64 PS4 target
        create_worker("sie-win-worker", properties={'jobs': 64}, max_builds=1),

        # XCore target, Ubuntu 20.04 x64 host
        create_worker("xcore-ubuntu20-x64", properties={'jobs': 4}, max_builds=1),

        # ARC Worker, CentOS 7.9 x86_64 Intel Xeon Platinum 8000 @ 3.6GHz, 32GB RAM
        create_worker("arc-worker", properties={'jobs': 16}, max_builds=1),

        # OpenMP on AMDGPU, Ubuntu 18.04.5, Intel(R) Xeon(R) Gold 5218 @ 2.30GHz with 64GB Memory, 1 Vega20 GPU with 16GB Memory
        create_worker("omp-vega20-0", properties={'jobs': 32}, max_builds=1),
        create_worker("omp-vega20-1", properties={'jobs': 32}, max_builds=1),

        # AMD ROCm support, Ubuntu 18.04.6, AMD Ryzen @ 1.5 GHz, MI200 GPU
        create_worker("mi200-buildbot", max_builds=1),

        # BOLT workers
        create_worker("bolt-worker", properties={'jobs' : 16}, max_builds=1),
        create_worker("bolt-worker-aarch64", properties={'jobs' : 2}, max_builds=1),

        # Fedora worker
        create_worker("standalone-build-x86_64", properties={'jobs': 32}, max_builds=1),

        # CSKY T-HEAD workers
        create_worker("thead-clang-csky", properties={'jobs' : 32}, max_builds=1),
        ]
