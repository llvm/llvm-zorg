# This file is part of the LLVM build and test infrastructure.
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from buildbot.interfaces import IRenderable
from buildbot.process.properties import WithProperties
from zope.interface import implements


class InterpolateToNativePath(WithProperties):
    """
    This is a marker class, used to indicate that we
    want to interpolate build properties as a paths with
    the correct buildslave path separator.
    """

    implements(IRenderable)
    compare_attrs = ('fmtstring', 'args')

    def __init__(self, fmtstring, *args, **lambda_subs):
        WithProperties.__init__(self, fmtstring, *args, **lambda_subs)

    def getRenderingFor(self, build):
        # Upcall the base class first.
        p = WithProperties.getRenderingFor(self, build)

        # Then we need to normalize the path for
        # watever is native on the buildslave.
        # Note: Do not call normpath here, as it could
        # change the path meaning if links used.
        slave = build.build.slavebuilder.slave

        return slave.path_module.normcase(p)


class InterpolateToPosixPath(WithProperties):
    """
    This is a marker class, used to indicate that we
    want to interpolate build properties as a paths with
    POSIX path separator.
    """

    implements(IRenderable)
    compare_attrs = ('fmtstring', 'args')

    def __init__(self, fmtstring, *args, **lambda_subs):
        WithProperties.__init__(self, fmtstring, *args, **lambda_subs)

    def getRenderingFor(self, build):
        # Upcall the base class first.
        p = WithProperties.getRenderingFor(self, build)

        # Then we need to figure out the buildslave OS:
        slave = build.build.slavebuilder.slave
        if slave.slave_system == 'posix':
            # Note: Do not call normpath here, as it could
            # change the path meaning if links used.
            p = slave.path_module.normcase(p)
        elif slave.slave_system in ('win32', 'nt'):
            # Normalize the path first, then replace
            # the path separator to the POSIX one.
            p = slave.path_module.normcase(p).replace('\\','/')
        else:
            # Return the string as is.
            pass

        return p
