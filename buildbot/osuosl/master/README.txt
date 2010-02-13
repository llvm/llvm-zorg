This directory contains the configuration for the public LLVM
buildbot, currently hosted at OSUOSL.

Most of the configuration is in LLVM, except for a few details on the
local configuration which are kept in config/local.cfg. Any sensitive
information should be placed in the local configuration file, not in
the public repository.

For connecting SVN author names to emails, there is also a required
config/llvmauthors.cfg file which should provide the mapping.

