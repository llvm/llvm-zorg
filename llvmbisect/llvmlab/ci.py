"""
Tools for working with llvmlab CI infrastructure.
"""

import errno
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time


from . import shell
from . import algorithm
from . import llvmlab
from . import util
from util import warning, fatal, note
from . import scripts
from . import util

from optparse import OptionParser


class Command(object):
    class Filter(object):
        def __init__(self):
            pass

        def evaluate(self, command):
            raise RuntimeError("Abstract method.")

    class NotFilter(Filter):
        def evaluate(self, command):
            warning("'negate' filter is deprecated, use 'not result' "
                    "filter expression")
            command.result = not command.result

    class MaxTimeFilter(Filter):
        def __init__(self, value):
            try:
                self.value = float(value)
            except:
                fatal("invalid argument: %r" % time)
            warning("'max_time' filter is deprecated, use "
                    "'user_time < %.4f' filter expression" % self.value)

        def evaluate(self, command):
            if command.metrics["user_time"] >= self.value:
                command.result = False

    available_filters = {"negate": NotFilter(),  # note this is an instance.
                         "max_time": MaxTimeFilter}

    def __init__(self, command, stdout_path, stderr_path, env):
        self.command = command
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.env = env

        # Test data.
        self.metrics = {}
        self.result = None

    def execute(self, verbose=False):
        if verbose:
            note('executing: %s' % ' '.join("'%s'" % arg
                                            for arg in self.command))

        start_rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
        start_time = time.time()

        p = subprocess.Popen(self.command,
                             stdout=open(self.stdout_path, 'w'),
                             stderr=open(self.stderr_path, 'w'),
                             env=self.env)
        self.result = p.wait() == 0

        end_time = time.time()
        end_rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
        self.metrics["user_time"] = end_rusage.ru_utime - start_rusage.ru_utime
        self.metrics["sys_time"] = end_rusage.ru_stime - start_rusage.ru_stime
        self.metrics["wall_time"] = end_time - start_time

        if verbose:
            note("command executed in -- "
                 "user: %.4fs, wall: %.4fs, sys: %.4fs" % (
                    self.metrics["user_time"], self.metrics["wall_time"],
                    self.metrics["sys_time"]))

    def evaluate_filter_spec(self, spec):
        # Run the filter in an environment with the builtin filters and the
        # metrics.
        env = {"result": self.result}
        env.update(self.available_filters)
        env.update(self.metrics)
        result = eval(spec, {}, env)

        # If the result is a filter object, evaluate it.
        if isinstance(result, Command.Filter):
            result.evaluate(self)
            return

        # Otherwise, treat the result as a boolean predicate.
        self.result = bool(result)


