# Routine Maintenance

The cluster requires routine maintenance to ensure it stays functioning.
Ideally, this maintenance is proactive, being performed before any issues arise
from neglect. This document aims to describe the routine maintenance needed
and how to perform it.

## Version Updates

The only routine maintenance that we currently do on the premerge
infrastructure are version updates. The infrastructure utilizes a lot of
different software, and all of it needs to be kept reasonably up to date
to ensure things keep working smoothly and that we are not vulernable to
security issues.

### Getting Notified of Version Updates

There are several pieces of software that we want to upgrade relatively
quickly (like the Github Actions Runner binary). Because of that, knowing
when a new version is released is important. The easiest way to do this is
to subscribe to new release notifications on Github. If you go to a
repository, you can click on the watch button, select custom, and then
select releases. Any new releases for that repository will show up in
your Github notifications.

Releases from the following repositories generally require an update on the
premerge infrastructure side:

1. https://github.com/actions/actions-runner-controller
2. https://github.com/actions/runner
3. https://github.com/llvm/llvm-project

### Github Actions Runner Binary

The runner binary is what runs inside the containers on the cluster to execute
jobs and report status results back to Github. The runner binary has a
relatively short time horizon (about six months) before it becomes unsupported
by Github and it will no longer work.

When a new runner binary is released, there are three places that need to
be updated in a PR against the LLVM monorepo:

1. The Linux CI container - The `Dockerfile` at
`.github/workflows/containers/github-action-ci/Dockerfile` has an environment
variable towards the bottom of the file called `GITHUB_RUNNER_VERSION` that
needs to be updated to the new version.
2. The Windows CI container - The `Dockerfile` at
`.github/workflows/containers/github-action-ci-windows/Dockerfile` has an
argument called `RUNNER_VERSION` near the bottom of the file that needs to
be updated to the new version.
3. The libc++ CI container - The `docker-compose` manifest at
`libcxx/utils/ci/docker-compose.yml` needs to be updated by updating the
`GITHUB_RUNNER_VERSION` variable to pull in the latest
runner images using the [libc++ instructions](https://libcxx.llvm.org/Contributing.html#updating-the-ci-testing-container-images)

### Other Container Image Software

The container images also contain many other pieces of software critical
for building LLVM, like CMake, ninja, and the toolchain itself. Keeping
most of these up to date is ideal.

A large amount of the software comes from the Linux distribution and thus does
not need to be explicitly updated. We prefer to install software from the
distribution when possible. However, this does mean that distribution updates
are quite important. To update the distribution for the Linux container, perform
the following steps:

1. Modify `.github/workflows/containers/github-action-ci/Dockerfile` locally
to use the latest `ubuntu:xx.04` image.
2. Ensure that `monolithic-linux.sh` with all options enabled runs successfully.
Push any needed changes. You can see the canonical invocation with all options
in `zorg/buildbot/builders/annotated/premerge/dispatch_job.py` within the
`llvm-zorg` repository.
3. Push the updated `Dockerfile` and update the workflow in
`.github/workflows/build-ci-container.yml` to use the correct image name, specifically
by updating the `container-name` value to use the correct ubuntu version.
4. Update the runner configuration in zorg (`premerge/linux_runners_values.yaml`)
to point to the new image.

Updating explicitly versioned software (just LLVM in the Linux container, but
most software in the Windows container) just requires bumping the version number
and pushing the new image to the monorepo. In the Linux container, the LLVM
version can be bumped by changing the `LLVM_VERSION` environment variable. In
the Windows container, versions of many of the packages we install are
controlled by the `--version` flag passed to `choco install` commands.

### Actions Runner Controller

The actions runner controller orchestrates all of the jobs on the cluster.
Given its key role, upgrading it needs to be done carefully using the
[described steps](cluster-management.md#upgradingresetting-github-arc) to
avoid any downtime.

It is advised to do this during a portion of the day with light traffic as
any upgrade will involve having an entire cluster down at times, which reduces
capacity in half.

### Windows Edition

Whenever a new Windows Server datacenter edition (eg 2025) is supported by GKE,
all of the windows infrastructure needs to be updated. This involves several
steps that will take significant time:

1. Modify `.github/workflows/containers/github-action-ci-windows/Dockerfile`
locally to get it building on the new Windows Server version. This requires
having a host at that version as Windows Server containers can only run on a
host with the same edition. Obtaining a host is most easily done by creating
a GCP virtual machine in the premerge project, for this with access.
Then, changing the `FROM` line at the top of the
`Dockerfile` has previously been enough.
2. When that is ready, push your changes in a PR along with changes to
`.github/workflows/build-ci-container-windows.yml` so that it uses the new
Windows Server edition. The only changes needed in the workflow file assuming
things go smoothly are the `runs-on` lines to reference the new Windows version.
3. Test locally that the pushed container image can run the
`monolithic-windows.sh` script with all projects enabled successfully. Make
and submit any changes that are needed. To test the script,
use `docker run` to launch the new container from the LLVM packages list
(https://github.com/orgs/llvm/packages). Then, clone the repository into
the container with
`git clone --config core.autocrlf=false https://github.com/llvm/llvm-project`.
Move into that directory, and then run the `monolithic-windows.sh` script.
An invocation should look like
`.ci/monolithic-windows.sh "clang;clang-tools-extra;libclc;lld;llvm;mlir;polly" "check-clang check-clang-tools check-lld check-llvm check-mlir check-polly"`.
The most recent version of the command should be in
`buildbot/builders/annotated/premerge/dispatch_job.py` within the `llvm-zorg`
repository.
4. Duplicate all of the versioned Windows resources in the terraform
configuration and apply it. This involves duplicating everything referencing
the old windows version in the `premerge/` folder in the llvm-zorg repo and
updating it to be named for/reference the new windows version.
5. Switch the workflow in `.github/workflows/premerge.yaml` to the new
runner set.
6. Sunset the existing runnerset in 1-2 weeks by deleting it and any other
resources specific to the old Windows version to give time for people utilizing
stacked PRs to rebase.
