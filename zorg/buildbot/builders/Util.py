
import buildbot.status.results

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

