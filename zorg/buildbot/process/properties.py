# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from zope.interface import implementer

from buildbot.interfaces import IRenderable
from buildbot.process.properties import WithProperties


@implementer(IRenderable)
class InterpolateToNativePath(WithProperties):
    """
    This is a marker class, used to indicate that we
    want to interpolate build properties as a paths with
    the correct worker path separator.
    """

    def getRenderingFor(self, build):
        # Upcall the base class first.
        p = super().getRenderingFor(build)

        # Then we need to normalize the path for
        # watever is native on that worker.
        # Note: Do not call normpath here, as it could
        # change the path meaning if links are used.
        worker = build.getBuild().workerforbuilder.worker
        return worker.path_module.normcase(p)


@implementer(IRenderable)
class InterpolateToPosixPath(WithProperties):
    """
    This is a marker class, used to indicate that we
    want to interpolate build properties as a paths with
    POSIX path separator.
    """

    def getRenderingFor(self, build):
        # Upcall the base class first.
        p = super().getRenderingFor(build)

        # Then we need to figure out the worker OS:
        worker = build.getBuild().workerforbuilder.worker
        if worker.worker_system == 'posix':
            # Note: Do not call normpath here, as it could
            # change the path meaning if links used.
            p = worker.path_module.normcase(p)
        elif worker.worker_system in ('win32', 'nt'):
            # Preserve the case, only replace
            # the path separator to the POSIX one.
            p = p.replace('\\','/')
        else:
            # Return the string as is.
            pass

        return p
