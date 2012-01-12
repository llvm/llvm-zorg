"""
Database models for the TestSuite databases themselves.

These are a bit magical because the models themselves are driven by the test
suite metadata, so we only create the classes at runtime.
"""

import datetime
import json

import sqlalchemy
from sqlalchemy import *

import testsuite

class TestSuiteDB(object):
    """
    Wrapper object for an individual test suites database tables.

    This wrapper is somewhat special in that it handles specializing the
    metatable instances for the given test suite.

    Clients are expected to only access the test suite database tables by going
    through the model classes constructed by this wrapper object.
    """

    def __init__(self, v4db, name, test_suite):
        testsuitedb = self
        self.v4db = v4db
        self.name = name
        self.test_suite = test_suite

        # Save caches of the various fields.
        self.machine_fields = list(self.test_suite.machine_fields)
        self.order_fields = list(self.test_suite.order_fields)
        self.run_fields = list(self.test_suite.run_fields)
        self.sample_fields = list(self.test_suite.sample_fields)

        self.base = sqlalchemy.ext.declarative.declarative_base()

        # Create parameterized model classes for this test suite.
        class ParameterizedMixin(object):
            # Class variable to allow finding the associated test suite from
            # model instances.
            testsuite = self

            # Class variable (expected to be defined by subclasses) to allow
            # easy access to the field list for parameterized model classes.
            fields = None

            def get_field(self, field):
                return getattr(self, field.name)

            def set_field(self, field, value):
                return setattr(self, field.name, value)

        db_key_name = self.test_suite.db_key_name
        class Machine(self.base, ParameterizedMixin):
            __tablename__ = db_key_name + '_Machine'

            fields = self.machine_fields
            id = Column("ID", Integer, primary_key=True)
            name = Column("Name", String(256), index=True)

            # The parameters blob is used to store any additional information
            # reported by the run but not promoted into the machine record. Such
            # data is stored as a JSON encoded blob.
            parameters_data = Column("Parameters", Binary)

            # Dynamically create fields for all of the test suite defined
            # machine fields.
            class_dict = locals()
            for item in fields:
                if item.name in class_dict:
                    raise ValueError,"test suite defines reserved key %r" % (
                        name,)

                class_dict[item.name] = item.column = Column(
                    item.name, String(256))

            def __init__(self, name):
                self.name = name

            def __repr__(self):
                return '%s_%s%r' % (db_key_name, self.__class__.__name__,
                                    (self.name,))

            @property
            def parameters(self):
                """dictionary access to the BLOB encoded parameters data"""
                return dict(json.loads(self.parameters_data))

            @parameters.setter
            def parameters(self, data):
                self.parameters_data = json.dumps(sorted(data.items()))

        class Order(self.base, ParameterizedMixin):
            __tablename__ = db_key_name + '_Order'

            # We guarantee that our fields are stored in the order they are
            # supposed to be lexicographically compared, the __cmp__ method
            # relies on this.
            fields = sorted(self.order_fields,
                            key = lambda of: of.ordinal)


            id = Column("ID", Integer, primary_key=True)

            # Define two common columns which are used to store the previous and
            # next links for the total ordering amongst run orders.
            next_order_id = Column("NextOrder", Integer, ForeignKey(
                    "%s.ID" % __tablename__))
            previous_order_id = Column("PreviousOrder", Integer, ForeignKey(
                    "%s.ID" % __tablename__))

            # FIXME: <sheepish> I would really like to have next_order and
            # previous_order relation's here, but can't figure out how to
            # declare them </sheepsih>.

            # Dynamically create fields for all of the test suite defined order
            # fields.
            class_dict = locals()
            for item in self.order_fields:
                if item.name in class_dict:
                    raise ValueError,"test suite defines reserved key %r" % (
                        name,)

                class_dict[item.name] = item.column = Column(
                    item.name, String(256))

            def __init__(self, previous_order_id = None, next_order_id = None,
                         **kwargs):
                self.previous_order_id = previous_order_id
                self.next_order_id = next_order_id

                # Initialize fields (defaulting to None, for now).
                for item in self.fields:
                    self.set_field(item, kwargs.get(item.name))

            def __repr__(self):
                fields = dict((item.name, self.get_field(item))
                              for item in self.fields)

                return '%s_%s(%r, %r, **%r)' % (
                    db_key_name, self.__class__.__name__,
                    self.previous_order_id, self.next_order_id, fields)

            def __cmp__(self, b):
                # SA occassionally uses comparison to check model instances
                # verse some sentinels, so we ensure we support comparison
                # against non-instances.
                if self.__class__ is not b.__class__:
                    return -1

                return cmp(tuple(self.get_field(item)
                                 for item in self.fields),
                           tuple(b.get_field(item)
                                 for item in self.fields))

        class Run(self.base, ParameterizedMixin):
            __tablename__ = db_key_name + '_Run'

            fields = self.run_fields
            id = Column("ID", Integer, primary_key=True)
            machine_id = Column("MachineID", Integer, ForeignKey(Machine.id),
                                index=True)
            order_id = Column("OrderID", Integer, ForeignKey(Order.id),
                              index=True)
            imported_from = Column("ImportedFrom", String(512))
            start_time = Column("StartTime", DateTime)
            end_time = Column("EndTime", DateTime)
            simple_run_id = Column("SimpleRunID", Integer)

            # The parameters blob is used to store any additional information
            # reported by the run but not promoted into the machine record. Such
            # data is stored as a JSON encoded blob.
            parameters_data = Column("Parameters", Binary)

            machine = sqlalchemy.orm.relation(Machine)
            order = sqlalchemy.orm.relation(Order)

            # Dynamically create fields for all of the test suite defined run
            # fields.
            #
            # FIXME: We are probably going to want to index on some of these,
            # but need a bit for that in the test suite definition.
            class_dict = locals()
            for item in fields:
                if item.name in class_dict:
                    raise ValueError,"test suite defines reserved key %r" % (
                        name,)

                class_dict[item.name] = item.column = Column(
                    item.name, String(256))

            def __init__(self, machine, order, start_time, end_time):
                self.machine = machine
                self.order = order
                self.start_time = start_time
                self.end_time = end_time
                self.imported_from = None

            def __repr__(self):
                return '%s_%s%r' % (db_key_name, self.__class__.__name__,
                                    (self.machine, self.order, self.start_time,
                                     self.end_time))

            @property
            def parameters(self):
                """dictionary access to the BLOB encoded parameters data"""
                return dict(json.loads(self.parameters_data))

            @parameters.setter
            def parameters(self, data):
                self.parameters_data = json.dumps(sorted(data.items()))

        class Test(self.base, ParameterizedMixin):
            __tablename__ = db_key_name + '_Test'

            id = Column("ID", Integer, primary_key=True)
            name = Column("Name", String(256), unique=True, index=True)

            def __init__(self, name):
                self.name = name

            def __repr__(self):
                return '%s_%s%r' % (db_key_name, self.__class__.__name__,
                                    (self.name,))

        class Sample(self.base, ParameterizedMixin):
            __tablename__ = db_key_name + '_Sample'

            fields = self.sample_fields
            id = Column("ID", Integer, primary_key=True)
            # We do not need an index on run_id, this is covered by the compound
            # (Run(ID),Test(ID)) index we create below.
            run_id = Column("RunID", Integer, ForeignKey(Run.id))
            test_id = Column("TestID", Integer, ForeignKey(Test.id), index=True)

            run = sqlalchemy.orm.relation(Run)
            test = sqlalchemy.orm.relation(Test)

            @staticmethod
            def get_primary_fields():
                """
                get_primary_fields() -> [SampleField*]

                Get the primary sample fields (those which are not associated
                with some other sample field).
                """
                status_fields = set(s.status_field
                                    for s in self.Sample.fields
                                    if s.status_field is not None)
                for field in self.Sample.fields:
                    if field not in status_fields:
                        yield field

            # Dynamically create fields for all of the test suite defined sample
            # fields.
            #
            # FIXME: We might want to index some of these, but for a different
            # reason than above. It is possible worth it to turn the compound
            # index below into a covering index. We should evaluate this once
            # the new UI is up.
            class_dict = locals()
            for item in self.sample_fields:
                if item.name in class_dict:
                    raise ValueError,"test suite defines reserved key %r" % (
                        name,)

                if item.type.name == 'Real':
                    item.column = Column(item.name, Float)
                elif item.type.name == 'Status':
                    item.column = Column(item.name, Integer, ForeignKey(
                            testsuite.StatusKind.id))
                else:
                    raise ValueError,(
                        "test suite defines unknown sample type %r" (
                            item.type.name,))

                class_dict[item.name] = item.column

            def __init__(self, run, test, **kwargs):
                self.run = run
                self.test = test

                # Initialize sample fields (defaulting to 0, for now).
                for item in self.fields:
                    self.set_field(item, kwargs.get(item.name, 0))

            def __repr__(self):
                fields = dict((item.name, self.get_field(item))
                              for item in self.fields)

                return '%s_%s(%r, %r, **%r)' % (
                    db_key_name, self.__class__.__name__,
                    self.run, self.test, fields)

        self.Machine = Machine
        self.Run = Run
        self.Test = Test
        self.Sample = Sample
        self.Order = Order

        # Create the compound index we cannot declare inline.
        sqlalchemy.schema.Index("ix_%s_Sample_RunID_TestID" % db_key_name,
                                Sample.run_id, Sample.test_id)

        # Create the index we use to ensure machine uniqueness.
        args = [Machine.name, Machine.parameters_data]
        for item in self.machine_fields:
            args.append(item.column)
        sqlalchemy.schema.Index("ix_%s_Machine_Unique" % db_key_name,
                                *args, unique = True)

        # Create the test suite database tables in case this is a new database.
        self.base.metadata.create_all(self.v4db.engine)

        # Add several shortcut aliases, similar to the ones on the v4db.
        self.add = self.v4db.add
        self.commit = self.v4db.commit
        self.query = self.v4db.query
        self.rollback = self.v4db.rollback

    def _getOrCreateMachine(self, machine_data):
        """
        _getOrCreateMachine(data) -> Machine, bool

        Add or create (and insert) a Machine record from the given machine data
        (as recorded by the test interchange format).

        The boolean result indicates whether the returned record was constructed
        or not.
        """

        # Convert the machine data into a machine record. We construct the query
        # to look for any existing machine at the same time as we build up the
        # record to possibly add.
        #
        # FIXME: This feels inelegant, can't SA help us out here?
        query = self.query(self.Machine).\
            filter(self.Machine.name == machine_data['Name'])
        machine = self.Machine(machine_data['Name'])
        machine_parameters = machine_data['Info'].copy()

        # First, extract all of the specified machine fields.
        for item in self.machine_fields:
            if item.info_key in machine_parameters:
                value = machine_parameters.pop(item.info_key)
            else:
                # For now, insert empty values for any missing fields. We don't
                # want to insert NULLs, so we should probably allow the test
                # suite to define defaults.
                value = ''

            query = query.filter(item.column == value)
            machine.set_field(item, value)

        # Convert any remaining machine_parameters into a JSON encoded blob. We
        # encode this as an array to avoid a potential ambiguity on the key
        # ordering.
        machine.parameters = machine_parameters
        query = query.filter(self.Machine.parameters_data ==
                             machine.parameters_data)

        # Execute the query to see if we already have this machine.
        try:
            return query.one(),False
        except sqlalchemy.orm.exc.NoResultFound:
            # If not, add the machine.
            self.add(machine)

            return machine,True

    def _getOrCreateOrder(self, run_parameters):
        """
        _getOrCreateOrder(data) -> Order, bool

        Add or create (and insert) an Order record based on the given run
        parameters (as recorded by the test interchange format).

        The run parameters that define the order will be removed from the
        provided ddata argument.

        The boolean result indicates whether the returned record was constructed
        or not.
        """

        query = self.query(self.Order)
        order = self.Order()

        # First, extract all of the specified order fields.
        for item in self.order_fields:
            if item.info_key in run_parameters:
                value = run_parameters.pop(item.info_key)
            else:
                # We require that all of the order fields be present.
                raise ValueError,"""\
supplied run is missing required run parameter: %r""" % (
                    item.info_key)

            query = query.filter(item.column == value)
            order.set_field(item, value)

        # Execute the query to see if we already have this order.
        try:
            return query.one(),False
        except sqlalchemy.orm.exc.NoResultFound:
            # If not, then we need to insert this order into the total ordering
            # linked list.

            # Add the new order and flush, to assign an ID.
            self.add(order)
            self.v4db.session.flush()

            # Load all the orders.
            orders = list(self.query(self.Order))

            # Sort the objects to form the total ordering.
            orders.sort()

            # Find the order we just added.
            index = orders.index(order)

            # Insert this order into the linked list which forms the total
            # ordering.
            if index > 0:
                previous_order = orders[index - 1]
                previous_order.next_order_id = order.id
                order.previous_order_id = previous_order.id
            if index + 1 < len(orders):
                next_order = orders[index + 1]
                next_order.previous_order_id = order.id
                order.next_order_id = next_order.id

            return order,True

    def _getOrCreateRun(self, run_data, machine):
        """
        _getOrCreateRun(data) -> Run, bool

        Add a new Run record from the given data (as recorded by the test
        interchange format).

        The boolean result indicates whether the returned record was constructed
        or not.
        """

        # Extra the run parameters that define the order.
        run_parameters = run_data['Info'].copy()

        # The tag has already been used to dispatch to the appropriate database.
        run_parameters.pop('tag')

        # Find the order record.
        order,inserted = self._getOrCreateOrder(run_parameters)
        start_time = datetime.datetime.strptime(run_data['Start Time'],
                                                "%Y-%m-%d %H:%M:%S")
        end_time = datetime.datetime.strptime(run_data['End Time'],
                                              "%Y-%m-%d %H:%M:%S")

        # Convert the rundata into a run record. As with Machines, we construct
        # the query to look for any existingrun at the same time as we build up
        # the record to possibly add.
        #
        # FIXME: This feels inelegant, can't SA help us out here?
        query = self.query(self.Run).\
            filter(self.Run.machine_id == machine.id).\
            filter(self.Run.order_id == order.id).\
            filter(self.Run.start_time == start_time).\
            filter(self.Run.end_time == end_time)
        run = self.Run(machine, order, start_time, end_time)

        # First, extract all of the specified run fields.
        for item in self.run_fields:
            if item.info_key in run_parameters:
                value = run_parameters.pop(item.info_key)
            else:
                # For now, insert empty values for any missing fields. We don't
                # want to insert NULLs, so we should probably allow the test
                # suite to define defaults.
                value = ''

            query = query.filter(item.column == value)
            run.set_field(item, value)

        # Any remaining parameters are saved as a JSON encoded array.
        run.parameters = run_parameters
        query = query.filter(self.Run.parameters_data == run.parameters_data)

        # Execute the query to see if we already have this run.
        try:
            return query.one(),False
        except sqlalchemy.orm.exc.NoResultFound:
            # If not, add the run.
            self.add(run)

            return run,True

    def _importSampleValues(self, tests_data, run, tag):
        # We now need to transform the old schema data (composite samples split
        # into multiple tests with mangling) into the V4DB format where each
        # sample is a complete record.
        tag_dot = "%s." % tag
        tag_dot_len = len(tag_dot)

        # Load a map of all the tests, which we will extend when we find tests
        # that need to be added.
        test_cache = dict((test.name, test)
                          for test in self.query(self.Test))

        # First, we aggregate all of the samples by test name. The schema allows
        # reporting multiple values for a test in two ways, one by multiple
        # samples and the other by multiple test entries with the same test
        # name. We need to handle both.
        tests_values = {}
        for test_data in tests_data:
            if test_data['Info']:
                raise ValueError,"""\
test parameter sets are not supported by V4DB databases"""

            name = test_data['Name']
            if not name.startswith(tag_dot):
                raise ValueError,"""\
test %r is misnamed for reporting under schema %r""" % (
                    name, tag)
            name = name[tag_dot_len:]

            # Add all the values.
            values = tests_values.get(name)
            if values is None:
                tests_values[name] = values = []

            values.extend(test_data['Data'])

        # Next, build a map of test name to sample values, by scanning all the
        # tests. This is complicated by the interchange's support of multiple
        # values, which we cannot properly aggregate. We handle this by keying
        # off of the test name and the sample index.
        sample_records = {}
        for name,test_samples in tests_values.items():
            # Map this reported test name into a test name and a sample field.
            #
            # FIXME: This is really slow.
            for item in self.sample_fields:
                if name.endswith(item.info_key):
                    test_name = name[:-len(item.info_key)]
                    sample_field = item
                    break
            else:
                # Disallow tests which do not map to a sample field.
                raise ValueError,"""\
test %r does not map to a sample field in the reported suite""" % (
                    name)

            # Get or create the test.
            test = test_cache.get(test_name)
            if test is None:
                test_cache[test_name] = test = self.Test(test_name)
                self.add(test)

            for i,value in enumerate(test_samples):
                record_key = (test_name, i)
                sample = sample_records.get(record_key)
                if sample is None:
                    sample_records[record_key] = sample = self.Sample(run, test)
                    self.add(sample)

                sample.set_field(sample_field, value)

    def importDataFromDict(self, data, config=None):
        """
        importDataFromDict(data) -> Run, bool

        Import a new run from the provided test interchange data, and return the
        constructed Run record.

        The boolean result indicates whether the returned record was constructed
        or not (i.e., whether the data was a duplicate submission).
        """

        # Construct the machine entry.
        machine,inserted = self._getOrCreateMachine(data['Machine'])

        # Construct the run entry.
        run,inserted = self._getOrCreateRun(data['Run'], machine)

        # Get the schema tag.
        tag = data['Run']['Info']['tag']

        # If we didn't construct a new run, this is a duplicate
        # submission. Return the prior Run.
        if not inserted:
            return False, run

        self._importSampleValues(data['Tests'], run, tag)

        # If we have a config object and we have a database which we are
        # supposed to link simple/ runs from, attempt to find the matching run
        # in that database.
        if config and config.simple_run_source:
            self.find_and_set_simple_run_id(run, data, config)

        return True, run


    def find_and_set_simple_run_id(self, run, data, config):
        # Get the database we are supposed to match run IDs in.
        db = config.config.get_database(config.simple_run_source)

        # Figure out the matching machine.
        simple_machine,created = db.getOrCreateMachine(
            data['Machine']['Name'], data['Machine']['Info'].items())
        if created:
            # Obviously missing, rollback and abort.
            db.rollback()
            return

        run_data = data['Run']
        simple_run,created = db.getOrCreateRun(
            simple_machine,
            run_data.get('Start Time',''), run_data.get('End Time',''),
            run_data['Info'].items())
        if created:
            # Obviously missing, rollback and abort.
            db.rollback()
            return

        # Otherwise, we found the run.
        run.simple_run_id = simple_run.id

    # Simple query support (mostly used by templates)

    def machines(self, name=None):
        q = self.query(self.Machine)
        if name:
            q = q.filter_by(name=name)
        return q

    def getMachine(self, id):
        return self.query(self.Machine).filter_by(id=id).one()

    def getRun(self, id):
        return self.query(self.Run).filter_by(id=id).one()

    def get_adjacent_runs_on_machine(self, run, N, direction = -1):
        """
        get_adjacent_runs_on_machine(run, N, direction = -1) -> [Run*]

        Return the N runs which have been submitted to the same machine and are
        adjacent to the given run.

        The actual number of runs returned may be greater than N in situations
        where multiple reports were received for the same order.

        The runs will be reported starting with the runs closest to the given
        run's order.

        The direction must be -1 or 1 and specified whether or not the
        preceeding or following runs should be returned.
        """
        assert N > 0, "invalid count"
        assert direction in (-1, 1), "invalid direction"

        # The obvious algorithm here is to step through the run orders in the
        # appropriate direction and yield any runs on the same machine which
        # were reported at that order.
        #
        # However, this has one large problem. In some cases, the gap between
        # orders reported on that machine may be quite high. This will be
        # particularly true when a machine has stopped reporting for a while,
        # for example, as there may be large gap between the largest reported
        # order and the last order the machine reported at.
        #
        # In such cases, we could end up executing a large number of individual
        # SA object materializations in traversing the order list, which is very
        # bad.
        #
        # We currently solve this by instead finding all the orders reported on
        # this machine, ordering those programatically, and then iterating over
        # that. This performs worse (O(N) instead of O(1)) than the obvious
        # algorithm in the common case but more uniform and significantly better
        # in the worst cast, and I prefer that response times be uniform. In
        # practice, this appears to perform fine even for quite large (~1GB,
        # ~20k runs) databases.

        # Find all the orders on this machine, then sort them.
        #
        # FIXME: Scalability! However, pretty fast in practice, see elaborate
        # explanation above.
        all_machine_orders = self.query(self.Order).\
            join(self.Run).\
            filter(self.Run.machine == run.machine).distinct().all()
        all_machine_orders.sort()

        # Find the index of the current run.
        index = all_machine_orders.index(run.order)

        # Gather the next N orders.
        if direction == -1:
            orders_to_return = all_machine_orders[max(0, index - N):index]
        else:
            orders_to_return = all_machine_orders[index+1:index+N]

        # Get all the runs for those orders on this machine in a single query.
        runs = self.query(self.Run).\
            filter(self.Run.machine == run.machine).\
            filter(self.Run.order_id.in_(o.id
                                         for o in orders_to_return)).all()

        # Sort the result by order, accounting for direction to satisfy our
        # requirement of returning the runs in adjacency order.
        #
        # Even though we already know the right order, this is faster than
        # issueing separate queries.
        runs.sort(key = lambda r: r.order, reverse = (direction==-1))

        return runs

    def get_previous_runs_on_machine(self, run, N):
        return self.get_adjacent_runs_on_machine(run, N, direction = -1)

    def get_next_runs_on_machine(self, run, N):
        return self.get_adjacent_runs_on_machine(run, N, direction = 1)
