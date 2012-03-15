import hashlib
import os
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

    # Check if this is icc, which isn't going to cooperate with most of our
    # interrogation. This has only been tested for icc 11.1, it isn't
    # particularly robust.
    cc1_binary = None
    if cc_version.startswith('icc: command line warning'):
        cc_name = 'icc'
        cc_version = capture([cc, '-v'], include_stderr=True).strip()
        cc_version_num = cc_version        
        if cc_version_num.startswith('Version '):
            cc_version_num = cc_version_num.split(' ', 1)[1]
        cc_target = capture([cc, '-dumpmachine']).strip()
    else:
        version_ln = None
        cc_target = None
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
            error("unable to find compiler cc1 binary: %r: %r" % (
                    cc, cc_version))
        m = re.match(r'(.*) version ([^ ]*) (\([^(]*\))(.*)', version_ln)
        if not m:
            error("unable to determine compiler version: %r: %r" % (
                    cc, version_ln))
        cc_name,cc_version_num,cc_build_string,cc_extra = m.groups()

    # Compute normalized compiler name and type. We try to grab source
    # revisions, branches, and tags when possible.
    cc_norm_name = None
    cc_build = None
    cc_src_branch = cc_alt_src_branch = None
    cc_src_revision = cc_alt_src_revision = None
    cc_src_tag = None
    llvm_capable = False
    if cc_name == 'icc':
        cc_norm_name = 'icc'
        cc_build = 'PROD'
        
    elif cc_name == 'gcc' and (cc_extra == '' or
                               re.match(r' \(dot [0-9]+\)', cc_extra)):
        cc_norm_name = 'gcc'
        m = re.match(r'\(Apple Inc. build ([0-9]*)\)', cc_build_string)
        if m:
            cc_build = 'PROD'
            cc_src_tag, = m.groups()
        else:
            error('unable to determine gcc build version: %r' % cc_build_string)
    elif (cc_name in ('clang', 'Apple clang') and
          cc_extra == '' or 'based on LLVM' in cc_extra or
          'llvm/' in cc_extra):
        llvm_capable = True
        if cc_name == 'Apple clang':
            cc_norm_name = 'apple_clang'
        else:
            cc_norm_name = 'clang'

        m = re.match(r'\(([^ ]*)( ([0-9]+))?\)', cc_build_string)
        if m:
            cc_src_branch,_,cc_src_revision = m.groups()

            # These show up with git-svn.
            if cc_src_branch == '$URL$':
                cc_src_branch = None
        else:
            # Otherwise, see if we can match a branch and a tag name. That could
            # be a git hash.
            m = re.match(r'\(([^ ]+) ([^ ]+)\)', cc_build_string)
            if m:
                cc_src_branch,cc_src_revision = m.groups()
            else:
                error('unable to determine Clang development build info: %r' % (
                        (cc_name, cc_build_string, cc_extra),))

        m = re.search('clang-([0-9]*)', cc_src_branch)
        if m:
            cc_build = 'PROD'
            cc_src_tag, = m.groups()
            
            # We sometimes use a tag of 9999 to indicate a dev build.
            if cc_src_tag == '9999':
                cc_build = 'DEV'
        else:
            cc_build = 'DEV'

        # Newer Clang's can report separate versions for LLVM and Clang. Parse
        # the cc_extra text so we can get the maximum SVN version.
        if 'llvm/' in cc_extra:
            m = re.match(r' \(llvm/(.*) (.*)\)', cc_extra)
            if m:
                cc_alt_src_branch,cc_alt_src_revision = m.groups()
            else:
                error('unable to determine Clang development build info: %r' % (
                        (cc_name, cc_build_string, cc_extra)))

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
    cc_as_version = capture([cc, "-c", '-Wa,-v', '-o', '/dev/null'] + cc_flags +
                            ['-x', 'assembler', '/dev/null'],
                            include_stderr=True).strip()

    tf = tempfile.NamedTemporaryFile(suffix='.c')
    name = tf.name
    tf.close()
    tf = open(name, 'w')
    print >>tf, "int main() { return 0; }"
    tf.close()
    cc_ld_version = capture(([cc, "-Wl,-v", '-o', '/dev/null'] + 
                             cc_flags + [tf.name]),
                            include_stderr=True).strip()
    rm_f(tf.name)

    cc_exec_hash = hashlib.sha1()
    cc_exec_hash.update(open(cc,'rb').read())

    info = { 'cc_build' : cc_build,
             'cc_name' : cc_norm_name,
             'cc_version_number' : cc_version_num,
             'cc_target' : cc_target,
             'cc_version' :cc_version,
             'cc_exec_hash' : cc_exec_hash.hexdigest(),
             'cc_as_version' : cc_as_version,
             'cc_ld_version' : cc_ld_version,
             }
    if cc1_binary is not None:
        cc1_exec_hash = hashlib.sha1()
        cc1_exec_hash.update(open(cc1_binary,'rb').read())
        info['cc1_exec_hash'] = cc1_exec_hash.hexdigest()
    if cc_src_tag is not None:
        info['cc_src_tag'] = cc_src_tag
    if cc_src_revision is not None:
        info['cc_src_revision'] = cc_src_revision
    if cc_src_branch is not None:
        info['cc_src_branch'] = cc_src_branch
    if cc_alt_src_revision is not None:
        info['cc_alt_src_revision'] = cc_alt_src_revision
    if cc_alt_src_branch is not None:
        info['cc_alt_src_branch'] = cc_alt_src_branch

    # Infer the run order from the other things we have computed.
    info['inferred_run_order'] = '%7d' % (get_inferred_run_order(info),)

    return info

