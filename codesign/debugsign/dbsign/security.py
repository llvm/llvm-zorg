# COPYRIGHT LINE: FIXME

"""
dbsign.security
"""

import os
import plistlib
import re
import tempfile

import dbsign.logger as L
from dbsign.result import Failure, Success
from dbsign.shell import run, sudo_run


log = L.get_logger(__name__)

UNSAFE_FLAG = "DEBUGSIGN_UNSAFE"

#
# Helper functions
#


def derive_keychain_extension():  # type: () -> str
    log.debug("Determining keychain file extension")

    ext = "keychain-db"     # used by macOS 10.12+
    log.debug("Starting with default extension: '%s'", ext)

    sw_vers = run('sw_vers -productVersion'.split())
    if sw_vers:
        version_string = sw_vers.stdout
        version = list(map(int, version_string.decode().split('.')))
        if version < [10, 12]:  # pragma: no cover
            ext = 'keychain'
            log.debug("Pre-Sierra OS detected (%s). Using: '%s'",
                      version_string, ext)
    else:  # pragma: no cover
        log.warn("Failed to query OS version: %s", sw_vers)

    sec_default = run("security default-keychain".split())
    if sec_default:
        # strip security garbage to get filename
        keydb = strip_security_noise(sec_default.stdout)
        ext = os.path.splitext(keydb)[1].lstrip('.')
        log.debug("Derived extension '%s' from login keychain '%s'",
                  ext, keydb)

    log.debug("Using keychain file extension: %s", ext)
    return ext


def keychain_to_file(name):  # type: (str) -> str
    """Converts user keychain name to a full path."""
    log.debug('keychain_to_file({!r})'.format(name))
    ext = _KEYCHAIN_EXT
    key_dir = os.path.expanduser('~/Library/Keychains')
    keydb = "{}/{}.{}".format(key_dir, name, ext)
    log.debug('keychain_to_file => {!r}'.format(keydb))
    return keydb


def rules_from(data):  # type: (str) -> list(str)
    log.debug("rules_from({!r})".format(data))
    dict_ = plistlib.readPlistFromString(data)
    log.debug(dict_)
    return dict_.get('rule', [])


def strip_security_noise(s):  # type: (str) -> str
    return s.decode().strip(''' "'\n''')


_KEYCHAIN_EXT = derive_keychain_extension()


#
# authorizationdb Operations
#


def authdb_privilege_read(privilege):  # type: (str) -> Result
    log.debug('authdb_privilege_read("%s")', privilege)

    res = run(["security", "authorizationdb", "read", privilege])
    if not res:
        err_msg = 'Failed to read privilege {}: {}'.format(
            privilege, res.stdout)
        log.warn(err_msg)
        return Failure(err_msg)

    return Success(res.stdout)


def authdb_privilege_write(privilege, value):  # type: (str, str) -> Result
    log.debug('authdb_privilege_write("%s", "%s")', privilege, value)

    if not os.getenv(UNSAFE_FLAG, False):
        log.info("Unauthorized unsafe operation")
        log.info("To enable running this command, pass the --unsafe flag or"
                 " set the %s environment variable.", UNSAFE_FLAG)
        return Failure("Setting privileges requires --unsafe flag")

    res = sudo_run(['security', 'authorizationdb', 'write', privilege, value])
    if not res:
        err_msg = 'Failed to set authdb privilege {} => {}'.format(
            privilege, value)
        log.warn(err_msg)
        return Failure(err_msg)

    return Success('{} => {}'.format(privilege, value))


def verify_privilege(priv):  # type: (str) -> Result
    log.debug('verify_privilege(%s)', repr(priv))

    rule_value = 'allow'

    res_read = authdb_privilege_read(priv)
    if not res_read:
        log.debug(res_read)
        return res_read

    rules = rules_from(res_read.value)
    if rule_value not in rules:
        return Failure(rules)

    return Success(priv)


def verify_privileges(privs):  # type: (list(str)) -> Result
    log.debug('verify_privileges(%s)', repr(privs))

    for priv in privs:
        res = verify_privilege(priv)
        if not res:
            log.debug(res)
            return res.renew()

    return Success(privs)


#
# Keychain Operations
#

