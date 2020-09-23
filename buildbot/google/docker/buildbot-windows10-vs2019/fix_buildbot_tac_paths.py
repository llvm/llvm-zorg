#!/usr/bin/env python3
# Replace backward slashes in the paths in a "buildbot.tac" file

import argparse
import re
import shutil


def fix_slashes(buildbot_tac_path : str):
    shutil.copy(buildbot_tac_path, buildbot_tac_path + ".bak")
    result = []
    with open(buildbot_tac_path) as buildbot_tac_file:
        buildbot_tac = buildbot_tac_file.readlines()
        for line in buildbot_tac:
            if line.lstrip().startswith('basedir'):
                line = line.replace(r'\\','/')
            result.append(line)
    with open(buildbot_tac_path, 'w') as buildbot_tac_file:
        buildbot_tac_file.writelines(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('buildbot_tac_path', help="path of 'buildbot.tac' file")
    args = parser.parse_args()
    fix_slashes(args.buildbot_tac_path)
