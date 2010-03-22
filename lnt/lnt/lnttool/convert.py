import os
import sys

def convert_data(input, output, inFormat, outFormat):
    from lnt import formats

    out = formats.get_format(outFormat)
    if out is None or not out.get('write'):
        raise SystemExit("unknown output format: %r" % outFormat)

    data = formats.read_any(input, inFormat)

    out['write'](data, output)
    output.flush()

def action_convert(name, args):
    """convert between input formats"""

    from optparse import OptionParser, OptionGroup
    from lnt import formats
    parser = OptionParser("%%prog %s [options] [<input>, [<output>]]" % name)
    parser.add_option("", "--from", dest="inputFormat", metavar="NAME",
                      help="input format name [%default]", default='<auto>',
                      choices=formats.format_names + ['<auto>'])
    parser.add_option("", "--to", dest="outputFormat", metavar="NAME",
                      help="output format name [%default]", default='plist',
                      choices=formats.format_names + ['<auto>'])
    (opts, args) = parser.parse_args(args)

    input = output = '-'
    if len(args) == 0:
        pass
    elif len(args) == 1:
        input, = args
    elif len(args) == 2:
        input,output = args
    else:
        parser.error("invalid number of arguments")

    if input == '-':
        # Guarantee that we can seek.
        import StringIO
        data = sys.stdin.read()
        inf = StringIO.StringIO(data)
    else:
        inf = input

    if output == '-':
        outf = sys.stdout
    else:
        outf = open(output, 'wb')

    try:
        try:
            convert_data(inf, outf, opts.inputFormat, opts.outputFormat)
        finally:
            if outf != sys.stdout:
                outf.close()
    except:
        if outf != sys.stdout:
            os.remove(output)
        raise