def execute_sandboxed_test(sandbox, builder, build, args,
                           verbose=False, very_verbose=False,
                           add_path_variables=True,
                           show_command_output=False,
                           reuse_sandbox=False):

    def split_command_filters(command):
        for i, arg in enumerate(command):
            if arg[:2] != "%%" or arg[-2:] != "%%":
                break
        else:
            fatal("invalid command: %s, only contains filter "
                  "specifications" % ("".join('"%s"' % a for a in command)))

        return ([a[2:-2] for a in command[:i]],
                command[i:])

    path = build.tobasename(include_suffix=False)
    fullpath = build.tobasename()

    if verbose:
        note('testing %r' % path)

    # Create the sandbox directory, if it doesn't exist.
    is_temp = False
    if sandbox is None:
        sandbox = tempfile.mkdtemp()
        is_temp = True
    else:
        # Make absolute.
        sandbox = os.path.abspath(sandbox)
        if not os.path.exists(sandbox):
            os.mkdir(sandbox)

    # Compute paths and make sure sandbox is clean.
    root_path = os.path.join(sandbox, fullpath)
    builddir_path = os.path.join(sandbox, path)
    need_build = True
    if reuse_sandbox and (os.path.exists(root_path) and
                          os.path.exists(builddir_path)):
        need_build = False
    else:
        for p in (root_path, builddir_path):
            if os.path.exists(p):
                fatal('sandbox is not clean, %r exists' % p)

    # Fetch and extract the build.
    if need_build:
        start_time = time.time()
        llvmlab.fetch_build_to_path(builder, build, root_path, builddir_path)
        if very_verbose:
            note("extracted build in %.2fs" % (time.time() - start_time,))

    # Attempt to find clang/clang++ in the downloaded build.
    def find_binary(name):
        x = subprocess.check_output(['find', builddir_path, '-name', name])\
                    .strip().split("\n")[0]
        if x == '':
            x = None
        return x

    clang_path = find_binary('clang')
    clangpp_path = find_binary('clang++')
    liblto_path = find_binary('libLTO.dylib')
    if liblto_path is not None:
        liblto_dir = os.path.dirname(liblto_path)
    else:
        liblto_dir = None

    # Construct the interpolation variables.
    options = {'sandbox': sandbox,
               'path': builddir_path,
               'revision': build.revision,
               'build': build.build,
               'clang': clang_path,
               'clang++': clangpp_path,
               'libltodir': liblto_dir}

    # Inject environment variables.
    env = os.environ.copy()
    for key, value in options.items():
        env['TEST_%s' % key.upper()] = str(value)

    # Extend the environment to include the path to the extracted build.
    #
    # FIXME: Ideally, we would be able to read some kind of configuration
    # notermation about a builder so that we could just set this up, it doesn't
    # necessarily here as hard-coded notermation.
    if add_path_variables:
        path_extensions = []
        dyld_library_path_extensions = []
        toolchains_dir = os.path.join(builddir_path,
                                      ('Applications/Xcode.app/Contents/'
                                       'Developer/Toolchains'))
        toolchain_paths = []
        if os.path.exists(toolchains_dir):
            toolchain_paths = [os.path.join(toolchains_dir, name, 'usr')
                               for name in os.listdir(toolchains_dir)]
        for package_root in ['', 'Developer/usr/'] + toolchain_paths:
            p = os.path.join(builddir_path, package_root, 'bin')
            if os.path.exists(p):
                path_extensions.append(p)
            p = os.path.join(builddir_path, package_root, 'lib')
            if os.path.exists(p):
                dyld_library_path_extensions.append(p)
        if path_extensions:
            env['PATH'] = os.pathsep.join(
                path_extensions + [os.environ.get('PATH', '')])
        if dyld_library_path_extensions:
            env['DYLD_LIBRARY_PATH'] = os.pathsep.join(
                dyld_library_path_extensions + [
                    os.environ.get('DYLD_LIBRARY_PATH', '')])

    # Split the arguments into distinct commands.
    #
    # Extended command syntax allows running multiple commands by separating
    # them with '----'.
    test_commands = util.list_split(args, "----")

    # Split command specs into filters and commands.
    test_commands = [split_command_filters(spec) for spec in test_commands]

    # Execute the test.
    command_objects = []
    interpolated_variables = False
    for i, (filters, command) in enumerate(test_commands):
        # Interpolate arguments.
        old_command = command
        command = [a % options for a in command]
        if old_command != command:
            interpolated_variables = True

        # Create the command object...
        stdout_log_path = os.path.join(sandbox, '%s.%d.stdout' % (path, i))
        stderr_log_path = os.path.join(sandbox, '%s.%d.stderr' % (path, i))
        cmd_object = Command(command, stdout_log_path, stderr_log_path, env)
        command_objects.append(cmd_object)

        # Execute the command.
        try:
            cmd_object.execute(verbose=verbose)
        except OSError, e:
            # Python's exceptions are horribly to read, and this one is
            # incredibly common when people don't use the right syntax (or
            # misspell something) when writing a predicate. Detect this and
            # notify the user.
            if e.errno == errno.ENOENT:
                fatal("invalid command, executable doesn't exist: %r" % (
                        cmd_object.command[0],))
            elif e.errno == errno.ENOEXEC:
                fatal("invalid command, executable has a bad format. Did you "
                      "forget to put a #! at the top of a script?: %r"
                      % (cmd_object.command[0],))
            else:
                # Otherwise raise the error again.
                raise e

        # Evaluate the filters.
        for filter in filters:
            cmd_object.evaluate_filter_spec(filter)

        if show_command_output:
            for p, type in ((stdout_log_path, "stdout"),
                            (stderr_log_path, "stderr")):
                if not os.path.exists(p):
                    continue

                f = open(p)
                data = f.read()
                f.close()
                if data:
                    print ("-- command %s (note: suppressed by default, "
                           "see sandbox dir for log files) --" % (type))
                    print "--\n%s--\n" % data

        test_result = cmd_object.result
        if not test_result:
            break
    if not interpolated_variables:
        warning('no substitutions found. Fetched root ignored?')

    # Remove the temporary directory.
    if is_temp:
        if shell.execute(['rm', '-rf', sandbox]) != 0:
            note('unable to remove sandbox dir %r' % path)

    return test_result, command_objects


