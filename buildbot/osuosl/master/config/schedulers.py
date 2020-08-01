from twisted.python import log

from buildbot.schedulers.filter import ChangeFilter
from buildbot.schedulers.basic import SingleBranchScheduler

def getProjectsToFilter(projects):
    # Here we could have "clang" project. In this case replace it by "cfe".
    return [ p if p != "clang" else "cfe" for p in projects ]

# Since we have many parametric builders, we dynamically build the minimum set
# of schedulers, which covers all actually used combinations of dependencies.
def getSingleBranchSchedulers(
    builders,
    explicitly_set_schedulers = None,
    **kwargs):
    """
    I'm taking over all of not yet assigned builders with the
    declared source code dependencies, and automatically generate
    a minimum set of SingleBranchSchedulers to handle all the declared
    source code dependency combinations.
    """

    builders_with_explicit_schedulers = set()
    if explicitly_set_schedulers:
        # TODO: Make a list of builder names with already set schedulers.
        # builders_with_explicit_schedulers.add(builder)
        pass

    # For the builders created with LLVMBuildFactory or similar,
    # we always use automatic schedulers,
    # unless schedulers already explicitly set.
    builders_with_automatic_schedulers = [
        builder for builder in builders
        if builder['name'] not in builders_with_explicit_schedulers
        if getattr(builder['factory'], 'depends_on_projects', None)
    ]

    return _getSingleBranchAutomaticSchedulers(
                builders_with_automatic_schedulers,
                filter_branch='master',     # git monorepo branch.
                treeStableTimer=kwargs.get('treeStableTimer', None))

def _getSingleBranchAutomaticSchedulers(
        builders_with_automatic_schedulers,
        filter_branch,
        treeStableTimer):

    automatic_schedulers = []

    # Do we have any to take care of?
    if builders_with_automatic_schedulers:
        # Let's reconsile first to get a unique set of dependencies.
        # We need a set of unique sets of dependent projects.
        set_of_dependencies = set([
            frozenset(getattr(b['factory'], 'depends_on_projects'))
            for b in builders_with_automatic_schedulers
        ])

        for projects in set_of_dependencies:
            sch_builders = [
                b['name']
                for b in builders_with_automatic_schedulers
                if frozenset(getattr(b['factory'], 'depends_on_projects')) == projects
            ]

            automatic_scheduler_name =  filter_branch + ":" + ",".join(sorted(projects))
            projects_to_filter = getProjectsToFilter(projects)

            automatic_schedulers.append(
                SingleBranchScheduler(
                    name=automatic_scheduler_name,
                    treeStableTimer=treeStableTimer,
                    builderNames=sch_builders,
                    change_filter=ChangeFilter(project=projects_to_filter, branch=filter_branch)
                )
            )

            log.msg(
                "Generated SingleBranchScheduler: { name='%s'" % automatic_scheduler_name,
                ", builderNames=", sch_builders,
                ", change_filter=", projects_to_filter, " (branch: %s)" % filter_branch,
                ", treeStableTimer=%s" % treeStableTimer,
                "}")
    return automatic_schedulers
