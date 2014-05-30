#from zorg.buildbot.builders.LNTBuilder import CreateLNTNightlyFactory
from zorg.buildbot.util.artifacts import rsync_user, master_name
import zorg.buildbot.builders.ClangBuilder as ClangBuilder
from zorg.buildbot.builders.LLDBBuilder import getLLDBxcodebuildFactory
import zorg.buildbot.builders.LibCXXBuilder as LibCXXBuilder


"""
Helper module to handle automatically constructing builder objects from a
builder name.

We use a relatively unambigous mangling of builder names to ensure that any
particular builder name is always descriptive of its job.
"""

# Builder Construction Dispatch

__all__ = ['construct']
def construct(name):
    """
    construct(name) -> builder

    Given a builder name, demangle the name and construct the appropriate
    builder for it.
    """

    # First, determine the 'kind' of build we are doing. Compiler builds are a
    # common case, so we specialize their names -- other builds should have
    # their type delimited by '_'.
    if name.startswith('clang-'):
        kind,subname = 'compile',name
        if 'lto' in name:
            kind += '-lto'
        elif 'incremental' in name:
            kind += '-incremental'
    else:
        if '_' not in name:
            raise ValueError, "invalid builder name: %r" % name
        kind,subname = name.split('_', 1)

    # Dispatch based on the kind of build.
    ctor = builder_kinds.get(kind)
    if ctor is None:
        raise ValueError, "invalid builder name: %r" % name

    # Construct the builder.
    builder = ctor(subname)

    # Validate that the ctor didn't attempt to define the name, build directory,
    # slaves or category.
    if 'name' in builder:
        raise ValueError, "name should not be defined by builder ctors!"
    if 'builddir' in builder:
        raise ValueError, "builddir should not be defined by builder ctors!"
    if 'slavename' in builder or 'slavenames' in builder:
        raise ValueError, "slaves should not be defined by builder ctors!"
    if 'category' in builder:
        raise ValueError, "categories should not be defined by builder ctors!"

    # The build directory is always based on the name.
    try:
        builder['name'] = name
    except TypeError:
        raise ValueError, "invalid builder name: %r" % name
    builder['builddir'] = 'build.%s' % name

    return builder

def construct_compiler_builder_from_name(name, use_lto=False,
                                         incremental=False):

    # Compiler builds are named following:
    #   <compiler>-<host arch>-<host os>-[<build cc>-]<build style>.
    # if <build cc> is unspecified, then the most recent validated build 
    # for this builder will be used as <build cc>
    # This can be undesirable. e.g. when building a Debug+Asserts compiler
    # for the time being, DA builds will bootstrap with the most recent 
    # validated RA build
    # At the moment, if anything is specified as <build cc> the build factory
    # will default to host's default compiler
    
    # Hack around x86_64 problem for now, to avoid changing builder names yet.
    #
    # FIXME: Use a better mangling.
    params = name.replace("x86_64", "x86$64").split('_')
    if len(params) == 2:
        name, branch = params
    name = name.replace("x86$64", "x86_64")
    params = name.replace('llvm-gcc', 'llvm$gcc').split('-')
    params = [p.replace('llvm$gcc', 'llvm-gcc')
              for p in params]
    if len(params) == 4:
        compiler,host_arch,host_os,build_style = params
        build_cc = None
    elif len(params) == 5:
        compiler,host_arch,host_os,build_cc,build_style = params
    else:
        raise ValueError, "invalid builder name: %r" % name

    # Check if this is an MSVC builder.
    if host_os == 'xp':
        if compiler == 'clang':
            # FIXME: This isn't using the host arch, build cc or
            if (host_arch != 'i386' or build_cc != 'msvc9' or
                build_style != 'DA'):
                raise ValueError, "invalid builder name: %r" % name
            # FIXME: Shouldn't have to hard code jobs or cmake path here.
            return { 'factory' : ClangBuilder.getClangMSVCBuildFactory(
                    cmake = r"c:\Program Files\CMake 2.8\bin\cmake",
                    jobs = 4) }
        else:
            raise NotImplementedError

    target_triple = '%s-apple-%s' % (host_arch, host_os)
    config_options = ['--build=%s' % target_triple,
                      '--host=%s' % target_triple]

    if build_style in ['DA', 'DAlto', 'DAincremental']:
        build_config = "Debug+Asserts"
        config_options.extend(['--disable-optimized'])
        config_options.extend(['--enable-assertions'])
    elif build_style in ['RA', 'RAlto', 'RAincremental']:
        build_config = "Release+Asserts"
        config_options.extend(['--enable-optimized'])
        config_options.extend(['--enable-assertions'])
    elif build_style in ['R', 'Rlto', 'Rincremental']:
        build_config = "Release"
        config_options.extend(['--enable-optimized'])
        config_options.extend(['--disable-assertions'])
    else:
        raise ValueError, "invalid build style: %r" % build_style

    # Passing is_bootstrap==False will specify the stage 1 compiler as the
    # latest validated apple-clang style compiler.

    # build_cc must be set for a bootstrapped compiler
    if compiler == 'clang':
        if host_os == 'darwin11':
            config_options.extend(['--enable-libcpp'])

        return { 'factory' : ClangBuilder.phasedClang(config_options,
                                         is_bootstrap=(build_cc is None),
                                         use_lto=use_lto,
                                         incremental=incremental) }
    elif compiler == 'llvm-gcc':
        # Currently, llvm-gcc builders do their own two-stage build,
        # they don't use any prebuilt artifacts.

        # Set the gxxincludedir.
        if host_os == 'darwin9':
            gxxincludedir = "/usr/include/c++/4.0.0"
        elif host_os == 'darwin11':
            gxxincludedir = "/usr/include/c++/v1"            
        else:
            gxxincludedir = "/usr/include/c++/4.2.1"

        # Construct the GCC style build triple:
        if host_arch == "i386" and host_os.startswith("darwin"):
            triple = 'i686-apple-%s' % host_os
        elif host_arch == "x86_64" and host_os.startswith("darwin"):
            triple = 'x86_64-apple-%s' % host_os
        else:
            raise ValueError, "invalid builder name: %r" % name

        dst = rsync_user + '@' + master_name + ':~/artifacts/' + name + '/'
        return {
            'factory' : LLVMGCCBuilder.getLLVMGCCBuildFactory(
                jobs = '%(jobs)s', triple = triple,
                gxxincludedir = gxxincludedir,
                stage1_config = build_config, stage2_config = build_config,
                package_dst = dst) }
    else:
        raise NotImplementedError

