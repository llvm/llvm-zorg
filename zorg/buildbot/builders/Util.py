from buildbot.process.results import SUCCESS
import re

def getVisualStudioEnvironment(vs=None, target_arch=None):
    # x86 builds should use the 64 bit -> x86 cross compilation toolchain to avoid
    # out of memory linker errors
    arch_arg = {'x86': 'amd64_x86', 'x64': 'amd64', 'amd64': 'amd64'}.get(target_arch, '%PROCESSOR_ARCHITECTURE%')

    if vs is None:
        vs = r"""%VS120COMNTOOLS%""" # To keep the backward compatibility.

    if vs.lower() == "autodetect":
        """Get the VC tools environment using vswhere.exe from VS 2017 if it exists and was requested.
        Otherwise, use the vs argument to construct a path to the expected location of vcvarsall.bat

        This code is following the guidelines from strategy 1 in this blog post:
        https://blogs.msdn.microsoft.com/vcblog/2017/03/06/finding-the-visual-c-compiler-tools-in-visual-studio-2017/

        It doesn't work when VS is not installed at the default location.
        """

        # LLVM code base requires VS 2017 or later.
        # This means vswhere.exe later than 1.0.40, so we add `-products *` to include Build Tools in the search
        # to support build-tools only installations.
        vcvars_command = "for /f \"tokens=* USEBACKQ\" %%F in " \
                            "(`\"%ProgramFiles(x86)%\\Microsoft Visual Studio\\Installer\\vswhere.exe\" -products * -latest -property installationPath`) DO " \
                            "\"%%F\"\\VC\\Auxiliary\\Build\\vcvarsall.bat"
    else:
        # Note: Support for older versions of VS is deprecated and will be removed.
        vcvars_command = "\"" + "\\".join((vs, '..','..','VC', 'vcvarsall.bat')) + "\""

    vcvars_command = "%s %s && set" % (vcvars_command, arch_arg)
    return vcvars_command

def extractVSEnvironment(exit_status, stdout, stderr):
    '''Helper function for SetPropertyCommand.
    Loads Visual Studio Environment into a dictionary,
    and returns vs_env property for ShellCommands.'''
    if exit_status:
        return {}
    vs_env_dict = dict(l.strip().split('=',1)
        for l in stdout.split('\n') if len(l.split('=', 1)) == 2)
    return {'vs_env': vs_env_dict}
