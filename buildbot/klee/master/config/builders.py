from zorg.buildbot.builders import LLVMBuilder
reload(LLVMBuilder)
from zorg.buildbot.builders import LLVMBuilder

def _get_linux_builders():
    return [
        {'name': "klee-x86_64-linux",
         'slavenames': ["klee.minormatter.com"],
         'builddir': "build.klee-x86_64-linux", 
         'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu", jobs=2)},
        ]

def get_builders():
    for b in _get_linux_builders():
        b['category'] = 'linux'
        yield b
