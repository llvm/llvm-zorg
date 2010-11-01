import buildbot
import os

import config

def create_slave(name, *args, **kwargs):
    password = config.options.get('Slave Passwords', name)
    return buildbot.buildslave.BuildSlave(name, password=password, *args, **kwargs)

def get_build_slaves():
    return [
        create_slave("osu1", properties={'jobs' : 4}, max_builds=1),

        # FreeBSD zero.sajd.net 9.0-CURRENT i386
        create_slave("freebsd1", properties={'jobs' : 1}, max_builds=1),

        # PowerPC Linux machine. 900MHz G3 processor with 256MB of RAM.
        create_slave("nick1", properties={'jobs' : 1}, max_builds=1),

        # Linux, Beagleboard, Cortex A8, 256MB RAM.
        create_slave("nick2", properties={'jobs' : 1}, max_builds=1),

        # Linux, NVidia Tegra 250, Dual-core Cortex A9, 1GB RAM
        create_slave("nick3", properties={'jobs' : 2}, max_builds=1),

        # Core 2 Duo running Ubuntu.
        create_slave("dunbar1", properties={'jobs' : 2}, max_builds=1),

        # Athlon 1.2 XP SP 3.
        create_slave("dunbar-win32", properties={'jobs' : 1}, max_builds=1),

        # Dual Quad Core Mc Pro (Nehalem) running SnowLeopard.
        create_slave("dunbar-darwin10", properties={'jobs' : 4}, max_builds=2),

        # Dual Core Pentium M, XP SP 3.
        create_slave("dunbar-win32-2", properties={'jobs' : 2}, max_builds=1),

        # CPU Marvell Kirkwood 88F6281 ARM Based armv5tejl running at 1.2Ghz
        # Memory 512MB SDRAM
        # Power 2.3w idle no attached devices, 7.0w running at 100% CPU utilization
        # Storage 400Gb USB drive.
        # OS Ubuntu Jaunty
        create_slave("ranby1"),

        # Quad Core Mac Pro running Leopard.
        create_slave("kistanova1", properties={'jobs' : 1}, max_builds=3),

        # Win XP SP3.
        create_slave("kistanova2", properties={'jobs' : 1}, max_builds=1),

        # Windows 7 Ultimate.
        create_slave("kistanova3", properties={'jobs' : 1}, max_builds=1),

        # CentOS 5.4.
        create_slave("kistanova4", properties={'jobs' : 1}, max_builds=2),

        # Quad Core x86_64, Solaris / AurorAUX
        create_slave("evocallaghan", properties={'jobs' : 4}, max_builds=1),

        # Adobe Contributed VM
        # Win XP SP2, Intel Core2 Duo 2.99GHz -E6850, 2.93 GB
        create_slave("adobe1", properties={'jobs' : 2}, max_builds=1),

        # GCC Farm Slaves

        # 2TB   2x12x1.5 GHz 2x Opteron Magny-Cours / 64 GB RAM / Supermicro AS-1022G-BTF
        create_slave("gcc10", properties={'jobs' : 12}, max_builds=1), 
        # 580G  2x 2x2.0 GHz Opteron 2212 / 4GB RAM / Dell SC1345
        create_slave("gcc11", properties={'jobs' : 2}, max_builds=1), 
        # 580G  2x 2x2.0 GHz Opteron 2212 / 4GB RAM / Dell SC1345
        create_slave("gcc12", properties={'jobs' : 2}, max_builds=1), 
        # 580G  2x2x2.0 GHz Opteron 2212 / 4GB RAM / Dell SC1345
        create_slave("gcc13", properties={'jobs' : 2}, max_builds=1), 
        # 750G  2x4x3.0 GHz Xeon X5450 / 16GB RAM / Dell Poweredge 1950
        create_slave("gcc14", properties={'jobs' : 4}, max_builds=1), 
        # 160G  1x2x2.8 GHz Xeon dual core "paxville" / 1 GB RAM / Dell SC1425
        create_slave("gcc15", properties={'jobs' : 1}, max_builds=1), 
        # 580G  2x4x2.2 GHz Opteron 8354 "Barcelona B3" / 16 GB RAM
        create_slave("gcc16", properties={'jobs' : 4}, max_builds=1), 
        # 580G  2x4x2.2 GHz Opteron 8354 "Barcelona B3" / 16 GB RAM
        create_slave("gcc17", properties={'jobs' : 4}, max_builds=1), 
        # 1TB     0.8  GHz Freescale i.MX515 (ARM Cortex-A8) / 512 MB RAM / Efika MX Client Dev Board 
        create_slave("gcc35", properties={'jobs' : 1}, max_builds=1), 
        # 1TB     3.2  GHz Sony Playstation 3 / Cell / SPE
        create_slave("gcc38", properties={'jobs' : 1}, max_builds=1), 
        # 160G     1.8  GHz PowerPC 970 G5 / 512 MB RAM / PowerMac G5
        create_slave("gcc40", properties={'jobs' : 1}, max_builds=1), 
        # 160G     0.8  GHz MIPS Loongson 2F /   1 GB RAM / Lemote Fuloong 6004 Linux mini PC
        create_slave("gcc42", properties={'jobs' : 1}, max_builds=1), 
        # 60G     1.4  GHz Powerpc G4 7447A / 1GB RAM / Apple Mac Mini
        create_slave("gcc43", properties={'jobs' : 1}, max_builds=1), 
        # 250G     0.6  GHz ARM XScale-80219 / 512 MB RAM / Thecus N2100 NAS
        create_slave("gcc50", properties={'jobs' : 1}, max_builds=1), 
        # 60G     0.8  GHz MIPS Loongson 2F /   1 GB RAM / Lemote YeeLoong 8089 notebook
        create_slave("gcc51", properties={'jobs' : 1}, max_builds=1), 
        # 1TB     0.8  GHz MIPS Loongson 2F / 512 MB RAM / Gdium Liberty 1000 notebook Mandriva 2009.1
        create_slave("gcc52", properties={'jobs' : 1}, max_builds=1), 
        # 80G   2x1.25 GHz PowerPC 7455 G4  / 1.5 GB RAM / PowerMac G4 dual processor
        create_slave("gcc53", properties={'jobs' : 1}, max_builds=1), 
        # 36G     0.5  GHz TI UltraSparc IIe (Hummingbird) / 1.5 GB RAM / Sun Netra T1 200 / Debian sparc64
        create_slave("gcc54", properties={'jobs' : 1}, max_builds=1), 
        # 250G     1.2  GHz ARM Feroceon 88FR131 (kirkwood) / 512 MB RAM / Marvell SheevaPlug
        create_slave("gcc55", properties={'jobs' : 1}, max_builds=1), 
        # 320G     1.2  GHz ARM Feroceon 88FR131 (kirkwood) / 512 MB RAM / Marvell SheevaPlug
        create_slave("gcc56", properties={'jobs' : 1}, max_builds=1), 
        # 320G     1.2  GHz ARM Feroceon 88FR131 (kirkwood) / 512 MB RAM / Marvell SheevaPlug
        create_slave("gcc57", properties={'jobs' : 1}, max_builds=1), 
        # 72G   2x1.3 GHz  Madison / 6 GB RAM / HP zx6000
        create_slave("gcc60", properties={'jobs' : 1}, max_builds=1), 
        # 36G   2x0.55 GHz PA8600 / 3.5 GB RAM / HP 9000/785/J6000
        create_slave("gcc61", properties={'jobs' : 1}, max_builds=1), 
        # 36G   6x0.4GHz   TI UltraSparc II (BlackBird) / 5 GB RAM / Sun Enterprise 4500 / Debian sparc64
        create_slave("gcc62", properties={'jobs' : 3}, max_builds=1), 
        # 72G   8x4x1GHz   UltraSparc T1 (Niagara) 1 GHz 8 core 32 threads / 8 GB RAM / Sun Fire T1000 / Debian sparc64
        create_slave("gcc63", properties={'jobs' : 16}, max_builds=1), 
        # 72G   1x1GHz     UltraSPARC-IIIi / 1 GB RAM / Sun V210 / OpenBSD 4.6 sparc64
        create_slave("gcc64", properties={'jobs' : 1}, max_builds=1), 
        # 1TB   2x2.6 GHz  Opteron 252 / 1GB RAM running FreeBSD 8 x86_64
        create_slave("gcc101", properties={'jobs' : 1}, max_builds=1), 
        # 80G   4x0.4GHz   TI UltraSparc II (BlackBird) / 4 GB RAM / Sun E250 / Gentoo sparc64
        create_slave("gcc200", properties={'jobs' : 2}, max_builds=1), 
        # 80G   4x0.4GHz   TI UltraSparc II (BlackBird) / 4 GB RAM / Sun E250 / Gentoo sparc64
        create_slave("gcc201", properties={'jobs' : 2}, max_builds=1), 

        # Debian x86_64, 2 x 6-core Opteron 2.6 GHz
        create_slave("osu7", properties={'jobs' : 6}, max_builds=4),
        create_slave("osu8", properties={'jobs' : 6}, max_builds=4),

        # Debian, P4 2.8GHz, 1GB mem
        create_slave("balint1", properties={'jobs' : 1}, max_builds=1),

        # Pentium Dual CPU T3400 @ 2.1GHz
        create_slave("dumitrescu1", properties={'jobs' : 2}, max_builds=1),

        # Defunct.
        #create_slave("osu2", properties={'jobs' : 4}, max_builds=2),
        #create_slave("andrew1"),
        #create_slave("danmbp1"),
        ]
