# Task Runner #


## Introduction ##

The task runner tool executes user defined tasks.

Tasks are recipes for performing typical build and test actions as found on
most CI systems. The task runner abstracts those so:
- Tasks can be tracked in a version control repository.
- Multiple tasks can share common files that come with the repository.
- Tasks can be run locally without installing a complete CI system.
- Tasks can be run via ssh on a separate machine without installing a CI system.

Task files describe:
- Required inputs (source control checkouts, artifacts to download,
                   string parameters)
- Steps to perform the task
- The outputs (currently everything the task produced in the `result` folder)
- Tasks are written as posix shell scripts with some conventions and a well
  defined environment.


## Running ##

### Local ###

Tasks can be run on the local machine without a CI system running. Example:
```bash
$ ./task try hello_world3.sh
```

### One-time Jenkins Build ###

We have a special jenkins job running which accepts task submission for
one-time execution. Example:
```bash
$ ./task submit hello_world3.sh
```

### Jenkins Job ###

Tasks can be executed as part of a normal jenkins job. This allows to use
jenkins triggers like version control changes or reporting features like
sending mails on failures to be used.

- The tool assumes the CI system already performed the source code checkouts.
  It will therefore merely verify the expected directories exist.
- Artifacts specified on the commandline (`-a xxx=yyy`) however work as usual.

The corresponding jenkins job should:
- Check out the repository containing the task definition and task runner into
  `${WORKSPACE}/config`
- Checkout all dependent repositories.
- Invoke the task tool in a jenkins shell step. Example:
```bash
config/task jenkinsrun config/hello_world3.sh
```

### SSH Remote ###

Tasks can be executed on a remote machine via ssh without having a CI system
installed. Requirements for this to work:

- Make sure you can login to the remote machine via ssh without a password
- Make sure you can login from the remote to the local machine via ssh
  without a password.
- You can then run on a remote machine. Example:
```bash
$ ./task sshrun mymachine.local hello_world3.sh
```

Notes:

- You can use `username@mymachine.local` to switch user names
- Use `$HOME/.ssh/config` to configure the ssh connection (see ssh docu)
- The script uses `ssh -A` so ssh keys from your local machine are forwarded
  and available on the remote machine.

## Task Tool Operation

### Artifact sources ###

The `task` tool decides what inputs are use for the tasks artifact parameters
before starting/submitting a build.

This is usually done by querying the repository definitions in the `repos`
directory (and `repos.try` in some modes). For example for an artifact
parameter called `llvm` we could have a `repos/llvm.json` configuration file
to query the latest revision of a git repository:
```json
{
    "url": "https://github.com/llvm-mirror/llvm.git",
    "type": "git",
    "default_rev": "refs/heads/master"
}
```

To query the latest artifact from a directory in the A2 artifact server:
```json
{
    "url": "http://lab.llvm.org:8080/artifacts/clang-stage1-configure-RA",
    "type": "artifact_server"
}
```

You can specify an URL to an archive file on the commandline to override the
other mechanisms:

```bash
$ lnt task try -a compiler=http://my.storage.server/my_compiler.tar.bz2
```


## Task Files ##

Tasks files are written as posix shell scripts.
The following describes the environment in which they are executed.

### Tutorial ###

`hello_world0.sh` up to `hello_world3.sh` and
`hello_param.sh` are considered tutorials.
They are simple tasks that are well documented and show more advanced uses with each script.

### Workspace ###

Scripts execute in an empty directory called workspace:
  - The `WORKSPACE` environment variable contains the name of this directory.
  - This directory is exclusively to a single run:
    No other tasks interfere, no files remaining from previous runs.
  - Files outside the workspace directory should not be modified.
    There are some exceptions like creating temporary files or writing
    to `/dev/null`. See `hooks/try.sb` for the sandbox definition.

### Task Parameters ###

A task can have named string and artifact parameters. An artifact is a
directory conaining files and subdirectories. Typical artifact sources are git
repositories or archives from artifact storage servers.

Artifacts can be queried and extracted into a workspace directory with the
same name:
```bash
build get ARTIFACT_NAME
```

To extract an artifact into a directory with a different name use:
```bash
build get DIRECTORY_NAME --from=ARTIFACT_NAME
```

Arguments for string parameters can be queried with:
```bash
VARIABLE="$(build get arg PARAMETER_NAME)"
```

Parameters marked as optional don't need an argument and will then return an
empty string:
```bash
VARIABLE="$(build get arg --optional PARAMETER_NAME)"
```

Other default values can be supplied with the usual shell tricks:
```bash
: ${VARIABLE:='DefaultValue'}
```

- Abstract artifacts like `refs/heads/master` in a git repository or
  `clang-stage2-cmake` on an A2 server are resolved to a concrete git revision
  or a specific URL when the task is started.
- A task with a set of artifact and parameter inputs is called a build.
- `task try mytask.sh` resolves artifact inputs and executes a local build.
- `task submit mytask.sh` resolves artifact inputs and submits a build to
  a queue on a jenkins server.
- `task jenkinsrun mytask.sh` may be used to run the task as part of a
  recurring jenking project.

### Config Artifact ###

The task files are part of a version control repository. When running a task
this repository is always checked out to a subdirectory named `config`.  This
allows task files to bundle and reference additional files in the repository
such as helper scripts shared between multiple tasks.