def add_to_search_list(keydb):  # type: (str) -> Result
    """
    Adds keychain to security search list.
    codesign will only search keychains on this list.
    """
    res_list = get_search_list()
    if not res_list:
        return res_list.renew()

    keylist = res_list.value
    if keydb in keylist:
        # keychain already present; noop
        log.debug(keylist)
        log.debug("{} already present in search list: {}".
                  format(keydb, keylist))
        return Success(keydb)

    keylist.append(keydb)
    cmd_params = ['security', 'list-keychains', '-d', 'user', '-s']
    sec_add = run(cmd_params + keylist)
    if not sec_add:  # pragma: no cover
        return Failure(sec_add)

    return Success(keydb)


def create_keychain(keydb, password):  # type: (str, str) -> Result
    log.debug("Creating keychain: %s", keydb)

    if not keychain_exists(keydb):
        sec_make = run(['security', 'create-keychain', '-p', password, keydb])
        if not sec_make:  # pragma: no cover
            return Failure(sec_make)

    sec_add = add_to_search_list(keydb)
    if not sec_add:  # pragma: no cover
        return Failure(sec_add)

    # Invoking without arguments sets timeout=infinite.
    # Prevents keychain from locking after timeout.
    sec_settings = run(['security', 'set-keychain-settings', keydb])
    if not sec_settings:  # pragma: no cover
        return Failure(sec_settings)

    return Success(sec_settings)


def delete_keychain(keydb, backup=True):  # type: (str, bool) -> Result
    log.debug('delete_keychain({!r}'.format(keydb))

    if backup:
        new_keydb = "{}.bak-{}".format(keydb, str(os.getpid()))
        try:
            os.rename(keydb, new_keydb)
            log.info("Backed up {!r} to {!r}".format(keydb, new_keydb))
        except OSError as ose:  # pragma: no cover
            log.debug(ose)
            return Failure(ose)

    sec_delete = run(['security', 'delete-keychain', keydb])
    if not (sec_delete or backup):  # pragma: no cover
        # If backed up, security WILL return non-zero.
        # However, it will also remove the keychain from the search list.
        log.debug(sec_delete)

    if os.path.exists(keydb):   # pragma: no cover
        os.unlink(keydb)        # if it's still around, brute force rm it

    return Success(new_keydb)


def get_search_list():  # type: () -> Result
    sec_list = run(['security', 'list-keychains'])
    if not sec_list:  # pragma: no cover
        return Failure("Failed to get search list: {}".format(sec_list))

    list_lines = map(strip_security_noise, sec_list.stdout.splitlines())
    return Success(list_lines)


def keychain_exists(keydb):  # type: (str, str) -> bool
    log.debug("keychain_exists(%s)", repr(keydb))

    if not os.path.exists(keydb):
        return Failure('No file at keychain path {!r}'.format(keydb))

    log.debug('keychain_exists: found keychain file at `%s`', keydb)

    return Success(keydb)


def unlock_keychain(keydb, password):  # type: (str, str) -> Result
    log.debug('unlock_keychain({!r}, {!r})'.format(keydb, '********'))

    sec_unlock = run(['security', 'unlock-keychain', '-p', password, keydb])
    if not sec_unlock:
        return Failure(sec_unlock)

    return Success(keydb)


#
# Identity Operations
#

def delete_identity(identity, keydb):  # type: (str, str) -> Result
    log.debug('delete_identity({!r}'.format(identity))

    sec_delete = run(['security', 'delete-identity',
                      '-tc', identity, keydb])
    if not sec_delete:
        return Failure(sec_delete.stderr)

    return Success(identity)


def find_identity(identity, keydb, valid=False):  # type: (str, str) -> Result
    log.debug('find_identity({!r}, {!r}, valid={!r})'.
              format(identity, keydb, valid))

    if valid:
        flags = '-vp'
    else:
        flags = '-p'

    sec = run(['security', 'find-identity', flags, 'codesigning', keydb])
    if not sec:
        log.debug(sec)
        return Failure(sec)

    m = re.search(r'\b{}\b'.format(identity), sec.stdout)
    if not m:
        log.debug("{}: {!r}".format(identity, sec.stdout))
        return Failure('{!r} not found in {!r}'.format(identity, sec.stdout))

    return Success(identity)


