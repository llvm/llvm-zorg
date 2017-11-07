import re

class Severity(object):
    """Set seriousness of an error."""
    FATAL = 0
    UNEXPECTED_ERROR = 1
    EXPECTED_ERROR = 2
    WARNING = 3
    INFO = 4


class SearchPattern(object):
    # noinspection PyPep8Naming
    """Define the issue's search pattern that was created through a regex match."""

    def __init__(self, name, nlp, pattern, html_template, severity,
                 keep_going=True):
        # type: (str, str, str, unicode, bool, int) -> None
        """
        Pattern to search for.

        :param name: short name to identify this pattern.
        :param pattern: a regex to match.
        """
        self.name = name  # type: str
        """The display name of the pattern."""

        self.html_template = html_template  # type: unicode
        """The HTML template to use to render the pattern."""

        self.pattern_text = pattern  # type: str
        """The regex for this pattern."""

        self.nlp = nlp
        """The NLP class to use to render this kind of error."""

        self.pattern = pattern
        """Regular expression for this pattern."""

        self.regex = re.compile(pattern)
        """The compiled regex for this pattern."""

        self.keep_going = keep_going
        """True if we should keep going after hitting one of these issues."""

        self.severity = severity
        """Integer severity level of this kind of pattern."""

    def __repr__(self):
        """Simplify and standardize printing of a search pattern."""
        return self.__class__.__name__ + "(" + self.name + ")"


