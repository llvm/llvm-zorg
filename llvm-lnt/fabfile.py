""" Script to control the deployment of LNT to Google Cloud Instance.


"""

import os
from os.path import expanduser

import re
from fabric.api import env, cd, task, run, put
from fabric.api import sudo
from fabric.context_managers import hide
from fabric.operations import get, local

here = os.path.dirname(os.path.realpath(__file__))

home = expanduser("~")

env.use_ssh_config = True
env.output_prefix = False

# The remote LNT venv location.
LNT_VENV = "/srv/lnt/sandbox"

# Prefix a command with this to get to the venv.
IN_VENV = "source " + LNT_VENV + "/bin/activate; "


def in_venv(command):
    """Run the command inside the LNT venv."""
    return IN_VENV + command


# The remote location of the LNT repo checkout.
LNT_PATH = "/srv/lnt/src/lnt/"
LNT_CONF_PATH = "/srv/lnt/install"


@task
def update():
    """Update the svn repo, then reinstall LNT."""
    with cd(LNT_PATH):
        with cd(LNT_PATH + "/docs/"):
            sudo('rm -rf _build')
        with cd(LNT_PATH + "/lnt/server/ui/static"):
            sudo('rm -rf docs')
            sudo('git checkout docs')

        sudo("git pull --rebase")
        run("git log -1 --pretty=%B")
        with cd(LNT_PATH + "/docs/"):
            sudo(in_venv("make"))
        sudo(IN_VENV + "python setup.py install --server")

    put(here + "/blacklist", "/tmp/blacklist")
    sudo("mv /tmp/blacklist /srv/lnt/install/blacklist")
    put(here + "/kill_zombies.py", "/tmp/kill_zombies.py")
    sudo("mv /tmp/kill_zombies.py /etc/cron.hourly/kill_zombies")
    sudo("chmod +x /etc/cron.hourly/kill_zombies")
    rotate_log()
    service_restart()


@task
def log():
    get('/srv/lnt/install/lnt.log', 'lnt.log')
    local('cat lnt.log')


@task
def new_log():
    """Show only lines since the last time the log was echoed."""
    if os.path.exists("lnt.log"):
        lines = {line for line in open("lnt.log", 'r').readlines()}
    else:
        lines = set()
    with hide('warnings'):
        get('/srv/lnt/install/lnt.log', 'lnt.log', )
    new_lines = {line for line in open("lnt.log", 'r').readlines()}
    for l in new_lines - lines:
        print ' '.join(l.split()[2:]),


@task
def ps():
    sudo('ps auxxxf | grep gunicorn')


@task
def rotate_log():
    """Rotate the LNT log."""
    sudo('rm -rf /srv/lnt/install/gunicorn.error.log')
    out = sudo('ps auxxxf | grep "gunicorn: master"')
    pid = re.search(r'lnt\s+(?P<pid>\d+)\s+', out).groupdict()['pid']
    print pid
    sudo('kill -USR1 ' + pid)


@task
def df():
    sudo('df -h')


@task
def kill_zombies():
    import re
    out = sudo("ps auxxxf")
    stranded = re.compile(r"^lnt\s+(?P<pid>\d+).*00\sgunicorn:\swork")
    pids = []
    for line in out.split('\n'):
        m = stranded.match(line)
        if m:
            pid = m.groupdict()['pid']
            pids.append(pid)
        else:
            print ">", line
    for pid in pids:
        sudo("kill -9 {}".format(pid))


@task
def service_restart():
    """Restarting LNT service with Launchctl"""
    sudo("systemctl restart gunicorn")