def get_best_match(builds, name, key=lambda x: x):
    builds = list(builds)
    builds.sort(key=key)

    if name is None and builds:
        return builds[-1]

    to_find = llvmlab.Build.frombasename(name, None)

    best = None
    for item in builds:
        build = key(item)
        # Check for a prefix match.
        path = build.tobasename()
        if path.startswith(name):
            return item

        # Check for a revision match.
        if build.revision == to_find.revision and build.revision is not None:
            return item

        # Otherwise, stop when we aren't getting closer.
        if build > to_find:
            break
        best = item

    return best


def action_fetch(name, args):
    """fetch a build from the server"""

    parser = OptionParser("""\
usage: %%prog %(name)s [options] builder [build-name]

Fetch the build from the named builder which matchs build-name. If no match is
found, get the first build before the given name. If no build name is given,
the most recent build is fetched.

The available builders can be listed using:

  %%prog ls

The available builds can be listed using:

  %%prog ls builder""" % locals())
    parser.add_option("-f", "--force", dest="force",
                      help=("always download and extract, overwriting any"
                            "existing files"),
                      action="store_true", default=False)
    parser.add_option("", "--update-link", dest="update_link", metavar="PATH",
                      help=("update a symbolic link at PATH to point to the "
                            "fetched build (on success)"),
                      action="store", default=None)
    parser.add_option("-d", "--dry-run", dest='dry_run',
                      help=("Perform all operations except the actual "
                            "downloading and extracting of any files"),
                      action="store_true", default=False)

    (opts, args) = parser.parse_args(args)

    if len(args) == 0:
        parser.error("please specify a builder name")
    elif len(args) == 1:
        builder, = args
        build_name = None
    elif len(args) == 2:
        builder, build_name = args
    else:
        parser.error("invalid number of arguments")

    builds = list(llvmlab.fetch_builds(builder))
    if not builds:
        parser.error("no builds for builder: %r" % builder)

    build = get_best_match(builds, build_name)
    if not build:
        parser.error("no match for build %r" % build_name)

    path = build.tobasename()
    if build_name is not None and not path.startswith(build_name):
        note('no exact match, fetching %r' % path)

    # Get the paths to extract to.
    root_path = path
    builddir_path = build.tobasename(include_suffix=False)

    if not opts.dry_run:
        # Check that the download and extract paths are clean.
        for p in (root_path, builddir_path):
            if os.path.exists(p):
                # If we are using --force, then clean the path.
                if opts.force:
                    shutil.rmtree(p, ignore_errors=True)
                    continue
                fatal('current directory is not clean, %r exists' % p)
        llvmlab.fetch_build_to_path(builder, build, root_path, builddir_path)

    print 'downloaded root: %s' % root_path
    print 'extracted path : %s' % builddir_path

    # Update the symbolic link, if requested.
    if not opts.dry_run and opts.update_link:
        # Remove the existing path.
        try:
            os.unlink(opts.update_link)
        except OSError as e:
            if e.errno != errno.ENOENT:
                fatal('unable to update symbolic link at %r, cannot unlink' % (
                        opts.update_link))

        # Create the symbolic link.
        os.symlink(os.path.abspath(builddir_path), opts.update_link)
        print 'updated link at: %s' % opts.update_link
    return os.path.abspath(builddir_path)


