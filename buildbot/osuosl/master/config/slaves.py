import buildbot
import buildbot.buildslave
import os

import config

def create_slave(name, *args, **kwargs):
    password = config.options.get('Slave Passwords', name)
    return buildbot.buildslave.BuildSlave(name, password=password, *args, **kwargs)

def get_build_slaves():
    return [
        # FreeBSD 11.0-CURRENT
        create_slave("as-bldslv5", properties={'jobs' : 24}, max_builds=2),

        # Linux Ubuntu 14.04 LTS
        create_slave("as-bldslv8", properties={'jobs' : 16}),

        # Mac Pro 2.7 GHz 12-Core Intel Xeon E5, Maverick 10.9.2
        create_slave("as-bldslv9", properties={'jobs' : 8}, max_builds=4),

        # ARMv7 Linaro slaves
        create_slave("linaro-tk1-01", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-tk1-02", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-tk1-03", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-tk1-04", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-tk1-05", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-tk1-06", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-tk1-07", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-tk1-08", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-tk1-09", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-armv8-01-arm-lnt", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-armv8-01-arm-selfhost-neon", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-armv8-01-arm-quick", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-armv8-01-arm-global-isel", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-armv8-01-arm-full", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-armv8-01-arm-full-selfhost", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-armv8-01-arm-lld", properties={'jobs' : 64}, max_builds=1),
        # Libcxx testsuite has tests with timing assumptions.  Run single-threaded to make
        # sure we have plenty CPU cycle to satisfy timing assumptions.
        create_slave("linaro-armv8-01-arm-libcxx", properties={'jobs' : 1}, max_builds=1),
        create_slave("linaro-armv8-01-arm-libcxx-noeh", properties={'jobs' : 1}, max_builds=1),
        create_slave("linaro-armv8-01-lldb-arm", properties={'jobs' : 64}, max_builds=1),
        # Packet.Net ThunderX1 for LLDB buildbot - Ubuntu Xenial 16.04 arm64 container
        create_slave("linaro-thx1-lldb-aarch64", properties={'jobs': 16}, max_builds=1),

        # AArch64 Linaro slaves
        create_slave("linaro-armv8-01-aarch64-quick", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-thx1-01-aarch64-quick", properties={'jobs' : 96}, max_builds=1),
        create_slave("linaro-armv8-01-aarch64-full", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-thx1-01-aarch64-full", properties={'jobs' : 96}, max_builds=1),
        create_slave("linaro-armv8-01-aarch64-global-isel", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-thx1-01-aarch64-global-isel", properties={'jobs' : 96}, max_builds=1),
        create_slave("linaro-armv8-01-aarch64-lld", properties={'jobs' : 64}, max_builds=1),
        create_slave("linaro-thx1-01-aarch64-lld", properties={'jobs' : 96}, max_builds=1),
        # Libcxx testsuite has tests with timing assumptions.  Run single-threaded to make
        # sure we have plenty CPU cycle to satisfy timing assumptions.
        create_slave("linaro-armv8-01-aarch64-libcxx", properties={'jobs' : 1}, max_builds=1),
        create_slave("linaro-thx1-01-aarch64-libcxx", properties={'jobs' : 1}, max_builds=1),
        create_slave("linaro-armv8-01-aarch64-libcxx-noeh", properties={'jobs' : 1}, max_builds=1),
        create_slave("linaro-thx1-01-aarch64-libcxx-noeh", properties={'jobs' : 1}, max_builds=1),

        # ARMv7 build cache slave
        create_slave("packet-linux-armv7-slave-1", properties={'jobs' : 64}, max_builds=1),

        # AArch64 build cache slave
        create_slave("packet-linux-aarch64-slave-1", properties={'jobs' : 64}, max_builds=1),


        # AMD Athlon(tm) 64 X2 Dual Core 3800+, Ubuntu x86_64
        create_slave("grosser1", properties={'jobs': 2}, max_builds=1),

        # Intel(R) Atom(TM) CPU D525 @ 1.8GHz, Fedora x86_64
        create_slave("atom1-buildbot", properties={'jobs': 2}, max_builds=1),

        # Windows 7 Intel(R) Xeon(R) CPU E5-2680 (2.80GHz), 16GB of RAM
        create_slave("windows7-buildbot", properties={'jobs': 2}, max_builds=1),

        # Windows Server 2016 Intel Xeon(R) Quad 2.30 GHz, 56GB of RAM
        create_slave("win-py3-buildbot", properties={'jobs' : 64}, max_builds=1),

        # POWER7 PowerPC big endian (powerpc64)
        create_slave("ppc64be-clang-test", properties={'jobs': 16}, max_builds=1),
        create_slave("ppc64be-clang-lnt-test", properties={'jobs': 16, 'vcs_protocol': 'https'}, max_builds=1),
        create_slave("ppc64be-clang-multistage-test", properties={'jobs': 16}, max_builds=1),
        create_slave("ppc64be-sanitizer", properties={'jobs': 16}, max_builds=1),

        # POWER 8 PowerPC little endian (powerpc64le)
        create_slave("ppc64le-clang-test", properties={'jobs': 4}, max_builds=1),
        create_slave("ppc64le-clang-lnt-test", properties={'jobs': 8}, max_builds=1),
        create_slave("ppc64le-clang-multistage-test", properties={'jobs': 8}, max_builds=1),
        create_slave("ppc64le-sanitizer", properties={'jobs': 4}, max_builds=1),
        create_slave("ppc64le-lld-multistage-test", properties={'jobs': 40}, max_builds=1),

        # POWER 8 PowerPC little endian (powerpc64le) with NVIDIA GPUs
        create_slave("ppc64le-nvidia-K40", properties={'jobs': 4}, max_builds=1),
        # POWER 8 PowerPC little endian (powerpc64le) with NVIDIA Pascal GPUs
        create_slave("ppc64le-nvidia-P100", properties={'jobs': 4}, max_builds=1),

        # Ubuntu x86-64, Intel(R) Xeon(R) CPU E5-2680 0 @ 2.70GHz
        create_slave("hexagon-build-02", properties={'jobs': 12, 'loadaverage': 32},
            max_builds=1),

        # Ubuntu x86-64, Intel(R) Xeon(R) CPU E5-2680 0 @ 2.70GHz
        create_slave("hexagon-build-03", properties={'jobs': 16, 'loadaverage':32},
            max_builds=1),

        # Ubuntu x86-64
        create_slave("avr-build-01", properties={'jobs': 10}, max_builds=1),

        # Arch Linux x86-64
        create_slave("riscv-build-01", properties={'jobs': 8}, max_builds=1),

        # Debian Jessie x86-64 GCE instance.
        create_slave("gribozavr3", properties={'jobs': 1}, max_builds=2),

        # Debian x86-64
        create_slave("gribozavr4", properties={'jobs': 96}, max_builds=2),

        # Debian 7.7 x86_64 GCE instance
        create_slave("sanitizer-buildbot1", properties={'jobs': 64}, max_builds=3),
        # Debian 7.7 x86_64 GCE instance
        create_slave("sanitizer-buildbot2", properties={'jobs': 64}, max_builds=3),
        # Debian 7.7 x86_64 GCE instance
        create_slave("sanitizer-buildbot3", properties={'jobs': 64}, max_builds=2),
        # Debian 7.7 x86_64 GCE instance
        create_slave("sanitizer-buildbot4", properties={'jobs': 64}, max_builds=2),
        # Debian 7.7 x86_64 GCE instance
        create_slave("sanitizer-buildbot5", properties={'jobs': 64}, max_builds=2),
        # Ubuntu 14.04 x86_64 6-core z440 workstation
        create_slave("sanitizer-buildbot6", properties={'jobs': 6}, max_builds=1),
        # Debian 7.7 x86_64 GCE instance
        create_slave("sanitizer-buildbot7", properties={'jobs': 64}, max_builds=3),
        # Debian 7.7 x86_64 GCE instance
        create_slave("sanitizer-buildbot8", properties={'jobs': 64}, max_builds=3),

        # Debian 7.7 x86_64 GCE instance
        create_slave("modules-slave-1", properties={'jobs': 16}, max_builds=1),

        # Debian 7.7 x86_64 GCE instance
        create_slave("modules-slave-2", properties={'jobs': 16}, max_builds=1),

        # IBM z13 (s390x), Ubuntu 16.04.2
        create_slave("systemz-1", properties={'jobs': 4, 'vcs_protocol': 'https'}, max_builds=4),

        # Ubuntu 14.10 x86_64, Intel(R) Xeon(R) CPU E3-1245 V2 @ 3.40GHz
        create_slave('ericwf-buildslave2', properties={'jobs': 4}, max_builds=2),

        # Debian 9, Docker based build. See libcxx/utils/docker.
        create_slave('libcxx-cloud1', properties={'jobs': 64}, max_builds=1),
        create_slave('libcxx-cloud2', properties={'jobs': 64}, max_builds=1),
        create_slave('libcxx-cloud3', properties={'jobs': 64}, max_builds=1),
        create_slave('libcxx-cloud4', properties={'jobs': 64}, max_builds=1),
        create_slave('libcxx-cloud5', properties={'jobs': 64}, max_builds=1),


        # Windows Server 2012 x86_64 16-core GCE instance
        create_slave("sanitizer-windows", properties={'jobs': 16}, max_builds=1),
        create_slave("windows-gcebot1", properties={'jobs': 8}, max_builds=1),
        # Windows Server 2012 x86_64 32-core GCE instance
        create_slave("windows-gcebot2", properties={'jobs': 32}, max_builds=1),
        # Windows Server 2016 x86_64 16-core GCE instance
        create_slave("windows-lld-thinlto-1", max_builds=1),

        # Ubuntu 14.04 x86_64-scei-ps4, 2 x Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
        create_slave("ps4-buildslave1"),
        create_slave("ps4-buildslave1a", properties={'jobs': 64}, max_builds=2),

        # Windows 10 Pro x86_64-scei-ps4, 2 x Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
        create_slave("ps4-buildslave2", properties={'jobs': 36}, max_builds=1),

        # Ubuntu 16.04.3 LTS x86_64-scei-ps4, 2 x Intel(R) Xeon(R) CPU E5-2699 v3 @ 2.30GHz
        create_slave("ps4-buildslave4"),

        # NetBSD amd64
        create_slave("netbsd-amd64", properties={'jobs': 8}, max_builds=1),

        # FreeBSD 11.0-CURRENT amd64, Intel(R) Xeon(R) CPU E3-1230 v3 @ 3.30GHz
        create_slave("freebsd01", properties={'jobs': 3}, max_builds=1),

        # Ubuntu 16.04 x86_64, 2 x Intel(R) Xeon(R) CPU E5-2690 v3 @ 2.60GHz, 64GB of RAM
        create_slave("cuda-build-test-01", properties={'jobs': 72}, max_builds=1),

        # Ubuntu 14.04 x86_64, AMD Athlon(tm) 5150 APU with Radeon(tm) R3, 8GiB RAM
        create_slave("am1i-slv1", properties={'jobs': 8}),

        # Ubuntu 16.04.2 LTS, AMD Athlon(tm) 5150 APU with Radeon(tm) R3, 8GiB RAM
        create_slave("am1i-slv2", properties={'jobs': 8}),

        # Ubuntu 14.04 x86_64, AMD Athlon(tm) 5150 APU with Radeon(tm) R3, 8GiB RAM
        create_slave("am1i-slv3", properties={'jobs': 8}),

        # Ubuntu 14.04 x86_64, AMD Athlon(tm) 5150 APU with Radeon(tm) R3, 8GiB RAM
        create_slave("am1i-slv4", properties={'jobs': 8}),

        # X86_64 AVX2, Ubuntu 16.04.2, Intel(R) Xeon(R) CPU E5-2699 v4 @ 2.20GHz
        create_slave("avx2-intel64", properties={'jobs': 80}, max_builds=1),

        # X86_64 with SDE, Ubuntu 16.04.2, Intel(R) Xeon(R) CPU E5-2699 v4 @ 2.20GHz
        create_slave("sde-avx512-intel64", properties={'jobs': 80}, max_builds=1),

        # FreeBSD 11 amd64
        create_slave("freebsd11-amd64", properties={'jobs': 2}, max_builds=1),

        # Debian 9.0 x86_64 64-core GCE instances
        create_slave("fuchsia-debian-64-us-central1-a-1", properties={'jobs': 64}, max_builds=1),
        create_slave("fuchsia-debian-64-us-central1-b-1", properties={'jobs': 64}, max_builds=1),

        # test only: Fedora latest stable x86_64, Intel i5-2500, 4 cores, 12GB RAM
        create_slave("lldb-x86_64-fedora", properties={'jobs': 4}, max_builds=1),

        # Debian x86_64 Buster Xeon(R) Gold 6154 CPU @ 3.00GHz, 192GB RAM
        create_slave("lldb-x86_64-debian", properties={'jobs': 72}, max_builds=1),

        # Windows dellfx2-sled3
        create_slave("as-builder-3", max_builds=1),

        # Ubuntu 18.04.2 LTS x86_64 Intel(R) Xeon(R) Gold CPU @ 2.1GHz, 128GB RAM
        create_slave("as-builder-4", properties={'jobs': 64}, max_builds=1),

        # Solaris 11
        create_slave("solaris11-amd64", properties={'jobs' : 8}, max_builds=1),
        create_slave("solaris11-sparcv9", properties={'jobs' : 8}, max_builds=1),

        ]
