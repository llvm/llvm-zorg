import buildbot
import zope

class ConfigEmailLookup(buildbot.util.ComparableMixin):
  """
  Email lookup implementation which searchs a user specified configuration
  file to match commit authors to email addresses.
  """

  # FIXME: This should be able to reload the config file when it
  # changes.

  zope.interface.implements(buildbot.interfaces.IEmailLookup)
  compare_attrs = ["author_filename", "default_address", "only_addresses"]

  def __init__(self, author_filename, default_address, only_addresses = None):
    from ConfigParser import ConfigParser

    self.author_filename = author_filename
    self.default_address = default_address
    self.only_addresses = only_addresses

    self.config_parser = ConfigParser()
    self.config_parser.read(author_filename)

    if only_addresses:
      import re
      self.address_match_p = re.compile(only_addresses).match
    else:
      self.address_match_p = lambda addr: True

  def getAddress(self, name):
    try:
      email = self.config_parser.get("authors", name)
    except:
      return self.default_address

    if self.address_match_p(email):
      return email

    return self.default_address
