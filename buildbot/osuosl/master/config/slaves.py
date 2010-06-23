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

        # Quad Core x86_64, Solaris / AurorAUX
        create_slave("evocallaghan", properties={'jobs' : 4}, max_builds=1),

        # Adobe Contributed VM
        # Win XP SP2, Intel Core2 Duo 2.99GHz -E6850, 2.93 GB
        create_slave("adobe1", properties={'jobs' : 2}, max_builds=1),

        # GCC Farm Slaves, for DragonEgg
        create_slave("baldrick11", properties={'jobs' : 4}, max_builds=1),
        create_slave("baldrick12", properties={'jobs' : 4}, max_builds=1),
        create_slave("baldrick13", properties={'jobs' : 4}, max_builds=1),
        create_slave("baldrick14", properties={'jobs' : 8}, max_builds=1),
        create_slave("baldrick15", properties={'jobs' : 2}, max_builds=1),
        create_slave("baldrick16", properties={'jobs' : 8}, max_builds=1),
        create_slave("baldrick17", properties={'jobs' : 8}, max_builds=1),

        # Debian x86_64, 2 x 6-core Opteron 2.6 GHz
        create_slave("osu7", properties={'jobs' : 6}, max_builds=4),
        create_slave("osu8", properties={'jobs' : 6}, max_builds=4),

        # Debian, P4 2.8GHz, 1GB mem
        create_slave("balint1", properties={'jobs' : 1}, max_builds=1),

        # Defunct.
        #create_slave("osu2", properties={'jobs' : 4}, max_builds=2),
        #create_slave("andrew1"),
        #create_slave("danmbp1"),
        ]
