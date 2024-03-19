'''
Get packaged artifact from an s3 server.

i.e.
ARTIFACT={BUCKET}/clangci/subdir/buz.tar.gz
'''
import os
from pathlib import Path
from pipes import quote

import tasktool.utils as utils

BUCKET = os.environ.get("S3_BUCKET")

def verify(config):
    if config.get('url') is None:
        raise Exception("No 'url' specified")


def resolve_latest(config):
    pass


def get_artifact(config, dest_dir):
    url = config['url']

    utils.check_call(['mkdir', '-p', dest_dir])

    download_cmd = ["aws", "s3", "cp", f"{BUCKET}/clangci/{url}", 'artifact']
    utils.check_call(download_cmd, cwd=dest_dir)

    local_name = 'artifact'

    # Determine if the artifact is actually a pointer to another file stored.
    # If so, download the file at the pointer
    if Path(dest_dir, local_name).stat().st_size < 1000:
        with Path(dest_dir, local_name).open() as pointer:
            package = pointer.read().strip()
            download_cmd = ["aws", "s3", "cp", f"{BUCKET}/clangci/{package}", local_name]
            utils.check_call(download_cmd, cwd=dest_dir)

    untar_cmd = ["tar", "zxf", local_name]
    utils.check_call(untar_cmd, cwd=dest_dir)


def repro_arg(config, dest_dir):
    return '-a %s=%s' % (dest_dir, quote(config['url']))