def action_ls(name, args):
    """list available build names or builds"""

    parser = OptionParser("""\
usage: %%prog %s [build-name]

With no arguments, list the available build names on 'llvmlab'. With a build
name, list the available builds for that builder.\
""" % name)

    (opts, args) = parser.parse_args(args)

    if not len(args):
        available_buildnames = llvmlab.fetch_builders()
        available_buildnames.sort()
        for item in available_buildnames:
            print item
        return available_buildnames

    for name in args:
        if len(args) > 1:
            if name is not args[0]:
                print
            print '%s:' % name
        available_builds = list(llvmlab.fetch_builds(name))
        available_builds.sort()
        available_builds.reverse()
        for build in available_builds:
            print build.tobasename(include_suffix=False)
        min_rev = min([x.revision for x in available_builds])
        max_rev = max([x.revision for x in available_builds])
        note("Summary: found {} builds: r{}-r{}".format(len(available_builds),
                                                        min_rev, max_rev))
        return available_builds

DEFAULT_BUILDER = "clang-stage1-configure-RA"


def action_bisect(name, args):
    """find first failing build using binary search"""

    parser = OptionParser("""\
usage: %%prog %(name)s [options] ... test command args ...

Look for the first published build where a test failed, using the builds on
llvmlab. The command arguments are executed once per build tested, but each
argument is first subject to string interpolation. The syntax is
"%%(VARIABLE)FORMAT" where FORMAT is a standard printf format, and VARIABLE is
one of:

  'sandbox'   - the path to the sandbox directory.
  'path'      - the path to the build under test.
  'revision'  - the revision number of the build.
  'build'     - the build number of the build under test.
  'clang'     - the path to the clang binary of the build if it exists.
  'clang++'   - the path to the clang++ binary of the build if it exists.
  'libltodir' - the path to the directory containing libLTO.dylib, if it
   exists.

Each test is run in a sandbox directory. By default, sandbox directories are
temporary directories which are created and destroyed for each test (see
--sandbox).

For use in auxiliary test scripts, each test is also run with each variable
available in the environment as TEST_<variable name> (variables are converted
to uppercase). For example, a test script could use "TEST_PATH" to find the
path to the build under test.

The stdout and stderr of the command are logged to files inside the sandbox
directory. Use an explicit sandbox directory if you would like to look at
them.

It is possible to run multiple distinct commands for each test by separating
them in the command line arguments by '----'. The failure of any command causes
the entire test to fail.\
""" % locals())

    parser.add_option("-b", "--build", dest="build_name", metavar="STR",
                      help="name of build to fetch",
                      action="store", default=DEFAULT_BUILDER)
    parser.add_option("-s", "--sandbox", dest="sandbox",
                      help="directory to use as a sandbox",
                      action="store", default=None)
    parser.add_option("-v", "--verbose", dest="verbose",
                      help="output more test notermation",
                      action="store_true", default=False)
    parser.add_option("-V", "--very-verbose", dest="very_verbose",
                      help="output even more test notermation",
                      action="store_true", default=False)
    parser.add_option("", "--show-output", dest="show_command_output",
                      help="display command output",
                      action="store_true", default=False)
    parser.add_option("", "--single-step", dest="single_step",
                      help="single step instead of binary stepping",
                      action="store_true", default=False)
    parser.add_option("", "--min-rev", dest="min_rev",
                      help="minimum revision to test",
                      type="int", action="store", default=None)
    parser.add_option("", "--max-rev", dest="max_rev",
                      help="maximum revision to test",
                      type="int", action="store", default=None)

    parser.disable_interspersed_args()

    (opts, args) = parser.parse_args(args)

    if opts.build_name is None:
        parser.error("no build name given (see --build)")

    # Very verbose implies verbose.
    opts.verbose |= opts.very_verbose

    start_time = time.time()
    available_builds = list(llvmlab.fetch_builds(opts.build_name))
    available_builds.sort()
    available_builds.reverse()
    if opts.very_verbose:
        note("fetched builds in %.2fs" % (time.time() - start_time,))

    if opts.min_rev is not None:
        available_builds = [b for b in available_builds
                            if b.revision >= opts.min_rev]
    if opts.max_rev is not None:
        available_builds = [b for b in available_builds
                            if b.revision <= opts.max_rev]

    def predicate(item):
        # Run the sandboxed test.
        test_result, _ = execute_sandboxed_test(
            opts.sandbox, opts.build_name, item, args, verbose=opts.verbose,
            very_verbose=opts.very_verbose,
            show_command_output=opts.show_command_output or opts.very_verbose)

        # Print status.
        print '%s: %s' % (('FAIL', 'PASS')[test_result],
                          item.tobasename(include_suffix=False))

        return test_result

    if opts.single_step:
        for item in available_builds:
            if predicate(item):
                break
        else:
            item = None
    else:
        if opts.min_rev is None or opts.max_rev is None:
            # Gallop to find initial search range, under the assumption that we
            # are most likely looking for something at the head of this list.
            search_space = algorithm.gallop(predicate, available_builds)
        else:
            # If both min and max revisions are specified,
            # don't gallop - bisect the given range.
            search_space = available_builds
        item = algorithm.bisect(predicate, search_space)

    if item is None:
        fatal('unable to find any passing build!')

    print '%s: first working build' % item.tobasename(include_suffix=False)
    index = available_builds.index(item)
    if index == 0:
        print 'no failing builds!?'
    else:
        print '%s: next failing build' % available_builds[index-1].tobasename(
            include_suffix=False)


