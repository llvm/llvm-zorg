# Load local options.
import os
from importlib import reload

from configparser import ConfigParser
options = ConfigParser(
            interpolation=None,
            empty_lines_in_values=False,
            allow_no_value=True,
          )
          
for f in ['local.cfg', 'worker-passwords.cfg']:
    print(f"Loading options '{f}' ...")
    options.read(os.path.join(os.path.dirname(__file__), f))

# Detect if the BUILDBOT_TEST environment variable is set and non-zero. This
# will be used to enable a local testing mode.
test_mode = os.getenv('BUILDBOT_TEST', '').lower() in {'1', 'true', 'on', 'yes', 'y'}
options.add_section('Internal')
options.set('Internal', 'test_mode', str(test_mode))

# Override some the configuration options for the configuration test mode.
if test_mode:
    for section in ['Buildbot', 'Protocols', 'Database', 'Master Options']:
        if not options.has_section(section):
            options.add_section(section)

    options.set('Buildbot', 'title', "Buildbot (test)")
    options.set('Buildbot', 'title_url', "http://localhost:8011/")
    options.set('Buildbot', 'my_url', "http://localhost:8011/")
    options.set('Buildbot', 'www_port', "tcp:8011:interface=127.0.0.1")
    options.set('Protocols', 'pb_port', "tcp:9990:interface=127.0.0.1")
    options.set('Database', 'db_url', "sqlite:///state.sqlite")
    options.set('Master Options', 'allow_orphan_workers', "True")
    options.set('Master Options', 'no_authentication', "True")
    options.set('Master Options', 'no_authorization', "True")
    options.set('Master Options', 'allow_ignore_offline_workers_timeout', "False")

import config.auth
import config.builders
import config.release_builders
import config.schedulers
import config.workers
import config.status

# Note: The following modules should be reloaded in
# a particular order to follow the dependency chain.
reload(config.auth)
reload(config.workers)
reload(config.schedulers)
reload(config.builders)
reload(config.release_builders)
reload(config.status)
