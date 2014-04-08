# Load local options.
import os
import ConfigParser
options = ConfigParser.RawConfigParser()
options.read(os.path.join(os.path.dirname(__file__), 'local.cfg'))

import builders
import slaves
import status