def action_exec(name, args):
    """execute a command against a published root"""

    parser = OptionParser("""\
usage: %%prog %(name)s [options] ... test command args ...

Executes the given command against the latest published build. The syntax for
commands (and exit code) is exactly the same as for the 'bisect' tool, so this
command is useful for testing bisect test commands.

See 'bisect' for more notermation on the exact test syntax.\
""" % locals())

    parser.add_option("-b", "--build", dest="build_name", metavar="STR",
                      help="name of build to fetch",
                      action="store", default=DEFAULT_BUILDER)
    parser.add_option("-s", "--sandbox", dest="sandbox",
                      help="directory to use as a sandbox",
                      action="store", default=None)
    parser.add_option("", "--min-rev", dest="min_rev",
                      help="minimum revision to test",
                      type="int", action="store", default=None)
    parser.add_option("", "--max-rev", dest="max_rev",
                      help="maximum revision to test",
                      type="int", action="store", default=None)
    parser.add_option("", "--near", dest="near_build",
                      help="use a build near NAME",
                      type="str", action="store", metavar="NAME", default=None)

    parser.disable_interspersed_args()

    (opts, args) = parser.parse_args(args)

    if opts.build_name is None:
        parser.error("no build name given (see --build)")

    available_builds = list(llvmlab.fetch_builds(opts.build_name))
    available_builds.sort()
    available_builds.reverse()

    if opts.min_rev is not None:
        available_builds = [b for b in available_builds
                            if b.revision >= opts.min_rev]
    if opts.max_rev is not None:
        available_builds = [b for b in available_builds
                            if b.revision <= opts.max_rev]

    if len(available_builds) == 0:
        fatal("No builds available for builder name: %s" % opts.build_name)

    # Find the best match, if requested.
    if opts.near_build:
        build = get_best_match(available_builds, opts.near_build)
        if not build:
            parser.error("no match for build %r" % opts.near_build)
    else:
        # Otherwise, take the latest build.
        build = available_builds[0]

    test_result, _ = execute_sandboxed_test(
        opts.sandbox, opts.build_name, build, args, verbose=True,
        show_command_output=True)

    print '%s: %s' % (('FAIL', 'PASS')[test_result],
                      build.tobasename(include_suffix=False))

    raise SystemExit(test_result != True)


def action_test(name, args):
    from . import test_llvmlab
    test_llvmlab.run_tests()
