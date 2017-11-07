from pipes import quote
import sys
import tasktool.utils as utils
import logging


def verify(config):
    if config.get('url') is None:
        raise Exception("No 'url' specified")


def resolve_latest(config):
    pass


def get_artifact(config, dest_dir):
    url = config['url']
    untar_cmd = "cd %s ; curl -s %s | tar -x" % (quote(dest_dir), quote(url))
    utils.check_call(['mkdir', '-p', dest_dir])
    utils.check_call(untar_cmd, shell=True)


def repro_arg(config, dest_dir):
    return '-a %s=%s' % (dest_dir, quote(config['url']))
