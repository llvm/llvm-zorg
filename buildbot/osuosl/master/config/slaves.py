import buildbot
import buildbot.buildslave
import os

import config

def create_slave(name, *args, **kwargs):
    password = config.options.get('Slave Passwords', name)
    return buildbot.buildslave.BuildSlave(name, password=password, *args, **kwargs)

def get_build_slaves():
    return [
        # FreeBSD zero.sajd.net 9.0-CURRENT i386
        create_slave("freebsd1", properties={'jobs' : 1}, max_builds=1),

        # CPU Marvell Kirkwood 88F6281 ARM Based armv5tejl running at 1.2Ghz
        # Memory 512MB SDRAM
        # Power 2.3w idle no attached devices, 7.0w running at 100% CPU utilization
        # Storage 400Gb USB drive.
        # OS Ubuntu Jaunty
        create_slave("ranby1"),

        # Quad Core Mac Pro running Leopard.
        create_slave("kistanova1", properties={'jobs' : 1}, max_builds=4),

        # Win XP SP3.
        create_slave("kistanova2", properties={'jobs' : 1}, max_builds=1),

        # Windows 7 Ultimate.
        create_slave("kistanova3", properties={'jobs' : 1}, max_builds=1),

        # CentOS 5.4.
        create_slave("kistanova4", properties={'jobs' : 1}, max_builds=2),

        # Win XP SP3.
        create_slave("kistanova5", properties={'jobs' : 1}, max_builds=1),

        # Ubuntu pandaboard cortex-a9
        create_slave("kistanova6", properties={'jobs' : 2}, max_builds=1),

        # FreeBSD 8.2 X86_64
        create_slave("kistanova7", properties={'jobs' : 2}, max_builds=1),

        # Windows 7 Ultimate
        create_slave("kistanova8", properties={'jobs' : 1}, max_builds=1),

        # GCC Compile Farm Slaves, see http://gcc.gnu.org/wiki/CompileFarm

        # gcc10  2TB   2x12x1.5 GHz AMD Opteron Magny-Cours / 64 GB RAM / Supermicro AS-1022G-BTF / Debian x86-64
        create_slave("gcc10", properties={'jobs' : 12}, max_builds=1),
        # gcc11  580G  2x 2x2.0 GHz AMD Opteron 2212 / 4GB RAM / Dell SC1345 / Debian x86-64
        create_slave("gcc11", properties={'jobs' : 2}, max_builds=1),
        # gcc12  580G  2x 2x2.0 GHz AMD Opteron 2212 / 4GB RAM / Dell SC1345 / Debian x86-64
        create_slave("gcc12", properties={'jobs' : 2}, max_builds=1),
        # gcc13  580G  2x2x2.0 GHz AMD Opteron 2212 / 4GB RAM / Dell SC1345 / Debian x86-64
        create_slave("gcc13", properties={'jobs' : 2}, max_builds=1),
        # gcc14  750G  2x4x3.0 GHz Intel Xeon X5450 / 16GB RAM / Dell Poweredge 1950 / Debian x86-64
        create_slave("gcc14", properties={'jobs' : 4}, max_builds=1),
        # gcc15  160G  1x2x2.8 GHz Intel Xeon 2.8 (Paxville DP) / 1 GB RAM / Dell SC1425 / Debian x86-64
        create_slave("gcc15", properties={'jobs' : 1}, max_builds=1),
        # gcc16  580G  2x4x2.2 GHz AMD Opteron 8354 (Barcelona B3) / 16 GB RAM / Debian x86-64
        create_slave("gcc16", properties={'jobs' : 4}, max_builds=1),
        # gcc17  580G  2x4x2.2 GHz AMD Opteron 8354 (Barcelona B3) / 16 GB RAM / Debian x86-64
        create_slave("gcc17", properties={'jobs' : 4}, max_builds=1),
        # gcc20   1TB  2x6x2.93 GHz Intel Dual Xeon X5670 2.93 GHz 12 cores 24 threads / 24 GB RAM / Debian amd64
        create_slave("gcc20", properties={'jobs' : 12}, max_builds=1),
        # gcc30        17G     0.4  GHz Alpha EV56 / 2GB RAM / AlphaServer 1200 5/400 => offline, to relocate
        create_slave("gcc30", properties={'jobs' : 1}, max_builds=1),
        # gcc31        51G   2x0.4  GHz TI UltraSparc II (BlackBird) / 2 GB RAM / Sun Enterprise 250 => offline, to relocate
        create_slave("gcc31", properties={'jobs' : 1}, max_builds=1),
        # gcc33 19033  1TB     0.8  GHz Freescale i.MX515 / 512 MB RAM / Efika MX Client Dev Board / Ubuntu armv7l
        create_slave("gcc33", properties={'jobs' : 1}, max_builds=1),
        # gcc34 19034  1TB     0.8  GHz Freescale i.MX515 / 512 MB RAM / Efika MX Client Dev Board / Ubuntu armv7l
        create_slave("gcc34", properties={'jobs' : 1}, max_builds=1),
        # gcc35 19035  1TB     0.8  GHz Freescale i.MX515 (ARM Cortex-A8) / 512 MB RAM / Efika MX Client Dev Board / Debian armel
        create_slave("gcc35", properties={'jobs' : 1}, max_builds=1),
        # gcc36 19036  1TB     0.8  GHz Freescale i.MX515 (ARM Cortex-A8) / 512 MB RAM / Efika MX Client Dev Board / Debian armel (?)
        create_slave("gcc36", properties={'jobs' : 1}, max_builds=1),
        # gcc37 19037  1TB     0.8  GHz Freescale i.MX515 / 512 MB RAM / Efika MX Client Dev Board / Ubuntu armv7l
        create_slave("gcc37", properties={'jobs' : 1}, max_builds=1),
        # gcc38   1TB      3.2  GHz IBM Cell BE / 256 MB RAM / Sony Playstation 3 / Debian powerpc
        create_slave("gcc38", properties={'jobs' : 1}, max_builds=1),
        # gcc40  160G      1.8  GHz IBM PowerPC 970 (G5) / 512 MB RAM / Apple PowerMac G5 / Debian powerpc
        create_slave("gcc40", properties={'jobs' : 1}, max_builds=1),
        # gcc42  9092 160G     0.8  GHz ICT Loongson 2F / 512 MB RAM / Lemote Fuloong 6004 Linux mini PC / Debian mipsel
        create_slave("gcc42", properties={'jobs' : 1}, max_builds=1),
        # gcc43  9093  60G     1.4  GHz Powerpc G4 7447A / 1GB RAM / Apple Mac Mini
        create_slave("gcc43", properties={'jobs' : 1}, max_builds=1),
        # gcc45 19045  1TB   4x3.0  GHz AMD Athlon II X4 640 / 4 GB RAM / Debian i386
        create_slave("gcc45", properties={'jobs' : 2}, max_builds=1),
        # gcc46  250G      1.66 GHz Intel Atom D510 2 cores 4 threads / 4 GB RAM / Debian amd64
        create_slave("gcc46", properties={'jobs' : 2}, max_builds=1),
        # gcc47  250G      1.66 GHz Intel Atom D510 2 cores 4 threads / 4 GB RAM / Debian amd64
        create_slave("gcc47", properties={'jobs' : 2}, max_builds=1),
        # gcc50  9080 250G     0.6  GHz ARM XScale-80219 / 512 MB RAM / Thecus N2100 NAS
        create_slave("gcc50", properties={'jobs' : 1}, max_builds=1),
        # gcc51  9081  60G     0.8  GHz ICT Loongson 2F /   1 GB RAM / Lemote YeeLoong 8089 notebook / Debian mipsel
        create_slave("gcc51", properties={'jobs' : 1}, max_builds=1),
        # gcc52  9082  1TB     0.8  GHz ICT Loongson 2F / 512 MB RAM / Gdium Liberty 1000 notebook / Mandriva 2009.1 mipsel
        create_slave("gcc52", properties={'jobs' : 1}, max_builds=1),
        # gcc53  9083  80G   2x1.25 GHz PowerPC 7455 G4  / 1.5 GB RAM / PowerMac G4 dual processor
        create_slave("gcc53", properties={'jobs' : 1}, max_builds=1),
        # gcc54   36G      0.5  GHz TI UltraSparc IIe (Hummingbird) / 1.5 GB RAM / Sun Netra T1 200 / Debian sparc
        create_slave("gcc54", properties={'jobs' : 1}, max_builds=1),
        # gcc55  9085 250G     1.2  GHz Marvell Kirkwood 88F6281 (Feroceon) / 512 MB RAM / Marvell SheevaPlug / Ubuntu armel
        create_slave("gcc55", properties={'jobs' : 1}, max_builds=1),
        # gcc56  9086 320G     1.2  GHz Marvell Kirkwood 88F6281 (Feroceon) / 512 MB RAM / Marvell SheevaPlug / Ubuntu armel
        create_slave("gcc56", properties={'jobs' : 1}, max_builds=1),
        # gcc57  9087 320G     1.2  GHz Marvell Kirkwood 88F6281 (Feroceon) / 512 MB RAM / Marvell SheevaPlug / Ubuntu armel
        create_slave("gcc57", properties={'jobs' : 1}, max_builds=1),
        # gcc60  9200  72G   2x1.3  GHz Intel Itanium 2 (Madison) / 6 GB RAM / HP zx6000 / Debian ia64
        create_slave("gcc60", properties={'jobs' : 1}, max_builds=1),
        # gcc61  9201  36G   2x0.55 GHz HP PA-8600 / 3.5 GB RAM / HP 9000/785/J6000 / Debian hppa
        create_slave("gcc61", properties={'jobs' : 1}, max_builds=1),
        # gcc62  9202  36G   6x0.4  GHz TI UltraSparc II (BlackBird) / 5 GB RAM / Sun Enterprise 4500 / Debian sparc
        create_slave("gcc62", properties={'jobs' : 3}, max_builds=1),
        # gcc63  9203  72G   8x4x1  GHz Sun UltraSparc T1 (Niagara) / 8 GB RAM / Sun Fire T1000 / Debian sparc
        create_slave("gcc63", properties={'jobs' : 16}, max_builds=1),
        # gcc64  9204  72G       1  GHz Sun UltraSPARC-IIIi / 1 GB RAM / Sun V210 / OpenBSD 4.6 sparc64
        create_slave("gcc64", properties={'jobs' : 1}, max_builds=1),
        # gcc70       160G   2x3.2 GHz  Intel Xeon 3.2E (Irwindale) / 3 GB RAM / Dell Poweredge SC1425 / NetBSD amd64
        create_slave("gcc70", properties={'jobs' : 1}, max_builds=1),
        # gcc100       1TB   2x2.6 GHz  AMD Opteron 252 / 1GB RAM running Debian x86_64
        create_slave("gcc100", properties={'jobs' : 1}, max_builds=1),
        # gcc101       1TB   2x2.6 GHz  AMD Opteron 252 / 1GB RAM running FreeBSD 8 x86_64
        create_slave("gcc101", properties={'jobs' : 1}, max_builds=1),
        # gcc200 8010  80G   4x0.4 GHz  TI UltraSparc II (BlackBird) / 4 GB RAM / Sun E250 / Gentoo sparc64
        create_slave("gcc200", properties={'jobs' : 2}, max_builds=1),
        # gcc201 8011  80G   4x0.4 GHz  TI UltraSparc II (BlackBird) / 4 GB RAM / Sun E250 / Gentoo sparc64
        create_slave("gcc201", properties={'jobs' : 2}, max_builds=1),

        # Debian, P4 2.8GHz, 1GB mem
        create_slave("balint1", properties={'jobs' : 1}, max_builds=1),

        # AMD Athlon(tm) 64 X2 Dual Core 3800+, Ubuntu x86_64
        create_slave("grosser1", properties={'jobs': 2}, max_builds=1),

        # Intel(R) Core(TM)2 CPU 6420  @ 2.13GHz, Ubuntu Oneiric x86_64
        create_slave("arxan_davinci", properties={'jobs': 4}, max_builds=1),

        # 2005 PowerPC Mac Mini, Mac OS X 10.5
        create_slave("arxan_bellini", properties={'jobs': 2}, max_builds=1),

        # Defunct.
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
        # Debian x86_64, 2 x 6-core Opteron 2.6 GHz
        #create_slave("osu7", properties={'jobs' : 6}, max_builds=4),
        #create_slave("osu8", properties={'jobs' : 6}, max_builds=4),
        #create_slave("andrew1"),
        #create_slave("danmbp1"),
        ]
