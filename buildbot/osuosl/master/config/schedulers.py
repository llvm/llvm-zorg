from twisted.python import log

from buildbot.schedulers.filter import ChangeFilter
from buildbot.schedulers.basic import SingleBranchScheduler

def getProjectsToFilter(projects):
    # Here we could have "clang" project. In this case replace it by "cfe".
    return [ p if p != "clang" else "cfe" for p in projects ]

# Since we have many parametric builders, we dynamically build the minimum set
# of schedulers, which covers all actually used combinations of dependencies.
def getSingleBranchSchedulers(builders, schedulers, **kwargs):
    """
    I'm taking over all of not yet assigned builders with the
    declared source code dependencies, and automatically generate
    a minimum set of SingleBranchSchedulers to handle all the declared
    source code dependency combinations.
    """

    # Prepare a list of builders which already have been assigned to schedulers.
    builders_with_schedulers = {
        b for s in schedulers for b in s.builderNames
    }

    builders_with_automatic_schedulers = []
    for builder in builders:
        # Only for the builders created with LLVMBuildFactory or similar.
        if getattr(builder['factory'], 'depends_on_projects', None):
            # And only if this builder does not yet have an assigned scheduler.
            if builder['name'] not in builders_with_schedulers:
                # This builder is a candidate for an automatic scheduler.
                builders_with_automatic_schedulers.append(builder)

    automatic_schedulers = []
    # Do we have any to take care of?
    if builders_with_automatic_schedulers:
        # Let's reconsile first to get a unique set of dependencies.
        # We need a set of unique sets of dependent projects.
        set_of_dependencies = set([
            frozenset(getattr(b['factory'], 'depends_on_projects'))
            for b in builders_with_automatic_schedulers
        ])

        treeStableTimer = kwargs.get('treeStableTimer', 2*60)
        automatic_schedulers = []
        for projects in set_of_dependencies:
            sch_builders = [
                b['name']
                for b in builders_with_automatic_schedulers
                if frozenset(getattr(b['factory'], 'depends_on_projects')) == projects
            ]

            automatic_scheduler_name = ",".join(sorted(projects))
            projects_to_filter = getProjectsToFilter(projects)

            automatic_schedulers.append(
                SingleBranchScheduler(
                    name=automatic_scheduler_name,
                    treeStableTimer=treeStableTimer,
                    builderNames=sch_builders,
                    change_filter=ChangeFilter(project=projects_to_filter)
                )
            )

            log.msg(
                "Generated SingleBranchScheduler: { name='%s'" % automatic_scheduler_name,
                ", builderNames=", sch_builders,
                ", change_filter=", projects_to_filter,
                "}")
    return automatic_schedulers
