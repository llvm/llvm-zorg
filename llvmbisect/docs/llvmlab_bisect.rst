.. _llvmlab-bisect:

Automatic compiler bisecting with llvmlab bisect
==================================================

``llvmlab bisect`` is a tool for automatically identifying
when a regression was introduced in any build of Clang, or LLVM
produced by one of our Buildbots or Jenkins jobs.

The basics of the tool are very simple, you must provide it with a "test case"
which will reproduce the problem you are seeing. Once you have done that, the
tool will automatically download compiler packages from the cloud
(typically produced by our continuous integration system) and will check whether
the problem reproduces with that compiler or not. The tool will then attempt to
narrow down on the first compiler which broke the test, and will report the last
compiler which worked and the first compiler that failed.

Getting the tool
~~~~~~~~~~~~~~~~

The tool is in our tools repo::

  $ svn checkout https://llvm.org/svn/llvm-project/zorg/trunk/ zorg
  $ cd zorg/llvmbisect
  $ sudo python setup.py install
  $ llvmlab ls

If you prefer a non-sudo install, replace ``sudo python setup.py install`` step
with::

  $ LOCAL_PYTHON_INSTALL_PATH=$(pwd)/local_python_packages/lib/python2.7/site-packages/
  $ mkdir -p $LOCAL_PYTHON_INSTALL_PATH
  $ export PYTHONPATH=$LOCAL_PYTHON_INSTALL_PATH:$PYTHONPATH
  $ python setup.py install --prefix=$(pwd)/local_python_packages
  $ export PATH=$(pwd)/bin:$PATH

Note that you should export ``PYTHONPATH`` and ``PATH`` to use ``llvmlab``.

The Bisection Process
~~~~~~~~~~~~~~~~~~~~~

There are several parts of the bisection process you should understand to use
``llvmlab bisect`` effectively:

 * How the tool gets compiler builds.

 * How tests (bisection predicates) are run.

 * How the bisect process sandboxes tests.

 * Test filters.

Compiler Packages
+++++++++++++++++

Bisection uses packages produced by the continuous integration
system. Currently, it will only consider packages which are produced by one
particular "builder". The default is to use the ``clang-stage1-configure-RA_build``
line of packages, because that is produced by our mini farm and has a very high
granularity and a long history.

You can tell the tool to use a particular line of builds using the ``-b`` or
``--build`` command line option.

You can see a list of the kinds of builds which are published using::

  $ ./llvmlab ls
  clang-stage1-configure-RA_build
  clang-stage2-foo

Each of these corresponds to a particular buildbot/Jenkins builder
which is constantly building new revisions and uploading them to
the cloud.

The important thing to understand is that the particular compiler package in use
may impact your test. For example, ``clang-stage1-configure-RA_build`` builds 
are x86_64 compilers built on Yosemite in release asserts mode.  Generally, you
should make sure your test explicitly sets anything which could impact the test 
(like the architecture).

The other way this impacts your tests is that some packages are laid out
differently than others. Most compiler packages are laid out in a "Unix" style,
with ``bin`` and ``lib`` subdirectories. One easy way to see the package layout
is to use ``llvmlab fetch`` to grab a build from the particular builder you
are using and poke at it. For example::

  $ llvmlab fetch clang-i386-darwin9-snt 
  downloaded root: clang-r128299-b6960.tgz
  extracted path : 
  $ ls clang-r128299-b6960
  bin	docs	lib	share
  
See ``llvmlab fetch --help`` for more information on the ``fetch`` tool.

The main exception to remember is that Apple style builds generally will have
"root" style layouts, where the package is meant to be installed directly into
``/``, and will be laid out with ``usr/bin`` and ``Developer/usr/bin``
subdirectories.


The Build Cache
+++++++++++++++