def construct_lnt_builder_from_name(name):
    # LNT builds are named following:
    #   lnt_<compiler under test>_<arch>_<options>.
    # and all options are prefixed by '-' and no '-' can appear in an option.

    # Hack around x86_64 problem for now, to avoid changing builder names yet.
    #
    # FIXME: Use a better mangling.
    params = name.replace("x86_64", "x86$64").split('_')
    params = [p.replace("x86$64", "x86_64")
              for p in params]
    if len(params) == 2:
        cc_under_test,lnt_options_string = params
    else:
        raise ValueError, "invalid builder name: %r" % name
    cc_path = None
    cxx_path = None
    # We assume that '-' will never occur in an LNT option. Sounds risky, no?
    split_options = lnt_options_string.split('-')
    arch = split_options[0]
    lnt_options = ['-'+s
                   for s in split_options[1:]]

    # Create the LNT flags.
    lnt_flags = []

    # If this is llvm-gcc, don't expect it to honor -arch (that is actually the
    # "driver driver"). Hard coded to support only i386 and x86_64 for now.
    if name.startswith('llvm-gcc'):
        if arch == 'x86_64':
            lnt_flags.extend(["--cflag", "-m64"])
        elif arch == 'i386':
            lnt_flags.extend(["--cflag", "-m32"])
        else:
            raise ValueError, "invalid builder name: %r" % name
    else:
        lnt_flags.extend(["--arch", arch])
    for option in lnt_options:
        # FIXME: Reorganize this.
        if option in ('-g','-flto'):
            lnt_flags.extend(["--cflag", option])
        else:
            lnt_flags.extend(["--optimize-option", option])
    lnt_flags.append("--small")

    return { 'factory' : CreateLNTNightlyFactory(lnt_flags, cc_path,
                                                          cxx_path,
                                                          parallel = True,
                                                          jobs = "2"),
             'properties' : {'use_builder' : cc_under_test } }

def construct_lldb_builder_from_name(name):
    cc_under_test = name
    params = name.split('-')
    if len(params) == 4:
        compiler, host_arch, host_os, kind = params
    else: 
        raise ValueError, "invalid builder name: %r" % name
    lldb_triple = '-'.join([host_arch,host_os])
    return { 'factory': getLLDBxcodebuildFactory()}

def construct_lto_compiler_builder_from_name(name):
    return construct_compiler_builder_from_name(name, use_lto=True)

def construct_incremental_compiler_build_from_name(name):
    return construct_compiler_builder_from_name(name, incremental=True)    

def construct_libcxx_builder_from_name(name):
    # libcxx builds are named following:
    #   libcxx_<compiler under test>
    
    cc_under_test = name
    return { 'factory' : LibCXXBuilder.getLibCXXBuilder(),
             'properties' : {'use_builder' : cc_under_test } }

builder_kinds = {
                  'compile' : construct_compiler_builder_from_name,
                  'compile-lto' : construct_lto_compiler_builder_from_name,
                  'compile-incremental' :
                      construct_incremental_compiler_build_from_name,
                  'lnt' : construct_lnt_builder_from_name,
                  'lldb' : construct_lldb_builder_from_name,
                  'libcxx' : construct_libcxx_builder_from_name }

# Testing.

if __name__ == '__main__':
    from phase_config import phases
    for phase in phases:
        for build in phase['builders']:
            print construct(build)
