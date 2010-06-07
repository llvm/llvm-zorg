"""
Classes for caching metadata about a PerfDB instance.
"""

from lnt.viewer.PerfDB import RunInfo

class SuiteSummary:
    def __init__(self, name, path):
        self.name = name
        self.path = path

class PerfDBSummary:
    @staticmethod
    def fromdb(db):
        revision = db.get_revision_number("Run")

        # Look for all the run tags and use them to identify the available
        # suites.
        q = db.session.query(RunInfo.value.distinct())
        q = q.filter(RunInfo.key == "tag")

        suites = [SuiteSummary("Nightlytest", ("nightlytest",))]
        for tag, in q:
            if tag == 'nightlytest':
                continue
            suites.append(SuiteSummary(tag, ("simple",tag)))

        suites.sort(key=lambda s: s.name)
        return PerfDBSummary(revision, suites)

    def __init__(self, revision, suites):
        self.revision = revision
        self.suites = suites

    def is_up_to_date(self, db):
        return self.revision == db.get_revision("Run")
