#!/usr/bin/env python3
#
# Search a given log file for patterns defined in patterns.py and produce a
# HTML snippet for the matching lines.
#
# Ideas for improvements:
# - Group together similar issues. A good rule would be by description
#   so if a warning/error happens for several source files in the project
#   we would only list it as a single issue. Should extend the description
#   with the count (i.e. "warning: bla blup [20 times]")
#   Could merge the first 2 or 3 instances to show in the details section.
# - Write highlighted html log with all matches highlighted/linked?
from html import escape
from collections import deque
from patterns import default_search
import os.path
import re
import sys


_JENKINS_POOL_PATTERN = r'\[.*]\s'
_JENKINS_POOL_REGEX = re.compile('^'+_JENKINS_POOL_PATTERN)


class _Matcher(object):
    '''Matching engine. Keeps data structures to match a single line against
    a fixed list of patterns.'''
    def __init__(self, patterns):
        # Create a combined main regex combining all patterns.
        combined = ''
        merge = ''
        for pattern in patterns:
            # Convert named groups into anonymous ones to avoid name clashes.
            p = pattern.pattern
            p = re.sub(r'\(\?P<[^>]+>', '(?:', p)
            combined += merge
            combined += '(?:%s)' % p
            merge = '|'
        self.combined_regex = re.compile(combined)
        self.patterns = patterns

    def match_line(self, line):
        if line[0] == '[':
            line = _JENKINS_POOL_REGEX.sub("", line, 1)
        if not self.combined_regex.match(line):
            return None
        for pattern in default_search:
            m = pattern.regex.search(line)
            if m:
                return (pattern, m.groupdict())
        return None


class _Match(object):
    '''Used for the results of a match.'''


def _match_with_context(matcher, istream, lines_before, lines_after):
    prev_lines = deque()
    needs_lines = deque()
    for line in istream:
        if len(needs_lines) > 0:
            for match in needs_lines:
                match.after.append(line)
            match = needs_lines[0]
            if len(match.after) == lines_after:
                needs_lines.popleft()
                yield match

        m = matcher.match_line(line)
        if m is not None:
            pattern, matches = m
            match = _Match()
            match.line = line
            match.pattern = pattern
            match.matches = matches
            match.before = list(prev_lines)
            match.after = []
            needs_lines.append(match)

        prev_lines.append(line)
        if len(prev_lines) > lines_before:
            prev_lines.popleft()

    for match in needs_lines:
        yield match


def _match_summary(match):
    template = match.pattern.html_template
    sub = {}
    sub.update(match.pattern.__dict__)
    sub.update(match.matches)
    if 'file_name' in sub:
        sub['file_name'] = os.path.basename(sub['file_name'])
    return escape(template.format(**sub))


def _sort_by_severity(matches):
    return sorted(matches, key=lambda m: m.pattern.severity)


def _make_html_snippets(matches, limit):
    def _prepare_lines(lines):
        string = escape(''.join(lines))
        if len(string) > 0 and string[-1] == '\n':
            string = string[:-1]
        return string

    matches = list(matches)
    if len(matches) == 0:
        return False

    sys.stdout.write('<div style="margin-bottom: 2em;">Found %d issues:</div>\n' % (len(matches), ))

    limited = False
    if len(matches) > limit:
        # Sort by severity so we cut the less severe ones.
        matches = _sort_by_severity(matches)
        matches = matches[:limit]
        limited = True

    for match in matches:
        match.summary = _match_summary(match)
        match.before = _prepare_lines(match.before)
        match.after = _prepare_lines(match.after)
        match.line = _prepare_lines(match.line)
        sys.stdout.write('''\
<details class="match">
    <summary><b>{summary}</b></summary>
    <pre style="margin-bottom: 1.5em;">
{before}
<span style='color: red'>{line}</span>
{after}</pre>
</details>'''.format(**match.__dict__))

    if limited:
        sys.stdout.write('<b>... (limited to first %d issues)</b>\n' % limit)

    return True


if __name__ == '__main__':
    lines_before = 5
    lines_after = 2
    matcher = _Matcher(default_search)
    matches = _match_with_context(matcher, sys.stdin,
                                  lines_before=lines_before,
                                  lines_after=lines_after)
    limit = 12 # Limit the amount of issues we show.
    had_issues = _make_html_snippets(matches, limit)
    if had_issues:
        sys.exit(1)