def identity_installed(identity, keydb):  # type: (str, str) -> Result
    log.debug('identity_installed({!r}, {!r})'.format(identity, keydb))

    find_all = find_identity(identity, keydb, valid=False)
    if not find_all:
        return Failure('Identity not found')

    find_valid = find_identity(identity, keydb, valid=True)
    if not find_valid:
        return Failure('Identity present but invalid')

    return Success(identity)


def import_identity(keydb, key_pass, identity, id_file, id_pass):
    # type: (str, str, str, str, str) -> Result
    log.debug('import_identity({!r}, {!r}, {!r}, {!r})'.format(
        keydb, identity, id_file, '********'))

    # ensure keychain exists
    if not os.path.exists(id_file):
        return Failure('Identity file {!r} not found'.format(id_file))

    sec_add = add_to_search_list(keydb)
    if not sec_add:
        return Failure(sec_add)

    res_find_id = identity_installed(identity, keydb)
    if res_find_id:
        return Failure("Identity exists: {!r}".format(res_find_id.value))

    # import identity to keychain
    cmd_import = run(['security', 'import', id_file,
                      '-k', keydb, '-f', 'pkcs12',
                      '-P', id_pass, '-T', '/usr/bin/codesign'])
    if not cmd_import:
        return Failure(cmd_import.stderr)

    sec_part = sudo_run(['security', 'set-key-partition-list',
                         '-S', 'apple', '-k', key_pass, keydb])
    if not sec_part:
        return Failure("Failed to authorize identity: {}".
                       format(sec_part.stderr))

    return Success("Imported identity {} from {}".format(identity, id_file))


def trust_identity(identity, keydb):  # type: (str) -> Result
    fd, tmpfile = tempfile.mkstemp()
    fh = os.fdopen(fd, 'w')
    log.debug("Temp filename: %s", tmpfile)

    sec_extract = run(['security', 'find-certificate', '-p',
                       '-c', identity, keydb])
    if not sec_extract:
        log.debug(sec_extract)
        return Failure(sec_extract)

    fh.write(sec_extract.stdout)
    fh.close()

    sec_add = sudo_run(['security', 'add-trusted-cert', '-d',
                        '-p', 'basic', '-p', 'codeSign', tmpfile])
    if not sec_add:
        os.unlink(tmpfile)
        return Failure("Failed to add cert:\n{}".format(sec_extract.stdout))

    res_valid = find_identity(identity, keydb, valid=True)
    if not res_valid:
        return Failure("Invalid identity.")

    sec_sign = run(['codesign', '--keychain', keydb, '-s', identity, tmpfile])
    os.unlink(tmpfile)
    if not sec_sign:
        return Failure("Codesigning failed: {}".format(sec_sign.stderr))

    return Success(identity)


def verify_identity(identity, keydb):  # type: (str) -> Result
    log.debug("verify_identity({!r}, {!r})".format(identity, keydb))

    fd, filename = tempfile.mkstemp(suffix='-temp')
    log.debug('Test file: {}'.format(filename))
    os.close(fd)

    res = verify_identity_with_file(identity, keydb, filename)
    if os.path.exists(filename):
        os.remove(filename)

    return res


def verify_identity_with_file(identity, keydb, filename):
    # type: (str, str) -> Result
    log.debug("verify_identity_with_file({!r}, {!r}, {!r})".
              format(identity, keydb, filename))

    # ensure tempfile exists
    if not os.path.exists(filename):
        return Failure("File {!r} doesn't exist!".format(filename))

    # ensure signing identity exists and is valid
    res_find = identity_installed(identity, keydb)
    if not res_find:
        log.debug(res_find)

    # use identity to codesign the tempfile
    cmd_sign = run(['codesign', '-fs', identity, filename])
    if not cmd_sign:
        return Failure(cmd_sign)

    # check signing authority of file signature
    cmd_check = run(['codesign', '-dvv', filename])
    if not cmd_check:
        return Failure(cmd_check)

    # ensure signing authority matches the identity name
    re_auth = r"^Authority=(?P<authority>{})$".format(identity)
    m = re.search(re_auth, cmd_check.stderr, re.MULTILINE)
    if not m:
        log.debug(cmd_check)
        return Failure('Identity not found in signature')

    return Success(m.group('authority'))