def get_inferred_run_order(info):
    # If the CC has a src revision, use that.
    if info.get('cc_src_revision','').isdigit():
        order = int(info['cc_src_revision'])

        # If the CC has an alt src revision, use that if it is greater:
        if info.get('cc_alt_src_revision','').isdigit():
            order = max(order, int(info.get('cc_alt_src_revision')))

        return order

    # If this is a production compiler, look for a source tag. We don't accept 0
    # or 9999 as valid source tag, since that is what llvm-gcc builds use when
    # no build number is given.
    if (info.get('cc_build') == 'PROD' and
          info.get('cc_src_tag') != '0' and
          info.get('cc_src_tag') != '00' and
          info.get('cc_src_tag') != '9999' and
          info.get('cc_src_tag','').split('.',1)[0].isdigit()):
        return int(info['cc_src_tag'].split('.',1)[0])

    # If that failed, infer from the LLVM revision.
    if info.get('llvm_revision','').isdigit():
        return int(info['llvm_revision'])

    # Otherwise, force at least some value for run_order, as it is now
    # generally required by parts of the "simple" schema.
    return 0

def infer_cxx_compiler(cc_path):
    # If this is obviously a compiler name, then try replacing with the '++'
    # name.
    name = os.path.basename(cc_path)
    if 'clang' in name:
        expected_cxx_name = 'clang++'
        cxx_name = name.replace('clang', expected_cxx_name)
    elif 'gcc' in name:
        expected_cxx_name = 'g++'
        cxx_name = name.replace('gcc', expected_cxx_name)
    elif 'icc' in name:
        expected_cxx_name = 'icpc'
        cxx_name = name.replace('icc', expected_cxx_name)
    else:
        # We have no idea, give up.
        return None

    # Check if the compiler exists at that path.
    cxx_path = os.path.join(os.path.dirname(cc_path), cxx_name)
    if os.path.exists(cxx_path):
        return cxx_path

    # Otherwise, try to let the compiler itself tell us what the '++' version
    # would be. This is useful when the compiler under test is a symlink to the
    # real compiler.
    cxx_path = capture([cc_path, '-print-prog-name=%s' % expected_cxx_name]).strip()
    if os.path.exists(cxx_path):
        return cxx_path
    
o__all__ = ['get_cc_info', 'infer_cxx_compiler']

if __name__ == '__main__':
    import pprint, sys
    pprint.pprint(('get_cc_info', get_cc_info(sys.argv[1], sys.argv[2:])))
    pprint.pprint(('infer_cxx_compiler', infer_cxx_compiler(sys.argv[1])))
