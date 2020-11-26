from twisted.internet import defer

@defer.inlineCallbacks
def collapseRequests(master, builder, req1, req2):
    """
    Returns true if both buildrequest can be merged, via Deferred.

    This implements Zorg's default collapse strategy.
    """
    # If these are for the same buildset, collapse away.
    if req1['buildsetid'] == req2['buildsetid']:
        return True

    # Check properties and do not collapse if properties do not match.
    if req1.get('properties', None) != req2.get('properties', None):
        return False

    # Get the buidlsets for each buildrequest.
    selfBuildsets = yield master.data.get(
        ('buildsets', str(req1['buildsetid'])))
    otherBuildsets = yield master.data.get(
        ('buildsets', str(req2['buildsetid'])))

    # Fetch the buildset properties.
    selfBuildsetPoperties = yield \
        master.db.buildsets.getBuildsetProperties(
            str(req1['buildsetid'])
        )
    otherBuildsetPoperties = yield \
        master.db.buildsets.getBuildsetProperties(
            str(req2['buildsetid'])
        )

    # Check buildsets properties and do not collapse
    # if properties do not match. This includes the check
    # for different schedulers.
    if selfBuildsetPoperties != otherBuildsetPoperties:
        return False

    # Extract sourcestamps, as dictionaries by codebase.
    selfSources = dict((ss['codebase'], ss)
                        for ss in selfBuildsets['sourcestamps'])
    otherSources = dict((ss['codebase'], ss)
                        for ss in otherBuildsets['sourcestamps'])

    # If the sets of codebases do not match, we can't collapse.
    if set(selfSources) != set(otherSources):
        return False

    for c, selfSS in selfSources.items():
        otherSS = otherSources[c]
        if selfSS['repository'] != otherSS['repository']:
            return False

        if selfSS['branch'] != otherSS['branch']:
            return False

        # TODO: Handle projects matching if we ever would have
        # a mix of projects from the monorepo and outside of
        # the monorepo. For now, we consider all of them being
        # a part of the monorepo, so all of them are compatible
        # and could be collapsed.

        # Anything with a patch won't be collapsed.
        if selfSS['patch'] or otherSS['patch']:
            return False

        # Get changes & compare.
        selfChanges = yield master.data.get(('sourcestamps', selfSS['ssid'], 'changes'))
        otherChanges = yield master.data.get(('sourcestamps', otherSS['ssid'], 'changes'))
        # If both have changes - proceed, else fail.
        # If no changes - check revision instead.
        if selfChanges and otherChanges:
            continue

        if selfChanges and not otherChanges:
            return False

        if not selfChanges and otherChanges:
            return False

        # Else check revisions.
        if selfSS['revision'] != otherSS['revision']:
            return False

    # Build requests with different reasons should be built separately.
    if req1.get('reason', None) == req2.get('reason', None):
        return True
    else:
        return False
