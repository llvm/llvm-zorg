import plistlib

def _matches_format(path_or_file):
    try:
        plistlib.readPlist(path_or_file)
        return True
    except:
        return False

format = { 'name' : 'plist',
           'predicate' : _matches_format,
           'read' : plistlib.readPlist,
           'write' : plistlib.writePlist }