default_search = [

    SearchPattern("Wrong LLVM Option",
                  'GenericNLP',
                  r"clang \(LLVM option parsing\): Unknown command line argument (?P<error>'.*')\.  "
                  r"Try: 'clang \(LLVM option parsing\) -help",
                  u"{name}: {error} ",
                  Severity.UNEXPECTED_ERROR),
    #  Untested
    SearchPattern("CMake Error",
                  'GenericNLP',
                  r"CMake Error: (?P<error>.*)",
                  u"{name}: {error} ",
                  Severity.UNEXPECTED_ERROR),
    #  Untested
    SearchPattern("Jenkins Shell Script Error",
                  'GenericNLP',
                  r"Build step (?P<reason>'(?!Trigger).*').*failure",
                  u"{name}: {reason} ",
                  Severity.INFO),
    #  Untested
    SearchPattern("rsync error",
                  'GenericNLP',
                  r"rsync error(?P<error>.*) at (?P<location>.*)\s*",
                  u"{name}: {error} {location} ",
                  Severity.UNEXPECTED_ERROR),
    #  Tested
    SearchPattern("Clang",
                  'Clang',
                  r"(?P<file_name>(\w|/|-|@|\.)*):(?P<line_number>\d+)(:\d+)?.*\s+"
                  r"(?P<kind>error):\s+(?P<error_msg>.*)",
                  u"{file_name} {kind}: {error_msg} ",
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Clang file warning",
                  'Clang',
                  r"(?P<file_name>(\w|/|-|@|\.)*):(?P<line_number>\d+)(:\d+)?.*\s+"
                  r"(?P<kind>warning):\s+(?P<error_msg>.*)",
                  u"{file_name} {kind}: {error_msg} ",
                  Severity.WARNING),
    #  Untested
    SearchPattern("Too many errors emitted",
                  'GenericNLP',
                  r"fatal error: too many errors emitted.*",
                  u"{name}: not good",
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("SSH Connection Closed",
                  'GenericNLP',
                  r'ssh_exchange_identification:(?P<error_message>.*)',
                  u"{name}:{error_message}",
                  Severity.FATAL,
                  ),

    SearchPattern("Clang Warning",
                  'Clang_Warning',
                  r"clang-(\d+\.)+\d+: warning: *(?P<type>.*): (?P<which_arg>'-.*').*",
                  u"{name}: {type} {which_arg}",
                  Severity.WARNING),

    SearchPattern("link error",
                  'GenericNLP',
                  r'.*linker command failed with exit code.*',
                  u"{name}",
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("node offline",
                  'GenericNLP',
                  r'ERROR: (?P<node>.*) is offline; cannot locate JDK',
                  u"{name}: {node}",
                  Severity.FATAL,
                  keep_going = False),

    SearchPattern("assertion",
                  'GenericNLP',
                  r'Assertion failed: \((?P<assert_text>.*)\), function (?P<function>.*), file '
                  r'(?P<file_name>[\S]*), line (?P<line_number>\d+).',
                  u"{name}: {assert_text}",
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("gtest error",
                  'GenericNLP',
                  r'.*/googletest\.py:\d+: error: (?P<error_msg>.*) in \'(?P<file_name>.*)\':',
                  u"{name}: {error_msg} in {file_name}",
                  Severity.EXPECTED_ERROR),

    SearchPattern("lit",
                  'Lit',
                  r'\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\* TEST \'(?P<test_name>.*)\' FAILED '
                  r'\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*\*',
                  u"{name}: {test_name}",
                  Severity.EXPECTED_ERROR),
    SearchPattern("lint",
                  'GenericNLP',  # 'lint: %(path)s:%(row)d:%(col)d: %(code)s %(text)s'
                  r'lint:\s(?P<file_name>.*):\d+:\d+:\s(?P<error_msg>.*)',
                  u"{name}: {error_msg}",
                  Severity.EXPECTED_ERROR),
    SearchPattern("lnt",
                  'GenericNLP',
                  r'FAIL:\s(?P<test_name>.*)\.(?P<test_kind>.*)\s\(',
                  u"{name}: {test_name}",
                  Severity.EXPECTED_ERROR),
    SearchPattern("Test Case",
                  'GenericNLP',
                  r'(?P<fail_type>FAIL|ERROR): (?P<test_name>.*)\s\((?P<file_name>.*)\)',
                  u"{name}: {fail_type} - {file_name} {test_name}",
                  Severity.EXPECTED_ERROR),
    SearchPattern("Cmake Error",
                  'GenericNLP',
                  r'CMake Error at (?P<file_name>.*) \(message\):',
                  u"{name}: {file_name}",
                  Severity.UNEXPECTED_ERROR),
    SearchPattern("Segfault",
                  'GenericNLP',
                  r'clang: error: unable to execute command: Segmentation fault: 11',
                  u"{name}",
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Ninja target",
                  'GenericNLP',
                  r'FAILED: (?P<file_name>.*)\s*',
                  u"{name}: {file_name}",
                  Severity.INFO),

    SearchPattern("Swift Execute Command Failed",
                  'GenericNLP',
                  r'FAIL.*command=\"(?P<command>[\w* ]*)-.*, (?P<return_code>returncode=.*)',
                  u'{name}: {command} with {return_code}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Timeout",
                  'GenericNLP',
                  r'Build timed out \(after \d+ minutes\)\. Marking the build as failed\.',
                  u"{name}",
                  Severity.UNEXPECTED_ERROR,
                  keep_going=False),

    SearchPattern("Aborted",
                  'GenericNLP',
                  r'Aborted by (\w+)',
                  u"{name}",
                  Severity.FATAL,
                  keep_going=False),

    SearchPattern("Jenkins Aborted",
                  'GenericNLP',
                  r'Build was aborted',
                  u"{name}",
                  Severity.FATAL,
                  keep_going=False),

    SearchPattern("Triggered build failed",
                  'GenericNLP',
                  r'(?i)Build step \'Trigger/call builds on other projects\' (marked|changed) build '
                  r'(as|result to) failure$',
                  u"{name}",
                  Severity.EXPECTED_ERROR),

    SearchPattern("Triggered build unstable",
                  'GenericNLP',
                  r'Build step \'Trigger/call builds on other projects\' changed build result to UNSTABLE$',
                  u"{name}",
                  Severity.EXPECTED_ERROR),

    SearchPattern("Ninja error",
                  'GenericNLP',
                  r'ninja: error: (?P<error_msg>.*)',
                  u"{name}: {error_msg}",
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Password expired",
                  'GenericNLP',
                  r'Password has expired$',
                  u"{name}",
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("SVN error",
                  'GenericNLP',
                  r'org\.tmatesoft\.svn\.core\.SVNException: svn: (?P<error_code>.*): (?P<error_msg>.*)',
                  u'{name}: {error_msg}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Java exception",
                  'GenericNLP',
                  r'(?P<exception>(hudson|java)\.\S*Exception):\s(?P<error_msg>.*)',
                  u'{exception}: {error_msg}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Non-specific Java exception",
                  'GenericNLP',
                  r'(?P<exception>(hudson|java)\.\S*Exception)',
                  u'{exception}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("HTTP Error",
                  'Error',
                  r'HTTP Error:\s(?P<code>\d+)\s(?P<url>.*)',
                  u'{name}: {code}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Fatal Error",
                  'Error',
                  r'(?i)fatal( error)?:\s(?P<error_msg>.*)',
                  u'{name}: {error_msg}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Warning",
                  'Error',
                  r'(?i)(warning):\s(?!profile data may be out of date)(?P<warning_msg>.*)',
                  u'{name}: {warning_msg}',
                  Severity.WARNING),

    SearchPattern("Python exception",
                  'GenericNLP',
                  r'(?P<exception>(socket\.error|'
                  r'SystemExit|'
                  r'KeyboardInterrupt|'
                  r'GeneratorExit|'
                  r'Exception|'
                  r'StopIteration|'
                  r'StandardError|'
                  r'BufferError|'
                  r'ArithmeticError|'
                  r'FloatingPointError|'
                  r'OverflowError|'
                  r'ZeroDivisionError|'
                  r'AssertionError|'
                  r'AttributeError|'
                  r'EnvironmentError|'
                  r'IOError|'
                  r'OSError|'
                  r'EOFError|'
                  r'ImportError|'
                  r'LookupError|'
                  r'IndexError|'
                  r'KeyError|'
                  r'MemoryError|'
                  r'NameError|'
                  r'UnboundLocalError|'
                  r'ReferenceError|'
                  r'RuntimeError'
                  r'|NotImplementedError|'
                  r'SyntaxError|'
                  r'IndentationError|'
                  r'TabError|'
                  r'SystemError|'
                  r'TypeError|'
                  r'ValueError|'
                  r'UnicodeError|'
                  r'UnicodeDecodeError|'
                  r'UnicodeEncodeError|'
                  r'UnicodeTranslateError|'
                  r'DeprecationWarning|'
                  r'PendingDeprecationWarning|'
                  r'RuntimeWarning|'
                  r'SyntaxWarning|'
                  r'UserWarning|'
                  r'FutureWarning|'
                  r'requests\.exceptions\.HTTPError|'
                  r'ImportWarning|'
                  r'UnicodeWarning|'
                  r'BytesWarning|'
                  r'subprocess\.CalledProcessError|'
                  r'common_adopter\.ExecuteCommandFailure|'
                  r'urllib2\.HTTPError)):\s(?P<error_msg>.*)',
                  u'{exception}: {error_msg}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Merge Conflict",
                  'GenericNLP',
                  r'CONFLICT \([\w\/]+\): Merge conflict in (?P<file_name>.*)',
                  u'{name}: {file_name}',
                  Severity.EXPECTED_ERROR),
    SearchPattern("Xcode Select Error",
                  'GenericNLP',
                  r'xcode-select: error:\s(?P<error_msg>.*)',
                  u'{name}: {error_msg}',
                  Severity.UNEXPECTED_ERROR),
    SearchPattern("ASANError",  # Fixes rdar://problem/31719510
                  'GenericNLP',
                  r'.*SUMMARY:\s(?!\s*\d)AddressSanitizer(?P<error_msg>.*)',
                  u'{name}: {error_msg}',
                  Severity.UNEXPECTED_ERROR),
    SearchPattern("Proxy Error Message",  # Fixes rdar://problem/31719510
                  'GenericNLP',
                  r'Reason: &lt;strong&gt;(?P<error_msg>.*)&lt;/strong.*&gt;',
                  u'{name}: {error_msg}',
                  Severity.UNEXPECTED_ERROR),
    SearchPattern("Env No Such File or Directory",  # Fixes rdar://problem/32157409
                  'GenericNLP',
                  r'env:\s*(?P<file_name>(?:/\w+)*):\s*No such file or directory',
                  u'{name}: {file_name}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Error Low Disk Space",  # Fixes rdar://problem/32081011
                  'GenericNLP',
                  r"Error: (?P<error_msg>low disk space).*scale\(collectd\.(?P<node>.*apple_com).*,\s(?P<free>\d*)",
                  u'{name}: {error_msg} on {node}, {free}GB left.',
                  Severity.EXPECTED_ERROR),

    SearchPattern("Error Device Name",  # Fixes rdar://problem/32081011
                  'GenericNLP',
                  r".*ERROR: (?P<error_msg>.*Cannot find device named '\w.*)",
                  u'{name}: {error_msg}',
                  Severity.UNEXPECTED_ERROR),
    # Other errors have stops. If we hit this one, we know we did not match above.
    SearchPattern("Error",
                  'Error',
                  r'.*(?i)ERROR:\s+'
                  r'('
                  r'(?!0)'  # Do not match "Error: 0", rdar://problem/31564106
                  r'(?!AddressSanitizer)'  # Covered by ASANError, rdar://problem/31719510
                  r'(?!Cannot find device named)'  # Covered by Error Device Name, rdar://problem/32081011
                  r'(?!: True$)'  # Nothing should match on: "Match found for :error: : True"
                  r')'
                  r'(?P<error_msg>.*)',
                  u'{name}: {error_msg}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("GPU Automerger Conflict",
                  'GenericNLP',
                  r'Failures in Automerger from (?P<from_branch>\S+) to (?P<to_branch>\S+)',
                  u'{name}: {from_branch} to {to_branch}',
                  Severity.EXPECTED_ERROR),

    SearchPattern("Kinit Error",
                  'GenericNLP',
                  r'kinit:\s(?P<msg>.*)',
                  u'{name}: {msg}',
                  Severity.UNEXPECTED_ERROR),

    SearchPattern("Install-Xcode",
                  'GenericNLP',
                  r'\((?P<kind>(WARNING|CRITICAL))\)\s(?P<msg>.*)',
                  u'{name} {kind}: {msg}',
                  Severity.UNEXPECTED_ERROR),
]
