from zorg.buildbot.builders import KLEEBuilder
reload(KLEEBuilder)
from zorg.buildbot.builders import KLEEBuilder

def _get_linux_builders():
    return [
        { 'name'       : "klee-x86_64-linux",
          'slavenames' : ["klee.minormatter.com"],
          'builddir'   : "build.klee-x86_64-linux", 
          'factory'    : KLEEBuilder.getKLEEBuildFactory("x86_64-pc-linux-gnu", clean=False) },

        { 'name'       : "klee-2.7-x86_64-linux",
          'slavenames' : ["klee.minormatter.com"],
          'builddir'   : "build.klee-2.7-x86_64-linux", 
          'factory'    : KLEEBuilder.getKLEEBuildFactory(
                "x86_64-pc-linux-gnu", clean=False,
                llvm_branch='tags/RELEASE_27',
                llvmgccdir='/home/klee-buildslave/llvm-gcc-4.2-2.7-x86_64-linux') },

        { 'name'       : "klee-2.6-x86_64-linux",
          'slavenames' : ["klee.minormatter.com"],
          'builddir'   : "build.klee-2.6-x86_64-linux", 
          'factory'    : KLEEBuilder.getKLEEBuildFactory(
                "x86_64-pc-linux-gnu", clean=False,
                llvm_branch='tags/RELEASE_26',
                llvmgccdir='/home/klee-buildslave/llvm-gcc-4.2-2.6-x86_64-linux') },
        ]

def get_builders():
    for b in _get_linux_builders():
        b['category'] = 'linux'
        yield b
