import json

def _matches_format(path_or_file):
    if isinstance(path_or_file, str):
        path_or_file = open(path_or_file)

    try:
        json.load(path_or_file)
        return True
    except:
        return False

def _load_format(path_or_file):
    if isinstance(path_or_file, str):
        path_or_file = open(path_or_file)
    
    return json.load(path_or_file)
    
format = { 'name' : 'json',
           'predicate' : _matches_format,
           'read' : _load_format,
           'write' : json.dump }
