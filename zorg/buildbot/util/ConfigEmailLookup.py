import buildbot
import zope
import os

from datetime import datetime, timedelta
from twisted.python import log

class ConfigEmailLookup(buildbot.util.ComparableMixin):
  """
  Email lookup implementation which searchs a user specified configuration
  file to match commit authors to email addresses.
  """

  # TODO: Document this class.
  # Class loads llvm_authors from file and reload if the file was updated.

  zope.interface.implements(buildbot.interfaces.IEmailLookup)
  compare_attrs = ["author_filename", "default_address", "only_addresses"]

  def __init__(self, author_filename, default_address, only_addresses = None, update_interval=timedelta(hours=1)):
    from ConfigParser import ConfigParser

    self.author_filename = author_filename
    self.default_address = default_address
    self.only_addresses = only_addresses
    self.update_interval = update_interval

    self.config_parser = ConfigParser()
    self.config_parser.read(self.author_filename)

    self.time_checked = datetime.utcnow()
    self.time_loaded  = datetime.utcfromtimestamp(os.path.getmtime(self.author_filename))

    if only_addresses:
      import re
      self.address_match_p = re.compile(only_addresses).match
    else:
      self.address_match_p = lambda addr: True

  def getAddress(self, name):

    try:

      if (datetime.utcnow() - self.time_checked) >= timedelta(minutes=1):
        self.time_checked = datetime.utcnow()
        current_mtime = datetime.utcfromtimestamp(os.path.getmtime(self.author_filename))

        if (current_mtime != self.time_loaded) and ((datetime.utcnow() - current_mtime) >= timedelta(minutes=1)):
          # Reload the list of authors.
          self.config_parser.read(self.author_filename)
          self.time_loaded = current_mtime
          log.msg('Reloaded file %s (mtime=%s) at %s' % (self.author_filename, self.time_loaded, self.time_checked))

    except:
      log.msg('Cannot load the %s file.' % self.author_filename)
      pass

    try:
      email = self.config_parser.get("authors", name)
    except:
      return self.default_address

    if self.address_match_p(email):
      return email

    return self.default_address
