# Load local options.
import os
from importlib import reload

from configparser import ConfigParser
options = ConfigParser(
            interpolation=None,
            empty_lines_in_values=False,
            allow_no_value=True,
          )
options.read(os.path.join(os.path.dirname(__file__), 'local.cfg'))

import config.auth
import config.builders
import config.schedulers
import config.workers
import config.status

# Note: The following modules should be reloaded in
# a particular order to follow the dependency chain.
reload(config.auth)
reload(config.workers)
reload(config.schedulers)
reload(config.builders)
reload(config.status)
