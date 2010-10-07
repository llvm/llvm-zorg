import hashlib
import re
import tempfile

from commands import capture
from commands import error
from commands import rm_f

def get_cc_info(path, cc_flags=[]):
    """get_cc_info(path) -> { ... }

    Extract various information on the given compiler and return a dictionary of
    the results."""

    cc = path

    # Interrogate the compiler.
    cc_version = capture([cc, '-v', '-E'] + cc_flags + 
                         ['-x', 'c', '/dev/null', '-###'],
                         include_stderr=True).strip()
    version_ln = None
    cc_target = None
    cc1_binary = None
    for ln in cc_version.split('\n'):
        if ' version ' in ln:
            version_ln = ln
        elif ln.startswith('Target:'):
            cc_target = ln.split(':',1)[1].strip()
        elif 'cc1' in ln or 'clang-cc' in ln:
            m = re.match(r' "([^"]*)".*"-E".*', ln)
            if not m:
                error("unable to determine cc1 binary: %r: %r" % (cc, ln))
            cc1_binary, = m.groups()
    if version_ln is None:
        error("unable to find compiler version: %r: %r" % (cc, cc_version))
    if cc_target is None:
        error("unable to find compiler target: %r: %r" % (cc, cc_version))
    if cc1_binary is None:
        error("unable to find compiler cc1 binary: %r: %r" % (cc, cc_version))
    m = re.match(r'(.*) version ([^ ]*) (\([^(]*\))(.*)', version_ln)
    if not m:
        error("unable to determine compiler version: %r: %r" % (cc, version_ln))
    cc_name,cc_version_num,cc_build_string,cc_extra = m.groups()

    # Compute normalized compiler name and type. We try to grab source
    # revisions, branches, and tags when possible.
    cc_build = None
    cc_src_branch = None
    cc_src_revision = None
    cc_src_tag = None
    llvm_capable = False
    if (cc_name, cc_extra) == ('gcc',''):
        cc_norm_name = 'gcc'
        m = re.match(r'\(Apple Inc. build ([0-9]*)\)', cc_build_string)
        if m:
            cc_build = 'PROD'
            cc_src_tag, = m.groups()
        else:
            error('unable to determine gcc build version: %r' % cc_build_string)
    elif (cc_name in ('clang', 'Apple clang') and
          cc_extra == '' or 'based on LLVM' in cc_extra):
        llvm_capable = True
        if cc_name == 'Apple clang':
            cc_norm_name = 'apple_clang'
        else:
            cc_norm_name = 'clang'
        m = re.search('clang-([0-9]*)', cc_build_string)
        if m:
            cc_build = 'PROD'
            cc_src_tag, = m.groups()
        else:
            cc_build = 'DEV'
            m = re.match(r'\(([^ ]+) ([0-9]+)\)', cc_build_string)
            if m:
                cc_src_branch,cc_src_revision = m.groups()

                # These show up with git-svn.
                if cc_src_branch == '$URL$':
                    cc_src_branch = None
            else:
                error('unable to determine Clang development build info: %r' % (
                        (cc_name, cc_build_string),))
    elif cc_name == 'gcc' and 'LLVM build' in cc_extra:
        llvm_capable = True
        cc_norm_name = 'llvm-gcc'
        m = re.match(r' \(LLVM build ([0-9.]+)\)', cc_extra)
        if m:
            llvm_build, = m.groups()
            if llvm_build:
                cc_src_tag = llvm_build.strip()
            cc_build = 'PROD'
        else:
            cc_build = 'DEV'
    else:
        error("unable to determine compiler name: %r" % ((cc_name,
                                                          cc_build_string),))

    if cc_build is None:
        error("unable to determine compiler build: %r" % cc_version)

    # If LLVM capable, fetch the llvm target instead.
    if llvm_capable:
        target_cc_ll = capture([cc, '-S', '-flto', '-o', '-'] + cc_flags + 
                               ['-x', 'c', '/dev/null'],
                               include_stderr=True).strip()
        m = re.search('target triple = "(.*)"', target_cc_ll)
        if m:
            cc_target, = m.groups()
        else:
            error("unable to determine LLVM compiler target: %r: %r" %
                  (cc, target_cc_ll))

    # Determine the binary tool versions for the assembler and the linker, as
    # found by the compiler.
    cc_as_version = capture([cc, "-c", '-Wa,-v'] + cc_flags +
                            ['-x', 'assembler', '/dev/null'],
                            include_stderr=True).strip()

    tf = tempfile.NamedTemporaryFile(suffix='.c')
    name = tf.name
    tf.close()
    tf = open(name, 'w')
    print >>tf, "int main() { return 0; }"
    tf.close()
    cc_ld_version = capture([cc, "-Wl,-v"] + cc_flags + [tf.name],
                            include_stderr=True).strip()
    rm_f(tf.name)

    cc_exec_hash = hashlib.sha1()
    cc_exec_hash.update(open(cc,'rb').read())

    cc1_exec_hash = hashlib.sha1()
    cc1_exec_hash.update(open(cc1_binary,'rb').read())

    info = { 'cc_build' : cc_build,
             'cc_name' : cc_norm_name,
             'cc_version_number' : cc_version_num,
             'cc_target' : cc_target,
             'cc_version' :cc_version,
             'cc_exec_hash' : cc_exec_hash.hexdigest(),
             'cc1_exec_hash' : cc1_exec_hash.hexdigest(),
             'cc_as_version' : cc_as_version,
             'cc_ld_version' : cc_ld_version,
             }
    if cc_src_tag is not None:
        info['cc_src_tag'] = cc_src_tag
    if cc_src_revision is not None:
        info['cc_src_revision'] = cc_src_revision
    if cc_src_branch is not None:
        info['cc_src_branch'] = cc_src_branch
    return info

__all__ = [get_cc_info]

if __name__ == '__main__':
    import pprint, sys
    pprint.pprint(get_cc_info(sys.argv[1], sys.argv[2:]))
