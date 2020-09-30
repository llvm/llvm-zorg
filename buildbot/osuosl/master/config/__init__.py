# Load local options.
import os
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
