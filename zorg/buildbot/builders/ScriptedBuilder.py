import buildbot
from buildbot.steps.shell import WarningCountingShellCommand, SetProperty
from buildbot.process.properties import WithProperties

def getScriptedBuildFactory(
                      source_code  = [],   # List of source code check out commands.
                      launcher     = None, # Build script launcher name.
                      build_script = None, # Build script name or common prefix.
                      extra_args   = [],   # Extra args common for all steps.
                      build_steps  = [],   # List of step commands.
                      env          = {},   # Environmental variables for all steps.
                      timeout      = 20):  # Timeout if no activity seen (minutes).

    # Validate input parameters
    if not launcher:
      raise ValueError,"Must specify launcher."

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(
      buildbot.steps.shell.SetProperty(
        name        = "get.builddir",
        command     = ["pwd"],
        property    = "builddir",
        description = "set build dir",
        workdir     = "."))

    # Common for all steps arguments
    scripted_step_common_args = list()
    # build_script is optional but must go first if given.
    if build_script:
      scripted_step_common_args.append(WithProperties(build_script))

    # Get all the source code directories we need for this build.
    for checkout in source_code:
      # Store the list of source code directories in the original order for later use.
      # Note: We require all spaces and special characters already escaped.
      try:
        src_dir = checkout.workdir
        if src_dir:
          scripted_step_common_args.append(WithProperties(src_dir))
      except AttributeError:
        # workdir property is missing. Skip it.
        pass

      # Get the source code from version control system
      f.addStep(checkout)

    # The last common arg is build directory
    scripted_step_common_args.append(WithProperties("%(builddir)s"))

    # Run build script for each requested step
    for step_params in build_steps:
      # TODO: Validate type step_params is dict 

      # Handle some of the parameters here.
      scripted_step_name            = step_params.pop('name',            None)
      scripted_step_type            = step_params.pop('type',            WarningCountingShellCommand)
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
        scripted_step_type(
          name            = "run.build.step." + scripted_step_name,
          description     = scripted_step_description,
          descriptionDone = scripted_step_descriptionDone,
          command = (
            [WithProperties("%(builddir)s/"      + launcher)] +
            scripted_step_common_args            +  # Common args
            [WithProperties(scripted_step_name)] +  # The requested step name
            scripted_step_extra_args             +  # Step-specific extra args 
            extra_args                              # Common extra args
          ),
          **step_params))

    if len(build_steps) == 0: # If no steps were defined.

      # Run the build_script once
      f.addStep(
          WarningCountingShellCommand(
            name="run.build.script",
            command=(
              [WithProperties("%(builddir)s/"    + launcher)] +
              scripted_step_common_args          +  # Common args
              extra_args                            # Common extra args
            ),
            haltOnFailure = True,
            description   = "Run build script",
            workdir       = ".",
            env           = env,
            timeout       = timeout*60))

    return f
