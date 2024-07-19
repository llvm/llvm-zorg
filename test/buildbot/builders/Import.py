# RUN: python %s

import zorg
from zorg.buildbot.builders import ClangBuilder
from zorg.buildbot.builders import SanitizerBuilder

# Just check that we can instantiate the build factors, what else can we do?

print("{}".format(ClangBuilder.getClangCMakeBuildFactory()))

print("{}".format(SanitizerBuilder.getSanitizerBuildFactory()))
