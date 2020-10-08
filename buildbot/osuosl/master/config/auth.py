from buildbot.plugins import util
#from twisted.python import log

import config


def getAuth():
    # For test local setup use NoAuth instead.
    auth = util.GitHubAuth(
        clientId=str(config.options.get('GitHub Auth', 'clientId')),
        clientSecret=str(config.options.get('GitHub Auth', 'clientSecret')),
        apiVersion=4,
        getTeamsMembership=True,
        debug=False,
    )
    return auth


def getAuthz():

    authz = util.Authz(
        allowRules=[
            # Admins can do anything.
            # defaultDeny=False: if user does not have the admin role,
            # we continue parsing rules.
            util.AnyEndpointMatcher(role="LLVM Lab team", defaultDeny=False),

            # Allow authors to stop, force or rebuild their own builds,
            util.StopBuildEndpointMatcher(role="owner", defaultDeny=False),
            # Allow bot owners to stop, force or rebuild on their own bots,
            util.StopBuildEndpointMatcher(role="worker-owner"),

            # allow devs to force or rebuild any build.
            util.RebuildBuildEndpointMatcher(role="owner", defaultDeny=False),
            util.RebuildBuildEndpointMatcher(role="worker-owner", defaultDeny=False),
            util.RebuildBuildEndpointMatcher(role="LLVM Committers"),

            util.ForceBuildEndpointMatcher(role="owner", defaultDeny=False),
            util.ForceBuildEndpointMatcher(role="worker-owner", defaultDeny=False),
            util.ForceBuildEndpointMatcher(role="LLVM Committers"),

            # Future-proof control endpoints. No parsing rules beyond this.

            # Allows anonymous to look at build results.
            util.AnyControlEndpointMatcher(role="LLVM Lab team"),
        ],
        roleMatchers=[
            util.RolesFromGroups(groupPrefix="llvm/"),
            util.RolesFromGroups(groupPrefix="llvm/"),
            # role owner is granted when property owner matches the email of the user
            util.RolesFromOwner(role="owner"),
        ],
    )

    return authz
