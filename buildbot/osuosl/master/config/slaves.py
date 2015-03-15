import buildbot
import buildbot.buildslave
import os

import config

def create_slave(name, *args, **kwargs):
    password = config.options.get('Slave Passwords', name)
    return buildbot.buildslave.BuildSlave(name, password=password, *args, **kwargs)

def get_build_slaves():
    return [
        # Ubuntu pandaboard cortex-a9 slaves
        create_slave("as-bldslv1", properties={'jobs' : 2}, max_builds=1),
        create_slave("as-bldslv2", properties={'jobs' : 2}, max_builds=1),
        create_slave("as-bldslv3", properties={'jobs' : 2}, max_builds=1),

        # Windows 7 Professional x64
        create_slave("as-bldslv4", properties={'jobs' : 2}, max_builds=1),

        # FreeBSD 9.2-RELEASE
        create_slave("as-bldslv5", properties={'jobs' : 24}, max_builds=2),

        # Windows 7 Ultimate
        create_slave("as-bldslv7", properties={'jobs' : 1}, max_builds=1),

        # FreeBSD 8.2 X86_64
        create_slave("as-bldslv8", properties={'jobs' : 2}, max_builds=1),

        # Mac Pro 2.7 GHz 12-Core Intel Xeon E5, Maverick 10.9.2
        create_slave("as-bldslv9", properties={'jobs' : 8}, max_builds=4),

        # Cortex-A15 slaves
        create_slave("linaro-chrome-01", properties={'jobs' : 2}, max_builds=1),
        create_slave("linaro-chrome-02", properties={'jobs' : 2}, max_builds=1),
        create_slave("linaro-chrome-03", properties={'jobs' : 2}, max_builds=1),
        create_slave("linaro-chrome-04", properties={'jobs' : 2}, max_builds=1),
        create_slave("linaro-chrome-05", properties={'jobs' : 2}, max_builds=1),

        create_slave("linaro-a15-01", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-a15-02", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-a15-03", properties={'jobs' : 4}, max_builds=1),
        create_slave("linaro-a15-04", properties={'jobs' : 4}, max_builds=1),

        create_slave("linaro-dragon-01", properties={'jobs' : 4}, max_builds=1),

        # AMD Athlon(tm) 64 X2 Dual Core 3800+, Ubuntu x86_64
        create_slave("grosser1", properties={'jobs': 2}, max_builds=1),

        # Intel(R) Core(TM)2 Quad CPU Q6600  @ 2.40GHz, Debian x86_64 GNU/Linux
        #create_slave("grosser2", properties={'jobs': 4}, max_builds=1),

        # Polly perf servers
        # Each is a:
        # 8 x Intel(R) Xeon(R) CPU E5430  @ 2.66GHz, Debian x86_64 GNU/Linux
        #create_slave("pollyperf1", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf2", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf3", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf4", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf5", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf6", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf7", properties={'jobs': 8}, max_builds=1),
        #create_slave("pollyperf8", properties={'jobs': 8}, max_builds=1),
        #create_slave("pollyperf9", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf10", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf11", properties={'jobs': 8}, max_builds=1),
        #create_slave("pollyperf12", properties={'jobs': 8}, max_builds=1),
        #create_slave("pollyperf13", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf14", properties={'jobs': 8}, max_builds=1),
        create_slave("pollyperf15", properties={'jobs': 8}, max_builds=1),

        # Intel(R) Atom(TM) CPU D525 @ 1.8GHz, Fedora x86_64
        create_slave("atom-buildbot", properties={'jobs': 2}, max_builds=1),
        create_slave("atom1-buildbot", properties={'jobs': 2}, max_builds=1),

        # Windows 7 Intel(R) Xeon(R) CPU E5-2680 (2.80GHz), 16GB of RAM
        create_slave("windows7-buildbot", properties={'jobs': 2}, max_builds=1),

        # LLVM Lab slaves
        create_slave("hpproliant1", properties={'jobs': 6}, max_builds=1),

        # POWER7 PowerPC (powerpc64), Fedora16.
        create_slave("chinook", properties={'jobs': 4}, max_builds=2),
        #    LNT slave
        create_slave("chinook-clangslave1", properties={'jobs': 4}, max_builds=2),
        #    Clang build slave
        create_slave("chinook-clangslave2", properties={'jobs': 4}, max_builds=2),

        # POWER7 PowerPC (powerpc64), Fedora16.
        create_slave("coho", properties={'jobs': 4}, max_builds=2),

        create_slave("sanitizer-ppc64-1", properties={'jobs': 4}, max_builds=1),

        # ppc64le slaves.  
        create_slave("ppc64le-llvm", properties={'jobs': 8}, max_builds=1),
        create_slave("ppc64le-clang", properties={'jobs': 8}, max_builds=1),
        create_slave("ppc64le-clanglnt", properties={'jobs': 8}, max_builds=1),
        create_slave("sanitizer-ppc64le-linux", properties={'jobs': 8}, max_builds=1),

        # Debian 86_64, 2 x 6-core Opteron 2.6 GHz
        create_slave("osu8", properties={'jobs' : 6}, max_builds=2),

        # Windows 6.1.7601 x86-64, Intel(R) Xeon(R) CPU E5-2680 0 @ 2.70GHz
        create_slave("hexagon-build-01", properties={'jobs': 4}, max_builds=2),

        # TODO: This slave is idle for now. Review the usage later.
        # Ubuntu x86-64, Intel(R) Xeon(R) CPU E5-2680 0 @ 2.70GHz
        create_slave("hexagon-build-02", properties={'jobs': 12, 'loadaverage': 32},
            max_builds=4),

        # Ubuntu x86-64, Intel(R) Xeon(R) CPU E5-2680 0 @ 2.70GHz
        create_slave("hexagon-build-03", properties={'jobs': 16, 'loadaverage':
32},
            max_builds=4),

        # Cavium Octeon II V0.8, MIPS64r2 big endian, Debian squeeze (6.0.6)
        create_slave("mipsswbrd002", properties={'jobs' : 6}, max_builds=1),

        # Cavium Octeon II V0.2, MIPS64r2 big endian, Debian Jessie
        create_slave("mips-kl-m001", properties={'jobs' : 10}, max_builds=1),

        # Debian Testing x86-64, Intel(R) Core(TM) i7-2700K CPU @ 3.50GHz
        #create_slave("gribozavr1", properties={'jobs': 8}, max_builds=1),

        # Ubuntu 13.04 x86-64, Intel(R) Xeon(R) CPU 5160 @ 3.00GHz
        create_slave("gribozavr2", properties={'jobs': 4}, max_builds=1),

        # CentOS 6.5 x86-64, VM on Intel(R) Core(TM) i5 CPU 750 @ 2.67GHz
        create_slave("gribozavr3", properties={'jobs': 4}, max_builds=1),

        # Debian x86-64
        create_slave("gribozavr4", properties={'jobs': 18}, max_builds=1),

        # Ubuntu 14.04 x86-64
        create_slave("gribozavr5", properties={'jobs': 6}, max_builds=1),

        # OpenBSD
        create_slave("openbsd-buildslave", properties={'jobs': 2}, max_builds=1),

        # Aarch64 Foundation Model
        create_slave("aarch64-foundation", properties={'jobs': 4}, max_builds=1),

        # AArch64 Qemu LNT
        create_slave("aarch64-qemu-lnt", properties={'jobs': 4}, max_builds=1),

        # AArch64 Clang, Juno ARM Development Platform
        create_slave("juno-aarch64-01", properties={'jobs': 4}, max_builds=1),

        # Debian 7.7 x86_64 16-core GCE instance
        create_slave("sanitizer-buildbot1", properties={'jobs': 16}, max_builds=1),
        # Debian 7.7 x86_64 16-core GCE instance
        create_slave("sanitizer-buildbot2", properties={'jobs': 16}, max_builds=1),
        # Debian 7.7 x86_64 8-core GCE instance
        create_slave("sanitizer-buildbot3", properties={'jobs': 8}, max_builds=1),
        # Debian 7.7 x86_64 8-core GCE instance
        create_slave("sanitizer-buildbot4", properties={'jobs': 8}, max_builds=1),
        # Debian 7.7 x86_64 8-core GCE instance
        create_slave("sanitizer-buildbot5", properties={'jobs': 8}, max_builds=1),

        # Debian 7.7 x86_64 GCE instance
        create_slave("modules-slave-1", properties={'jobs': 1}, max_builds=1),

        # zEnterprise 196 (s390x), SLES 11 SP2
        create_slave("systemz-1", properties={'jobs': 4}, max_builds=1),

        # Ubuntu 14.04 x86_64, Intel(R) Xeon(R) CPU E5-1650 0 @ 3.20GHz
        create_slave("ericwf-buildslave", properties={'jobs': 4}, max_builds=2),
        # Ubuntu 14.10 x86_64, Intel(R) Xeon(R) CPU E3-1245 V2 @ 3.40GHz
        create_slave('ericwf-buildslave2', properties={'jobs': 4}, max_builds=2),
        # OS X 10.10 x86_64, Intel Core 2 Duo @ 2.40GHz
        create_slave("ericwf-osx-slave", properties={'jobs': 2}, max_builds=1),

        # Windows Server 2008 R2, Quad 2.6GHz Intel Xeon(R) 4GB RAM
        create_slave("zturner-win2008", properties={'jobs': 4}, max_builds=1),
        # Windows Server 2008 R2, Quad 2.6GHz Intel Xeon(R) 8GB RAM
        create_slave("sanitizer-windows", properties={'jobs': 4}, max_builds=1),
        # Windows Server 2008 R2, Quad 2.6GHz Intel Xeon(R) 8GB RAM
        create_slave("windows-gcebot1", properties={'jobs': 8}, max_builds=1),

        # Ubuntu x86-64, 51GiB System memory Intel(R) Xeon(R) CPU @ 2.60GHz
        create_slave("lldb-build1-ubuntu-1404", properties={'jobs': 16, 'loadaverage':
32},
            max_builds=1),
        # Darwin 13.4.0, x86_64
        create_slave("lldb-x86_64-darwin-13.4", properties={'jobs': 16, 'loadaverage':32}, max_builds=1),
        # Defunct.
        # Intel(R) Pentium(R) CPU G620 @ 2.60GHz, Ubuntu i686
        #create_slave("botether", properties={'jobs': 2}, max_builds=1),

        # Intel(R) Core(TM)2 CPU 6420  @ 2.13GHz, Ubuntu Oneiric x86_64
        #create_slave("arxan_davinci", properties={'jobs': 4}, max_builds=1),

        # Intel(R) Core(TM)2 CPU 6420  @ 2.13GHz, Ubuntu Oneiric x86_64
        #create_slave("arxan_raphael", properties={'jobs': 4}, max_builds=1),

        # 2005 PowerPC Mac Mini, Mac OS X 10.5
        #create_slave("arxan_bellini", properties={'jobs': 2}, max_builds=1),

        # Intel(R) Core i7 920 @ 2.8GHz, 6 GB RAM, Windows 7 x64, Mingw64
        #create_slave("sschiffli1", properties={'jobs': 4}, max_builds=1),

        # Debian Testing x86-64, Intel Core i5-3570K (ivybridge) CPU @ 3.40GHz
        #create_slave("obbligato-ellington", properties={'jobs': 2}, max_builds=1),

#        # GCC Compile Farm Slaves, see http://gcc.gnu.org/wiki/CompileFarm

#        # gcc10  2TB   2x12x1.5 GHz AMD Opteron Magny-Cours / 64 GB RAM / Supermicro AS-1022G-BTF / Debian x86-64
#        create_slave("gcc10", properties={'jobs' : 12}, max_builds=1),
#        # gcc11  580G  2x 2x2.0 GHz AMD Opteron 2212 / 4GB RAM / Dell SC1345 / Debian x86-64
#        create_slave("gcc11", properties={'jobs' : 2}, max_builds=1),
#        # gcc12  580G  2x 2x2.0 GHz AMD Opteron 2212 / 4GB RAM / Dell SC1345 / Debian x86-64
#        create_slave("gcc12", properties={'jobs' : 2}, max_builds=1),
#        # gcc13  580G  2x2x2.0 GHz AMD Opteron 2212 / 4GB RAM / Dell SC1345 / Debian x86-64
#        create_slave("gcc13", properties={'jobs' : 2}, max_builds=1),
#        # gcc14  750G  2x4x3.0 GHz Intel Xeon X5450 / 16GB RAM / Dell Poweredge 1950 / Debian x86-64
#        create_slave("gcc14", properties={'jobs' : 4}, max_builds=1),
#        # gcc15  160G  1x2x2.8 GHz Intel Xeon 2.8 (Paxville DP) / 1 GB RAM / Dell SC1425 / Debian x86-64
#        create_slave("gcc15", properties={'jobs' : 1}, max_builds=1),
#        # gcc16  580G  2x4x2.2 GHz AMD Opteron 8354 (Barcelona B3) / 16 GB RAM / Debian x86-64
#        create_slave("gcc16", properties={'jobs' : 4}, max_builds=1),
#        # gcc17  580G  2x4x2.2 GHz AMD Opteron 8354 (Barcelona B3) / 16 GB RAM / Debian x86-64
#        create_slave("gcc17", properties={'jobs' : 4}, max_builds=1),
#        # gcc20   1TB  2x6x2.93 GHz Intel Dual Xeon X5670 2.93 GHz 12 cores 24 threads / 24 GB RAM / Debian amd64
#        create_slave("gcc20", properties={'jobs' : 6}, max_builds=1),
#        # gcc30        17G     0.4  GHz Alpha EV56 / 2GB RAM / AlphaServer 1200 5/400 => offline, to relocate
#        create_slave("gcc30", properties={'jobs' : 1}, max_builds=1),
#        # gcc31        51G   2x0.4  GHz TI UltraSparc II (BlackBird) / 2 GB RAM / Sun Enterprise 250 => offline, to relocate
#        create_slave("gcc31", properties={'jobs' : 1}, max_builds=1),
#        # gcc33 19033  1TB     0.8  GHz Freescale i.MX515 / 512 MB RAM / Efika MX Client Dev Board / Ubuntu armv7l
#        create_slave("gcc33", properties={'jobs' : 1}, max_builds=1),
#        # gcc34 19034  1TB     0.8  GHz Freescale i.MX515 / 512 MB RAM / Efika MX Client Dev Board / Ubuntu armv7l
#        create_slave("gcc34", properties={'jobs' : 1}, max_builds=1),
#        # gcc35 19035  1TB     0.8  GHz Freescale i.MX515 (ARM Cortex-A8) / 512 MB RAM / Efika MX Client Dev Board / Debian armel
#        create_slave("gcc35", properties={'jobs' : 1}, max_builds=1),
#        # gcc36 19036  1TB     0.8  GHz Freescale i.MX515 (ARM Cortex-A8) / 512 MB RAM / Efika MX Client Dev Board / Debian armel (?)
#        create_slave("gcc36", properties={'jobs' : 1}, max_builds=1),
#        # gcc37 19037  1TB     0.8  GHz Freescale i.MX515 / 512 MB RAM / Efika MX Client Dev Board / Ubuntu armv7l
#        create_slave("gcc37", properties={'jobs' : 1}, max_builds=1),
#        # gcc38   1TB      3.2  GHz IBM Cell BE / 256 MB RAM / Sony Playstation 3 / Debian powerpc
#        create_slave("gcc38", properties={'jobs' : 1}, max_builds=1),
#        # gcc40  160G      1.8  GHz IBM PowerPC 970 (G5) / 512 MB RAM / Apple PowerMac G5 / Debian powerpc
#        create_slave("gcc40", properties={'jobs' : 1}, max_builds=1),
#        # gcc42  9092 160G     0.8  GHz ICT Loongson 2F / 512 MB RAM / Lemote Fuloong 6004 Linux mini PC / Debian mipsel
#        create_slave("gcc42", properties={'jobs' : 1}, max_builds=1),
#        # gcc43  9093  60G     1.4  GHz Powerpc G4 7447A / 1GB RAM / Apple Mac Mini
#        create_slave("gcc43", properties={'jobs' : 1}, max_builds=1),
#        # gcc45 19045  1TB   4x3.0  GHz AMD Athlon II X4 640 / 4 GB RAM / Debian i386
#        create_slave("gcc45", properties={'jobs' : 2}, max_builds=1),
#        # gcc46  250G      1.66 GHz Intel Atom D510 2 cores 4 threads / 4 GB RAM / Debian amd64
#        create_slave("gcc46", properties={'jobs' : 2}, max_builds=1),
#        # gcc47  250G      1.66 GHz Intel Atom D510 2 cores 4 threads / 4 GB RAM / Debian amd64
#        create_slave("gcc47", properties={'jobs' : 2}, max_builds=1),
#        # gcc49  2TB   4x0.9  GHz ICT Loongson 3A / 2 GB RAM / prototype board / Debian mipsel
#        create_slave("gcc49", properties={'jobs' : 2}, max_builds=1),
#        # gcc50  9080 250G     0.6  GHz ARM XScale-80219 / 512 MB RAM / Thecus N2100 NAS
#        create_slave("gcc50", properties={'jobs' : 1}, max_builds=1),
#        # gcc51  9081  60G     0.8  GHz ICT Loongson 2F /   1 GB RAM / Lemote YeeLoong 8089 notebook / Debian mipsel
#        create_slave("gcc51", properties={'jobs' : 1}, max_builds=1),
#        # gcc52  9082  1TB     0.8  GHz ICT Loongson 2F / 512 MB RAM / Gdium Liberty 1000 notebook / Mandriva 2009.1 mipsel
#        create_slave("gcc52", properties={'jobs' : 1}, max_builds=1),
#        # gcc53  9083  80G   2x1.25 GHz PowerPC 7455 G4  / 1.5 GB RAM / PowerMac G4 dual processor
#        create_slave("gcc53", properties={'jobs' : 1}, max_builds=1),
#        # gcc54   36G      0.5  GHz TI UltraSparc IIe (Hummingbird) / 1.5 GB RAM / Sun Netra T1 200 / Debian sparc
#        create_slave("gcc54", properties={'jobs' : 1}, max_builds=1),
#        # gcc55  9085 250G     1.2  GHz Marvell Kirkwood 88F6281 (Feroceon) / 512 MB RAM / Marvell SheevaPlug / Ubuntu armel
#        create_slave("gcc55", properties={'jobs' : 1}, max_builds=1),
#        # gcc56  9086 320G     1.2  GHz Marvell Kirkwood 88F6281 (Feroceon) / 512 MB RAM / Marvell SheevaPlug / Ubuntu armel
#        create_slave("gcc56", properties={'jobs' : 1}, max_builds=1),
#        # gcc57  9087 320G     1.2  GHz Marvell Kirkwood 88F6281 (Feroceon) / 512 MB RAM / Marvell SheevaPlug / Ubuntu armel
#        create_slave("gcc57", properties={'jobs' : 1}, max_builds=1),
#        # gcc60  9200  72G   2x1.3  GHz Intel Itanium 2 (Madison) / 6 GB RAM / HP zx6000 / Debian ia64
#        create_slave("gcc60", properties={'jobs' : 1}, max_builds=1),
#        # gcc61  9201  36G   2x0.55 GHz HP PA-8600 / 3.5 GB RAM / HP 9000/785/J6000 / Debian hppa
#        create_slave("gcc61", properties={'jobs' : 1}, max_builds=1),
#        # gcc62  9202  36G   6x0.4  GHz TI UltraSparc II (BlackBird) / 5 GB RAM / Sun Enterprise 4500 / Debian sparc
#        create_slave("gcc62", properties={'jobs' : 3}, max_builds=1),
#        # gcc63  9203  72G   8x4x1  GHz Sun UltraSparc T1 (Niagara) / 8 GB RAM / Sun Fire T1000 / Debian sparc
#        create_slave("gcc63", properties={'jobs' : 16}, max_builds=1),
#        # gcc64  9204  72G       1  GHz Sun UltraSPARC-IIIi / 1 GB RAM / Sun V210 / OpenBSD 4.6 sparc64
#        create_slave("gcc64", properties={'jobs' : 1}, max_builds=1),
#        # gcc66  9206  72G   2x1.3  GHz Intel Itanium 2 (Madison) / 12 GB RAM / HP rx2600 / Debian ia64
#        create_slave("gcc66", properties={'jobs' : 1}, max_builds=1),
#        # gcc70       160G   2x3.2 GHz  Intel Xeon 3.2E (Irwindale) / 3 GB RAM / Dell Poweredge SC1425 / NetBSD amd64
#        create_slave("gcc70", properties={'jobs' : 1}, max_builds=1),
#        # gcc76       2TB    4x2x3.4 GHz Core i7-2600 / 16 GB RAM / 2TB
#        create_slave("gcc76", properties={'jobs' : 4}, max_builds=1),
#        # gcc100       1TB   2x2.6 GHz  AMD Opteron 252 / 1GB RAM running Debian x86_64
#        create_slave("gcc100", properties={'jobs' : 1}, max_builds=1),
#        # gcc101       1TB   2x2.6 GHz  AMD Opteron 252 / 1GB RAM running FreeBSD 8 x86_64
#        create_slave("gcc101", properties={'jobs' : 1}, max_builds=1),
#        # gcc110       2TB    4x16x3.55 GHz IBM POWER7 / 64 GB RAM / IBM Power 730 Express server / Fedora ppc64
#        create_slave("gcc110", properties={'jobs' : 2}, max_builds=1),
#        # gcc200 8010  80G   4x0.4 GHz  TI UltraSparc II (BlackBird) / 4 GB RAM / Sun E250 / Gentoo sparc64
#        create_slave("gcc200", properties={'jobs' : 2}, max_builds=1),
#        # gcc201 8011  80G   4x0.4 GHz  TI UltraSparc II (BlackBird) / 4 GB RAM / Sun E250 / Gentoo sparc64
#        create_slave("gcc201", properties={'jobs' : 2}, max_builds=1),

        # Pentium Dual CPU T3400 @ 2.1GHz
        #create_slave("dumitrescu1", properties={'jobs' : 2}, max_builds=1),
        # Quad Core x86_64, Solaris / AurorAUX
        #create_slave("evocallaghan", properties={'jobs' : 4}, max_builds=1),
        # Adobe Contributed VM
        # Win XP SP2, Intel Core2 Duo 2.99GHz -E6850, 2.93 GB
        #create_slave("adobe1", properties={'jobs' : 2}, max_builds=1),
        # PowerPC Linux machine. 900MHz G3 processor with 256MB of RAM.
        #create_slave("nick1", properties={'jobs' : 1}, max_builds=1),
        # Linux, Beagleboard, Cortex A8, 256MB RAM.
        #create_slave("nick2", properties={'jobs' : 1}, max_builds=1),
        # Linux, NVidia Tegra 250, Dual-core Cortex A9, 1GB RAM
        #create_slave("nick3", properties={'jobs' : 2}, max_builds=1),
        # Core 2 Duo running Ubuntu.
        #create_slave("dunbar1", properties={'jobs' : 2}, max_builds=1),
        # Athlon 1.2 XP SP 3.
        #create_slave("dunbar-win32", properties={'jobs' : 1}, max_builds=1),
        # Dual Quad Core Mc Pro (Nehalem) running SnowLeopard.
        #create_slave("dunbar-darwin10", properties={'jobs' : 4}, max_builds=2),
        # Dual Core Pentium M, XP SP 3.
        #create_slave("dunbar-win32-2", properties={'jobs' : 2}, max_builds=1),
        #create_slave("osu1", properties={'jobs' : 4}, max_builds=1),
        #create_slave("osu2", properties={'jobs' : 4}, max_builds=2),
        #create_slave("andrew1"),
        #create_slave("danmbp1"),
        # FreeBSD zero.sajd.net 9.0-CURRENT i386
        #create_slave("freebsd1", properties={'jobs' : 1}, max_builds=1),
        # Debian, P4 2.8GHz, 1GB mem
        #create_slave("balint1", properties={'jobs' : 1}, max_builds=1),

        # create_slave("lab-mini-01", properties={'jobs': 2}, max_builds=1),
        # create_slave("lab-mini-02", properties={'jobs': 2}, max_builds=1),
        # create_slave("lab-mini-03", properties={'jobs': 2}, max_builds=1),
        # create_slave("lab-mini-04", properties={'jobs': 2}, max_builds=1),
        # create_slave("xserve1", properties={'jobs': 4}, max_builds=1),
        # create_slave("xserve2", properties={'jobs': 4}, max_builds=1),
        # create_slave("xserve3", properties={'jobs': 4}, max_builds=1),
        # create_slave("xserve4", properties={'jobs': 4}, max_builds=1),
        # create_slave("xserve5", properties={'jobs': 4}, max_builds=1),
        ]
