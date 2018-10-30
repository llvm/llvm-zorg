import buildbot.status.results
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

        # TODO: Implement autodetect for VS versions other than 2017
        vcvars_command = "for /f \"tokens=* USEBACKQ\" %%F in " \
                            "(`\"%ProgramFiles(x86)%\\Microsoft Visual Studio\\Installer\\vswhere.exe\" -latest -property installationPath`) DO " \
                            "\"%%F\"\\VC\\Auxiliary\\Build\\vcvarsall.bat"
    else:
        # Older versions of VS
        vcvars_command = "\"" + "\\".join((vs, '..','..','VC', 'vcvarsall.bat')) + "\""

    vcvars_command = "%s %s && set" % (vcvars_command, arch_arg)
    return vcvars_command

def extractSlaveEnvironment(exit_status, stdout, stderr):
    '''Helper function for SetPropertyCommand. Loads Slave Environment
    into a dictionary, and returns slave_env property for ShellCommands.'''
    if exit_status:
        return {}
    slave_env_dict = dict(l.strip().split('=',1)
        for l in stdout.split('\n') if len(l.split('=', 1)) == 2)
    return {'slave_env': slave_env_dict}

def extractClangVersion(exit_status, stdout, stderr):
    '''Helper function for SetPropertyCommand. Receives "clang --version" output
    and returns clang_version property for ShellCommands.'''
    if exit_status:
        return {}
    res = re.search(r"version\s*(\S+)", stdout)
    if res:
        return {'clang_version': res.group(1)}
    return {}

def getConfigArgs(origname):
  name = origname
  args = []
  if name.startswith('Release'):
    name = name[len('Release'):]
    args.append('--enable-optimized')
  elif name.startswith('Debug'):
    name = name[len('Debug'):]
  else:
    raise ValueError,'Unknown config name: %r' % origname

  if name.startswith('+Asserts'):
    name = name[len('+Asserts'):]
    args.append('--enable-assertions')
  elif name.startswith('-Asserts'):
    name = name[len('-Asserts'):]
    args.append('--disable-assertions')
  else:
    args.append('--disable-assertions')

  if name.startswith('+Checks'):
    name = name[len('+Checks'):]
    args.append('--enable-expensive-checks')

  if name:
    raise ValueError,'Unknown config name: %r' % origname

  return args

def _did_last_build_fail(buildstep):
  # Grab the build number for the current build.
  build_number = buildstep.build.build_status.number
  # If build number is 0, there is no previous build to fail and the build
  # directory *SHOULD* be clean. So dont clean.
  if build_number == 0:
    return False
  
  # Lookup the status of the last build from the master.
  builder = buildstep.build.builder
  previous_build = builder.master.status.getBuilder(builder.name)\
                                        .getLastFinishedBuild()
  
  # If the previous build is None, do a clean build.
  if previous_build is None:
    return True
  
  # If the previous builder did not succeed, do a clean build.
  return previous_build.getResults() != buildbot.status.results.SUCCESS

