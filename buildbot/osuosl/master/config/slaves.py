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
        create_slave("freebsd1", properties={'jobs' : 1}), 

        # A PowerPC Linux machine. 900MHz G3 processor with 256MB of RAM.
        create_slave("nick1"), 

        # Core 2 Due running Ubuntu.
        create_slave("dunbar1", properties={'jobs' : 2}, max_builds=1),

        # Athlon 1.2 XP SP 3.
        create_slave("dunbar-win32", properties={'jobs' : 1}, max_builds=1),

        # Dual Quad Core Mc Pro (Nehalem) running SnowLeopard.
        create_slave("dunbar-darwin10", properties={'jobs' : 4}, max_builds=4),

        # Dual Core Pentium M, XP SP 3.
        create_slave("dunbar-win32-2", properties={'jobs' : 2}, max_builds=1),

        # CPU Marvell Kirkwood 88F6281 ARM Based armv5tejl running at 1.2Ghz
        # Memory 512MB SDRAM
        # Power 2.3w idle no attached devices, 7.0w running at 100% CPU utilization
        # Storage 400Gb USB drive.
        # OS Ubuntu Jaunty
        create_slave("ranby1"),

        # Quad Core Mac Pro running Leopard.
        create_slave("kistanova1", properties={'jobs' : 1}, max_builds=1),

        # Quad Core x86_64, Solaris / AurorAUX
        create_slave("evocallaghan", properties={'jobs' : 4}, max_builds=1),

        # Adobe
        create_slave("adobe1", properties={'jobs' : 1}, max_builds=1),

        # Defunct.
        #create_slave("osu2", properties={'jobs' : 4}, max_builds=2), 
        #create_slave("andrew1"),
        #create_slave("danmbp1"),
        ]
