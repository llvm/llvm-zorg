# RUN: python %s

import zorg
from zorg.buildbot.builders import ClangBuilder, LLVMBuilder, LLVMGCCBuilder
from zorg.buildbot.builders import SanitizerBuilder

# Just check that we can instantiate the build factors, what else can we do?

print ClangBuilder.getClangBuildFactory()

print LLVMBuilder.getLLVMBuildFactory()

print LLVMGCCBuilder.getLLVMGCCBuildFactory()

print SanitizerBuilder.getSanitizerBuildFactory()
