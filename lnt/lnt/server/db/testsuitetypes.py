"""
This module maintains information on the "known" test suite types.

In order to follow the existing usage model for LNT with the v0.4 design (in
which test suites get customized databases), we support dynamically creating
appropriate test suites on the fly for these known types.
"""

from lnt.server.db import testsuite

def get_compile_testsuite(db):
    # Create a test suite compile with "lnt runtest compile".
    ts = testsuite.TestSuite("compile", "compile")

    # Promote some natural information to fields.
    ts.machine_fields.append(testsuite.MachineField("hardware",
                                                    "hw.model"))
    ts.machine_fields.append(testsuite.MachineField("os_version",
                                                    "kern.version"))

    # The only reliable order currently is the "run_order" field. We will want
    # to revise this over time.
    ts.order_fields.append(testsuite.OrderField("llvm_project_revision",
                                                "run_order", 0))

    # We expect up to five fields per test, each with a status field.
    for name,type_name in (('user', 'time'),
                           ('sys', 'time'),
                           ('wall', 'time'),
                           ('size', 'bytes'),
                           ('mem', 'bytes')):
        status = testsuite.SampleField(
            "%s_status" % (name,), db.status_sample_type, "%s.status" % (name,))
        ts.sample_fields.append(status)
        value = testsuite.SampleField(
            "%s_%s" % (name,type_name), db.real_sample_type, ".%s" % (name,),
            status_field = status)
        ts.sample_fields.append(value)

    return ts

def get_nts_testsuite(db):
    # Create a test suite compile with "lnt runtest nt".
    ts = testsuite.TestSuite("nts", "NT")

    # Promote the natural information produced by 'runtest nt' to fields.
    ts.machine_fields.append(testsuite.MachineField("hardware", "hardware"))
    ts.machine_fields.append(testsuite.MachineField("os", "os"))

    # The only reliable order currently is the "run_order" field. We will want
    # to revise this over time.
    ts.order_fields.append(testsuite.OrderField("llvm_project_revision",
                                                "run_order", 0))

    # We are only interested in simple runs, so we expect exactly four fields
    # per test.
    compile_status = testsuite.SampleField(
            "compile_status", db.status_sample_type, ".compile.status")
    compile_time = testsuite.SampleField(
        "compile_time", db.real_sample_type, ".compile",
        status_field = compile_status)
    exec_status = testsuite.SampleField(
            "execution_status", db.status_sample_type, ".exec.status")
    exec_time = testsuite.SampleField(
            "execution_time", db.real_sample_type, ".exec",
            status_field = exec_status)
    ts.sample_fields.append(compile_time)
    ts.sample_fields.append(compile_status)
    ts.sample_fields.append(exec_time)
    ts.sample_fields.append(exec_status)

    return ts

_registry = {
    'compile' : get_compile_testsuite,
    'nts' : get_nts_testsuite,
    }
def get_testsuite_for_type(typename, db):
    method = _registry.get(typename)
    if method:
        return method(db)
    return None

__all__ = ['get_testsuite_for_type']