``llvmlab bisect`` can be configured to cache downloaded archives. This is
useful for users who frequently bisect things and want the command to run as 
fast as possible. Note that the tool doesn't try and do anything smart about
minimizing the amount of disk space the cache uses, so use this at your own
risk.

To enable the cache::
  $ mkdir -p ~/.llvmlab
  $ echo "[ci]" > ~/.llvmlab/config
  $ echo "cache_builds = True" > ~/.llvmlab/config


Bisection Predicates
++++++++++++++++++++

Like most bisection tools, ``llvmlab bisect`` needs to have a way to test
whether a particular build "passes" or "fails". ``llvmlab bisect`` uses a
format which allows writing most bisection commands on a single command line
without having to write extra shell scripts.

``llvmlab ci exec`` is an invaluable tool for checking bisection
predicates. It accepts the exact same syntax as llvmlab bisect, but prints a
bit more information by default and only runs a single command. This is useful
for vetting bisection predicates before running a full bisection process.

Predicates are written as commands which are expected to exit successfully
(i.e., return 0 as the exit code) when the test succeeds
[#predicate_tense]_. The command will be run once for each downloaded package to
determine if the test passes or fails on that particular build.

``llvmlab bisect`` treats all non-optional command line arguments as the
command to be run. Each argument will be rewritten to possibly substitute
variables, and then the entire command line will be run (i.e., ``exec()``'d) to
determine whether the test passes or fails.

.. _string: http://docs.python.org/library/stdtypes.html#string-formatting

Bisection downloads each package into a separate directory inside a sandbox and
provides a mechanism for substituting the path to package into the command to be
run. Variables are substituted using the Python syntax with string_ formatting
named keys. For the most part, the syntax is like ``printf`` but variable names
are written in parentheses before the format specifier [#sh_parens]_.

The most important variable is "path", which will be set to the path to the
downloaded package. For example::

  %(path)s/bin/clang

would typically be expanded to something like::

  .../<sandbox>/clang-r128289-b6957/bin/clang 

before the command is run. You can use the ``-v`` (``--verbose``) command line
option to have ``llvmlab bisect`` print the command lines it is running after
substitution.

The tool provides a few other variables but "path" is the only one needed for
all but the rarest bisections. You can see the others in ``llvmlab bisect
--help``.

The tool optimizes for the situation where downloaded packages include command
line executable which are going to be used in the tests, by automatically
extending the PATH and DYLD_LIBRARY_PATH variables to point into the downloaded
build directory whenever it sees that the downloaded package has ``bin`` or
``lib`` directories (the tool will also look for ``/Developer/usr/...``
directories). This environment extensions mean that it is usually possible to
write simple test commands without requiring any substitutions.

For some bisection scenarios, it is easier to write a test script than to try
and come up with a single predicate command. For these scenarioes, ``llvmlab
bisect`` also makes all of the substitution variables available in the command's
environment. Each variable is injected into the environment as
``TEST_<variable>``. As an example, the following script could be used as a test
predicate which just checks that the compile succeeds::

  #!/bin/sh
  
  $TEST_PATH/bin/clang -c t.c

Even though llvmlab bisect itself will only run one individual command per
build, you can write arbitrarily complicated test predicates by either (a)
writing external test scripts, or (b) writing shell "one-liners" and using
``/bin/sh -c`` to execute them. For example, the following bisect will test that
a particular source file both compiles and executes successfully::

  llvmlab bisect /bin/sh -c '%(path)s/bin/clang t.c && ./a.out'

llvmlab bisect also supports a shortcut for this particular pattern. Separate
test commands can be separated on the command by a literal "----" command line
argument. Each command will be substituted as usual, but will they will be run
separately in order and if any command fails the entire test will fail.

.. [#predicate_tense] Note that ``llvmlab bisect`` always looks for the latest
                      build where a predicate *passes*. This means that it
                      generally expects the predicate to fail on any recent
                      build. If you are used to using tools like ``delta`` you
                      may be used to the predicate having the opposite tense --
                      however, for regression analysis usually one is
                      investigating a failure, and so one expects the test to
                      currently fail.

.. [#sh_parens] Most shells will assign a syntax to (foo) so you generally have
                to quote arguments which require substitution. One day I'll
                think of a clever way I like to commands even easier to
                write. Until then, quote away!


The Bisection Sandbox
+++++++++++++++++++++

``llvmlab bisect`` tries to be very lightweight and not modify your working
directory or leave stray files around unless asked to. For that reason, it
downloads all of the packages and runs all of the tests inside a sandbox. By
default, the tool uses a sandbox inside ``/tmp`` and will destroy the sandbox
when it is done running tests.

The tool also tries to be quiet and minimize command output, so the output of
each individual test run is also stored inside the sandbox. Unfortunately, this
means when the sandbox is destroyed you will no longer have access to the log
files if you think the predicate was not working correctly.

For long running or complicated bisects, it is recommended to use the ``-s`` or
``--sandbox`` to tell the tool where to put the sandbox. If this option is used,
the sandbox will not be destroyed and you can investigate the log files for each
predicate run and the downloaded packages at your leisure.

Predicates commands themselves are **NOT** run inside the sandbox, they are
always run in the current working directory. This is useful for referring to
test input files, but may be a problem if you wish to store the outputs of each
individual test run (for example, to analyze later). For that case, one method
is to store the test outputs inside the download package directories. The
following example will store each generated executable inside the build
directory for testing later::

  llvmlab bisect /bin/sh -c '%(path)s/bin/clang t.c -o %(path)s/foo && %(path)s/foo'


Environment Extensions
++++++++++++++++++++++

``llvmlab bisect`` tries to optimize for the common case where build product
have executables or libraries to test, by automatically extending the ``PATH``
and ``DYLD_LIBRARY_PATH`` variables when it recognizes that the build package
has ``bin`` or ``lib`` subdirectories.

For almost all common bisection tasks, this makes it possible to run the tool
without having to explicitly specify the substitution variables.

For example::

  llvmlab bisect '%(path)s/bin/clang' -c t.c

could just be written as::

  llvmlab bisect clang -c t.c

because the ``clang`` binary in the downloaded package will be found first in
the environment lookup.


Test Filters
++++++++++++

For more advanced uses, llvmlab bisect has a syntax for specifying "filters"
on individual commands. The syntax for filters is that they should be specified
at the start of the command using arguments like "%%<filter expression>%%".

The filters are used as a way to specify additional parameters which only apply
to particular test commands. The expressions themselves are just Python
expressions which should evaluate to a boolean result, which becomes the result
of the test.

The Python expressions are evaluate in an environment which contains the
following predefined variables:

``result``

  The current boolean result of the test predicate (that is, true if the test is
  "passing"). This may have been modified by preceeding filters.

``user_time``, ``sys_time``, ``wall_time``

  The user, system, and wall time the command took to execute, respectively.

These variables can be used to easily construct predicates which fail based on
more complex criterion. For example, here is a filter to look for the latest
build where the compiler succeeds in less than .5 seconds::

  llvmlab bisect "%% result and user_time < .5 %%" clang -c t.c


Using ``llvmlab bisect``
~~~~~~~~~~~~~~~~~~~~~~~~~~

``llvmlab bisect`` is very flexible but takes some getting used to. The
following section has example bisection commands for many common scenarios.

Compiler Crashes
++++++++++++++++

This is the simplest case, a bisection for a compiler crash or assertion failure
usually looks like::

  $ llvmlab bisect '%(path)s'/bin/clang -c t.c ... compiler flags ...

because when the compiler crashes it will have a non-zero exit code. *For
bisecting assertion failures, you should make sure the build being tested has
assertions compiled in!*

Suppose you are investigating a crash which has been fixed, and you want to know
where. Just use the LLVM ``not`` tool to reverse the test:

  $ llvmlab bisect not '%(path)s'/bin/clang -c t.c ... compiler flags ...

By looking for the latest build where ``not clang ...`` *passes* we are
effectively looking for the latest broken build. The next build will generally
be the one which fixed the problem.


Miscompiles
+++++++++++

Miscompiles usually involve compiling and running the output.

The simplest scenario is when the program crashes when run. In that case the
simplest method is to use the ``/bin/sh -c "... arguments ..."`` trick to
combine the compile and execute steps into one command line::

  $ llvmlab bisect /bin/sh -c '%(path)s/bin/clang t.c && ./a.out'

Note that because we are already quoting the shell command, we can just move the
quotes around the entire line and not worry about quoting individual arguments
(unless they have spaces!).

A more complex scenario is when the program runs but has bad output. Usually
this just means you need to grep the output for correct output. For example, to
bisect a program which is supposed to print "OK" (but isn't currently) we could
use::

  $ llvmlab bisect /bin/sh -c '%(path)s/bin/clang t.c && ./a.out | grep "OK"'

Beware the pitfalls of exit codes and pipes, and use temporary files if you
aren't sure of what you are doing!


Overlapped Failures
+++++++++++++++++++

If you are used to using a test case reduction tool like ``delta`` or
``bugpoint``, you are probably familiar with the problem of running the tool for
hours, only to find that it found a very nice test case for a different problem
than what you were looking for.

The same problem happens when bisecting a program which was previously broken
for a different reason. If you run the tool but the results don't seem to make
sense, I recommend saving the sandbox (e.g., ``llvmlab bisect -s /tmp/foo
...``) and investigating the log files to make sure bisection looked for the
problem you are interested in. If it didn't, usually you should make your
predicate more precise, for example by using ``grep`` to search the output for a
more precise failure message (like an assertion failure string).


Infinite Loops
++++++++++++++

On occasion, you will want to bisect something that infinite loops or takes
much longer than usual. This is a problem because you usually don't want to wait
for a long time (or infinity) for the predicate to complete.

One simple trick which can work is to use the ``ulimit`` command to set a time
limit. The following command will look for the latest build where the compiler
runs in less than 10 seconds on the given input::

  $ llvmlab bisect /bin/sh -c 'ulimit -t 10; %(path)s/bin/clang -c t.c'


Performance Regressions
+++++++++++++++++++++++

Bisecting performance regressions is done most easily using the filter
expressions. Usually you would start by determining what an approximate upper
bound on the expected time of the command is. Then, use a ``max_time`` filter
with that time to cause any test running longer than that to fail.

For example, the following example shows a real bisection of a performance
regression on the ``telecom-gsm`` benchmark::

  llvmlab bisect \
    '%(path)s/bin/clang' -o telecomm-gsm.exe -w -arch x86_64 -O3 \
        ~/llvm-test-suite/MultiSource/Benchmarks/MiBench/telecomm-gsm/*.c \
        -lm -DSTUPID_COMPILER -DNeedFunctionPrototypes=1 -DSASR \
    ---- \
    "%% user_time < 0.25 %%" ./telecomm-gsm.exe -fps -c \
        ~/llvm-test-suite/MultiSource/Benchmarks/MiBench/telecomm-gsm/large.au


Nightly Test Failures
+++++++++++++++++++++

If you are bisecting a nightly test failure, it commonly helps to leverage the
existing nightly test Makefiles rather than try to write your own step to build
or test an executable against the expected output. In particular, the Makefiles
generate report files which say whether the test passed or failed.

For example, if you are using LNT to run your nightly tests, then the top line
the ``test.log`` file shows the exact command used to run the tests. You can
always rerun this command in any subdirectory. For example, here is an example
from an i386 Clang run::

  2010-10-12 08:54:39: running: "make" "-k" "-j" "1" "report" "report.simple.csv" \
      "TARGET_LLVMGCC=/Users/ddunbar/llvm.ref/2010-10-12_00-01.install/bin/clang" \
      "CC_UNDER_TEST_TARGET_IS_I386=1" "ENABLE_HASHED_PROGRAM_OUTPUT=1" "TARGET_CXX=None" \
      "LLI_OPTFLAGS=-O0" "TARGET_CC=None" \
      "TARGET_LLVMGXX=/Users/ddunbar/llvm.ref/2010-10-12_00-01.install/bin/clang++" \
      "TEST=simple" "CC_UNDER_TEST_IS_CLANG=1" "TARGET_LLCFLAGS=" "TARGET_FLAGS=-g -arch i386" \
      "USE_REFERENCE_OUTPUT=1" "OPTFLAGS=-O0" "SMALL_PROBLEM_SIZE=1" "LLC_OPTFLAGS=-O0" \
      "ENABLE_OPTIMIZED=1" "ARCH=x86" "DISABLE_CBE=1" "DISABLE_JIT=1"

Suppose we wanted to bisect a test failure on something complicated, like
``254.gap``. The "easiest" thing to do is:

 #. Replace the compiler paths with "%(path)s" so that we use the right compiler to test.

 #. Change into the test directory, in this case ``External/SPEC/CINT2000/254.gap``.

 #. Each test produces a ``<test name>.simple.execute.report.txt`` text file which will have a line that looks like::

      TEST-FAIL: exec /Users/ddunbar/nt/clang.i386.O0.g/test-2011-03-25_06-35-35/External/SPEC/CINT2000/254.gap/254.gap

    because the tests are make driven, we can tell make to only build this
    file. In SingleSource directories, this would make sure we don't run any
    tests we don't need to.

    In this case, replace the "report" and "report.simple.csv" make targest on
    the command line with "Output/254.gap.simple.exec.txt".

 #. Make sure your test predicate removes the Output directory and any ``report...`` files (if
    you forget this, you won't end up rebuilding the test with the right compiler).

 #. Add a grep for "TEST-PASS" of the report file.

An example of what the final bisect command might look like::

  $ llvmlab bisect /bin/sh -c \
      'rm -rf report.* Output && \
       "make" "-k" "-j" "1" "Output/254.gap.simple.exec.txt" \
           "TARGET_LLVMGCC=%(path)s/bin/clang" \
           "CC_UNDER_TEST_TARGET_IS_I386=1" "ENABLE_HASHED_PROGRAM_OUTPUT=1" "TARGET_CXX=None" \
           "LLI_OPTFLAGS=-O0" "TARGET_CC=None" \
           "TARGET_LLVMGXX=%(path)s/bin/clang++" \
           "TEST=simple" "CC_UNDER_TEST_IS_CLANG=1" "TARGET_LLCFLAGS=" "TARGET_FLAGS=-g -arch i386" \
           "USE_REFERENCE_OUTPUT=1" "OPTFLAGS=-O0" "SMALL_PROBLEM_SIZE=1" "LLC_OPTFLAGS=-O0" \
           "ENABLE_OPTIMIZED=1" "ARCH=x86" "DISABLE_CBE=1" "DISABLE_JIT=1" && \
       grep "TEST-PASS" "Output/254.gap.simple.exec.txt"'


Nightly Test Performance Regressions
++++++++++++++++++++++++++++++++++++

This is similar to the problem of bisecting nightly test above, but made more
complicated because the test predicate needs to do a comparison on the
performance result.

One way to do this is to extract a script which reproduces the performance
regression, and use a filter expression as described previously. However, this
requires extracting the exact commands which are run by the ``test-suite``
Makefiles.

A simpler way is to use the ``test-suite/tools/get-report-time`` script in
conjunction with a standard Unix command line tool like ``expr`` to do the
performance comparison.

The basic process is similar to the one above, the differences are that instead
of just using ``grep`` to check the output, we use the ``get-report-time`` tool
and a quick script using ``bc`` to compare the result. Here is an example::

  $ llvmlab bisect -s sandbox /bin/sh -c \
      'set -ex; \
       rm -rf Output && \
       "make" "-k" "-j" "1" "Output/security-rijndael.simple.compile.report.txt" \
           "TARGET_LLVMGCC=%(path)s/bin/clang" "ENABLE_HASHED_PROGRAM_OUTPUT=1" "TARGET_CXX=None" \
           "LLI_OPTFLAGS=-O0" "TARGET_CC=None" \
           "TARGET_LLVMGXX=%(path)s/bin/clang++" \
           "TEST=simple" "CC_UNDER_TEST_IS_CLANG=1" "ENABLE_PARALLEL_REPORT=1" "TARGET_FLAGS=-g" \
           "USE_REFERENCE_OUTPUT=1" "CC_UNDER_TEST_TARGET_IS_X86_64=1" "OPTFLAGS=-O0" \
           "LLC_OPTFLAGS=-O0" "ENABLE_OPTIMIZED=1" "ARCH=x86_64" "DISABLE_CBE=1" "DISABLE_JIT=1" && \
       ./check-value.sh'

Where ``check-value.sh`` looks like this::

      #!/bin/sh -x

      cmd1=`/Volumes/Data/sources/llvm/projects/test-suite/tools/get-report-time \
      		Output/security-rijndael.simple.compile.report.txt`
      cmd2=`echo "$cmd1 < 0.42" | bc -l`

      if [ $cmd2 == '1' ]; then
        exit 0
      fi

      exit 1

Another trick this particular example uses is using the bash ``set -x`` command
to log the commands which get run. In this case, this allows us to inspect the
log files in the ``sandbox`` directory and see what the time used in the
``expr`` comparison was. This is handy in case we aren't exactly sure if the
comparison time we used is correct.


Tests With Interactive Steps
++++++++++++++++++++++++++++

Sometimes test predicates require some steps that must be performed
interactively or are too hard to automate in a test script.

In such cases its still possible to use llvmlab bisect by writing the test
script in such a way that it will wait for the user to inform it whether the
test passed or failed. For example, here is a real test script that was used to
bisect where I was running a GUI app to check for distorted colors as part of
the test step.

After each step, the GUI app would be launched, I would check the colors, and
then type in "yes" or "no" based on whether the app worked or not. Note that
because llvmlab bisect hides the test output by default, the prompt itself
doesn't show up, but the command still can read stdin.

Here is the test script::

  #!/bin/sh

  git reset --hard
  
  CC=clang
  COMPILE HERE  
  sudo ditto built_files/ /
  
  open /Applications/GUIApp
  
  while true; do
      read -p "OK?" is_ok
      if [ "$is_ok" == "yes" ]; then
          echo "OK!"
          exit 0
      elif [ "$is_ok" == "no" ]; then
          echo "FAILED!"
          exit 1
      else
          echo "Answer yes or no you!";
      fi
  done
  
And here is log showing the transcript of the bisect::

  bash-3.2# ~admin/zorg/utils/llvmlab bisect --max-rev 131837 ./test.sh
  no
  FAIL: clang-r131837-b8165
  no
  FAIL: clang-r131835-b8164
  no
  FAIL: clang-r131832-b8162
  no
  FAIL: clang-r131828-b8158
  yes
  PASS: clang-r131795-b8146
  no
  FAIL: clang-r131809-b8151
  no
  FAIL: clang-r131806-b8149
  no
  FAIL: clang-r131801-b8147
  clang-r131795-b8146: first working build
  clang-r131801-b8147: next failing build
  
Note that it is very easy to make a mistake and type the wrong answer when
following this process, in which case the bisect will come up with the wrong
answer. It's always worth sanity checking the results (e.g., using ``llvmlab
ci exec``) after the bisect is complete.
