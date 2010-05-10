import buildbot
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.process.properties import WithProperties

def getScriptedBuildFactory(
                      source_code  = [],   # List of source code check out commands.
                      launcher     = None, # Build script launcher name.
                      build_script = None, # Build script name or common prefix.
                      extra_args   = [],   # Extra args common for all steps.
                      build_steps  = [],   # List of step commands.
                      env          = {}):  # Environmental variables for all steps.

    # Validate input parameters
    if not launcher:
      raise ValueError,"Must specify launcher."
    if not build_script:
      raise ValueError,"Must specify build_script."

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(
      buildbot.steps.shell.SetProperty(
        name        = "get.builddir",
        command     = ["pwd"],
        property    = "builddir",
        description = "set build dir",
        workdir     = "."))

    # Get all the source code we need for this build
    for checkout in source_code:

      # Figure out from the source code check out commands where
      # llvm and llvm-gcc source code directories are.
      if checkout.name == 'svn-llvm':
        llvm_src_dir = checkout.args.get('workdir', None)
      elif checkout.name == 'svn-llvm-gcc':
        llvm_gcc_src_dir = checkout.args.get('workdir', None)

      f.addStep(checkout)

    assert llvm_src_dir,     \
      "Cannot retrieve where llvm source code gets checked out to."
    assert llvm_gcc_src_dir, \
      "Cannot retrieve where llvm-gcc source code gets checked out to."

    # Run build script for each requested step
    for step_params in build_steps:
      # TODO: Validate type step_params is dict 

      # Handle some of the parameters here.
      scripted_step_name            = step_params.pop('name',            None)
      scripted_step_description     = step_params.pop('description',     None)
      scripted_step_descriptionDone = step_params.pop('descriptionDone', None)
      scripted_step_extra_args      = step_params.pop('extra_args',      [])
      scripted_step_env             = step_params.pop('env',             {})
      # The rest will pass through.

      assert 'command' not in step_params, "Command is generated, please do not specify it."

      # scripted_step_extra_args must be a list
      if isinstance(scripted_step_extra_args, str):
          scripted_step_extra_args = [scripted_step_extra_args]

      # Combine together common env and step-specific env
      scripted_step_env.update(env)
      step_params['env'] = scripted_step_env

      f.addStep(
        ShellCommand(
          name            = "run.build.step." + scripted_step_name,
          description     = scripted_step_description,
          descriptionDone = scripted_step_descriptionDone,
          command = (
            [WithProperties("%(builddir)s/"      + launcher)] +
            [WithProperties(build_script)]       +  # Build script to launch
            [WithProperties(llvm_src_dir)]       +  # TODO: Escape spaces and special charactes
            [WithProperties(llvm_gcc_src_dir)]   +  # TODO: Escape spaces and special charactes
            [WithProperties("%(builddir)s")]     +  # TODO: Escape spaces and special charactes
            [WithProperties(scripted_step_name)] +  # The requested step name
            scripted_step_extra_args             +  # Step-specific extra args 
            extra_args                              # Common extra args
          ),
          **step_params))

    if len(build_steps) == 0: # If no steps were defined.

      # Run the build_script once
      f.addStep(
          ShellCommand(
            name="run.build.script",
            command=(
              [WithProperties("%(builddir)s/"    + launcher)] +
              [WithProperties(build_script)]     +  # Build script to launch
              [WithProperties(llvm_src_dir)]     +  # TODO: Escape spaces and special charactes
              [WithProperties(llvm_gcc_src_dir)] +  # TODO: Escape spaces and special charactes
              [WithProperties("%(builddir)s")]   +  # TODO: Escape spaces and special charactes
            extra_args                              # Common extra args
            ),
            haltOnFailure = True,
            description   = "Run build script",
            workdir       = ".",
            env           = env))

    return f
