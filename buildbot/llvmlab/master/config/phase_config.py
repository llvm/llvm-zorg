"""
Declarative definition of the CI phase organization
"""

def builder(name, category, slaves):
    return { 'name' : name,
             'category' : category,
             'slaves' : slaves }

def build(name, slaves):
    return builder(name, 'build-public', slaves)
def test(name, slaves):
    return builder(name, 'test-public', slaves)
def experimental(name, slaves):
    return builder(name, 'experimental', slaves)

# FIXME: Eliminate description from builder name?
phases = []
phaseRunners = ['macpro1']
# if any darwin11 slaves stop working, remember to fix the authorization settings
# so that gdb will work properly by adding to group procmod with:
# sudo dscl localhost -append /Local/Default/Groups/procmod GroupMembership [username]
# also make sure the slave is runninf with an effective group of procmod in the
# LauchDaemon plist

phase1_slaves=['xserve5']
phase1_builders = []

phase1_builders.append(build('clang-x86_64-darwin11-nobootstrap-RAincremental', phase1_slaves))

phases.append(
    { 'number' : 1,
      'name' : 'sanity',
      'title' : 'Sanity',
      'builders' : phase1_builders,
      'description' : """\

The first phase is responsible for quickly testing that tree is sane -- namely
that it can be built and that the basic tests are passing. The purpose of this
phase is to make sure the tree is in good enough condition that most developers
can get work done, and that it is worth doing further testing.

This phase is also responsible for building the initial Stage 1 compilers which
will be used to boot strap subsequent builds.

The first phase is targeted to run on almost every commit and to react within at
most 10 to 15 minutes to failures.""" })

phase2_slaves=['xserve4']
phase2_builders = []

phase2_builders.append(build('clang-x86_64-darwin11-DA', phase2_slaves))
phase2_builders.append(build('clang-x86_64-darwin11-RA', phase2_slaves))

phases.append(
    { 'number' : 2,
      'name' : 'living',
      'title' : 'Living On',
      'builders' : phase2_builders,
      'description' : """\
The second phase is designed to test that the compiler is basically functional
and that it is suitable for living on. This means that almost all developers can
get their work done using sources which have passed this phase.

This phase produces the majority of the compilers which are used in subsequent
testing.

The second phase is targeted to run on most commits and to react within at most
15 to 30 minutes to failures.""" })

###

# Phase 3

phase3_slaves = ['xserve4']
phase3_slaves_lto = ['xserve3']
phase3_builders = []

# Add an i386 build.
phase3_builders.append(build('clang-i386-darwin11-RA', phase3_slaves))

# Add a release (no asserts) build.
phase3_builders.append(build('clang-x86_64-darwin11-R', phase3_slaves))

# Add an lto release build.
phase3_builders.append(build('clang-x86_64-darwin11-Rlto', phase3_slaves_lto))

phases.append(
    { 'number' : 3,
      'name' : 'tree health',
      'title' : 'Tree Health',
      'builders' : phase3_builders,
      'description' : """\
The third phase is designed to check the general health of the tree across a
variety of targets and build environments. In general, all developers should be
able to work using sources which have passed this phase, and the tree should be
good enough for many users.

The third phase is targeted to react within at most 1 to 2 hours.""" })
