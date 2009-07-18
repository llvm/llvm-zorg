import buildbot
import zope

class ConfigEmailLookup(buildbot.util.ComparableMixin):
  """
  Email lookup implementation which searchs a user specified configuration
  file to match commit authors to email addresses.
  """

  zope.interface.implements(buildbot.interfaces.IEmailLookup)
  compare_attrs = ["author_filename", "default_address"]

  def __init__(self, author_filename, default_address):
    from ConfigParser import ConfigParser

    self.author_filename = author_filename
    self.default_address = default_address

    self.config_parser = ConfigParser()
    self.config_parser.read(author_filename)

  def getAddress(self, name):
    try:
      return self.config_parser.get("authors", name)
    except:
      return self.default_address
