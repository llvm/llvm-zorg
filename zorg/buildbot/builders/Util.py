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

  if name.startswith('-Asserts'):
    name = name[len('-Asserts'):]
    args.append('--disable-assertions')

  if name.startswith('+Checks'):
    name = name[len('+Checks'):]
    args.append('--enable-expensive-checks')

  if name:
    raise ValueError,'Unknown config name: %r' % origname

  return args
