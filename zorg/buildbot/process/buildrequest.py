from twisted.internet import defer
import json
import sqlalchemy as sa


@defer.inlineCallbacks
def setBuildsetProperty(db, bsid, name, value, source="Collapse"):
    """Set a buildset property

    buildbot.db.buildset.BuildsetConnectorComponent only has
    getBuildsetProperties, but no setter. This setter is modelled after
    setBuildProperty.
    """
    def thd(conn):
        bs_props_tbl = db.model.buildset_properties
        db.buildsets.checkLength(bs_props_tbl.c.property_name, name)

        whereclause=sa.and_(bs_props_tbl.c.buildsetid == bsid, bs_props_tbl.c.property_name == name)
        q = sa.select([bs_props_tbl.c.property_name, bs_props_tbl.c.property_value], whereclause=whereclause)
        prop = conn.execute(q).fetchone()
        value_js = json.dumps([value,source])
        if prop is None:
            conn.execute(bs_props_tbl.insert(), {
                "buildsetid": bsid,
                "property_name": name,
                "property_value": value_js
            })
        elif prop.property_value != value_js:
            conn.execute(bs_props_tbl.update(whereclause=whereclause), {"property_value": value_js})

    yield db.pool.do(thd)

    # Also update the lookup cache, if this buidset properties' has been cached.
    if bsid in db.buildsets. getBuildsetProperties.cache.keys():
        # Lookup of old values will be from the cache
        properties = yield db.buildsets.getBuildsetProperties(bsid)

        # Update the property value and store back to cache
        properties[name] = (value,source)
        db.buildsets.getBuildsetProperties.cache.put(bsid, properties)



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


    # Requests can be collapsed regardless of clean property, but remember
    # whether a collapsed buildrequest should be clean.
    anyClean = selfBuildsetPoperties.get("clean") or otherBuildsetPoperties.get("clean")
    selfBuildsetPoperties.pop('clean', None)
    otherBuildsetPoperties.pop('clean', None)

    anyCleanObj = selfBuildsetPoperties.get("clean_obj") or otherBuildsetPoperties.get("clean_obj")
    selfBuildsetPoperties.pop('clean_obj', None)
    otherBuildsetPoperties.pop('clean_obj', None)

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
    if req1.get('reason', None) != req2.get('reason', None):
        return False

    # We decided to collapse the requests. One request will be marked 'SKIPPED',
    # the other used to subsume both. If at least one of them requires a clean
    # build, mark the subsuming request as such. Since we don't know which one
    # it is, mark both.
    if anyClean:
        yield setBuildsetProperty(master.db, req1['buildsetid'], 'clean', True)
        yield setBuildsetProperty(master.db, req2['buildsetid'], 'clean', True)

    if anyCleanObj:
        yield setBuildsetProperty(master.db, req1['buildsetid'], 'clean_obj', True)
        yield setBuildsetProperty(master.db, req2['buildsetid'], 'clean_obj', True)

    return True
