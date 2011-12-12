import datetime
from lnt.server.ui import util

def filter_asusertime(time):
    # FIXME: Support alternate timezones?
    ts = datetime.datetime.fromtimestamp(time)
    return ts.strftime('%Y-%m-%d %H:%M:%S %Z PST')

def filter_aspctcell(value, *args, **kwargs):
    cell = util.PctCell(value, *args, **kwargs)
    return cell.render()

def register(app):
    for name,object in globals().items():
        if name.startswith('filter_'):
            app.jinja_env.filters[name[7:]] = object
