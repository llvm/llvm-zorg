#!/usr/bin/python2.7
"""
Dependency manager for llvm CI builds.

We have complex dependencies for some of our CI builds. This will serve
as a system to help document and enforce them.

Developer notes:

- We are trying to keep package dependencies to a minimum in this project. So it
does not require an installer. It should be able to be run as a stand alone script
when checked out of VCS. So, don't import anything not in the Python 2.7
standard library.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import collections
import json
import platform
import re
import subprocess

import os

try:
    # noinspection PyUnresolvedReferences
    from typing import List, Text, Union, Dict, Type, Optional  # noqa
except ImportError as e:
    pass  # Not really needed at runtime, so okay to not have installed.


VERSION = '0.1'
"""We have a built in version check, so we can require specific features and fixes."""


class Version(object):
    """Model a version number, which can be compared to another version number.

    Keeps a nice looking text version around as well for printing.

    This abstraction exists to make some of the more complex comparisons easier,
    as well as collecting and printing versions.

    In the future, we might want to have some different comparison,
    for instance, 4.0 == 4.0.0 -> True.

    """

    def __init__(self, text):
        """Create a version from a . separated version string."""
        self.text = text
        self.numeric = [int(d) for d in text.split(".")]

    def __gt__(self, other):
        """Compare the numeric representation of the version."""
        return self.numeric.__gt__(other.numeric)

    def __lt__(self, other):
        """Compare the numeric representation of the version."""
        return self.numeric.__lt__(other.numeric)

    def __eq__(self, other):
        """Compare the numeric representation of the version."""
        return self.numeric.__eq__(other.numeric)

    def __le__(self, other):
        """Compare the numeric representation of the version."""
        return self.numeric.__le__(other.numeric)

    def __ge__(self, other):
        """Compare the numeric representation of the version."""
        return self.numeric.__ge__(other.numeric)

    def __repr__(self):
        """Print the original text representation of the Version."""
        return "v{}".format(self.text)


class Dependency(object):
    """Dependency Abstract base class."""

    def __init__(self, line, str_kind):
        """Save line information.

        :param line: A parsed Line object that contains the raw dependency deceleration.
        :param str_kind: The determined kind of the Dependency.
        """
        # type: (Line, Text) -> object
        self.line = line
        self.str_kind = str_kind
        self.installed_version = None

    def parse(self):
        """Read the input line and prepare to verify this dependency.

        Raise a MalformedDependencyError if three is something wrong.

        Should return nothing, but get the dependency ready for verification.
        """
        raise NotImplementedError()

    def verify(self):
        # type: () -> bool
        """Determine if this dependency met.

        :returns: True when the dependency is met, otherwise False.
        """
        raise NotImplementedError()

    def inject(self):
        """If possible, modify the system to meet the dependency."""
        raise NotImplementedError()

    def verify_and_act(self):
        """Parse, then verify and trigger pass or fail.

        Extract that out here, so we don't duplicate the logic in the subclasses.
        """
        met = self.verify()
        if met:
            self.verify_pass()
        else:
            self.verify_fail()

    def verify_fail(self):
        """When dependency is not met, raise an exception.

        This is the default behavior; but I want the subclasses to be able
        to change it.
        """
        raise MissingDependencyError(self, self.installed_version)

    def verify_pass(self):
        """Print a nice message that the dependency is met.

        I'm not sure we even want to print this, but we will for now. It might
        be to verbose.  Subclasses should override this if wanted.
        """
        print("Dependency met", str(self))


class MalformedDependency(Exception):
    """Raised when parsing a dependency directive fails.

    This is situations like the regexes not matching, or part of the dependency directive missing.

    Should probably record more useful stuff, but Exception.message is set. So we can print it later.
    """

    pass


def brew_cmd(command):
    # type: (List[Text]) -> List[Dict[Text, object]]
    """Help run a brew command, and parse the output.

    Brew has a json output option which we use.  Run the command and parse the stdout
    as json and return the result.
    :param command: The brew command to execute, and parse the output of.
    :return:
    """
    assert "--json=v1" in command, "Must pass JSON arg so we can parse the output."
    out = subprocess.check_output(command)
    brew_info = json.loads(out)
    return brew_info


class MissingDependencyError(Exception):
    """Fail verification with one of these when we determine a dependency is not met.

    For each dependency, we will print a useful message with the dependency line as well as the
    reason it was not matched.
    """

    def __init__(self, dependency, installed=None):
        # type: (Dependency, Optional[Text]) -> None
        """Raise when a dependency is not met.

        This exception can be printed as the error message.

        :param dependency: The dependency that is not being met.
        :param installed: what was found to be installed instead.
        """
        # type: (Dependency, Union[Text, Version]) -> None
        super(MissingDependencyError, self).__init__()
        self.dependency = dependency
        self.installed = installed

    def __str__(self):
        """For now, we will just print these as our error message."""
        return "missing dependency: {}, found {} installed, requested from {}".format(self.dependency,
                                                                                      self.installed,
                                                                                      self.dependency.line)


def check_version(installed, operator, requested):
    """Check that the installed version does the operator of the requested.

    :param installed: The installed Version of the requirement.
    :param operator: the text operator (==, <=, >=)
    :param requested: The requested Version of the requirement.
    :return: True if the requirement is satisfied.
    """
    # type: (Version, Text, Version) -> bool

    dependency_met = False
    if operator == "==" and installed == requested:
        dependency_met = True
    if operator == "<=" and installed <= requested:
        dependency_met = True
    if operator == ">=" and installed >= requested:
        dependency_met = True
    return dependency_met


class ConMan(Dependency):
    """Version self-check of this tool.

    In case we introduce something in the future, the dep files can
    be made to depend on a specific version of this tool.  We will
    increment the versions manually.

    """

    conman_re = re.compile(r'(?P<command>\w+)\s+(?P<operator>>=|<=|==)\s*(?P<version_text>[\d.-_]+)')
    """For example: config_manager <= 0.1"""

    def __init__(self, line, kind):
        """Check that this tool is up to date."""
        super(ConMan, self).__init__(line, kind)
        self.command = None
        self.operator = None
        self.version = None
        self.version_text = None
        self.installed_version = None

    def parse(self):
        """Parse dependency."""
        text = self.line.text
        match = self.conman_re.match(text)
        if not match:
            raise MalformedDependency("Expression does not compile in {}: {}".format(self.__class__.__name__,
                                                                                     self.line))
        self.__dict__.update(match.groupdict())

        self.version = Version(self.version_text)

    def verify(self):
        """Verify the version of this tool."""
        self.installed_version = Version(VERSION)

        return check_version(self.installed_version, self.operator, self.version)

    def inject(self):
        """Can't really do much here."""
        pass

    def __str__(self):
        """Show as dependency and version."""
        return "{} {}".format(self.str_kind, self.version)


class HostOSVersion(Dependency):
    """Use Python's platform module to get host OS information and verify.

    Wew can only verify, but not inject for host OS version.
    """

    conman_re = re.compile(r'(?P<command>\w+)\s+(?P<operator>>=|<=|==)\s*(?P<version_text>[\d.-_]+)')

    def __init__(self, line, kind):
        """Parse and Verify host OS version using Python's platform module.

        :param line: Line with teh Dependencies deceleration.
        :param kind: the dependency kind that was detected by the parser.
        """
        # type: (Line, Text) -> None
        super(HostOSVersion, self).__init__(line, kind)
        self.command = None
        self.operator = None
        self.version = None
        self.version_text = None
        self.installed_version = None

    def parse(self):
        """Parse dependency."""
        text = self.line.text
        match = self.conman_re.match(text)
        if not match:
            raise MalformedDependency("Expression does not compile in {}: {}".format(self.__class__.__name__,
                                                                                     self.line))
        self.__dict__.update(match.groupdict())

        self.version = Version(self.version_text)

    def verify(self):
        """Verify the request host OS version holds."""
        self.installed_version = Version(platform.mac_ver()[0])

        return check_version(self.installed_version, self.operator, self.version)

    def inject(self):
        """Can't change the host OS version, so not much to do here."""
        pass

    def __str__(self):
        """For printing in error messages."""
        return "{} {}".format(self.str_kind, self.version)


class Brew(Dependency):
    """Verify and Inject brew package dependencies."""

    # brew <package> <operator> <version>.  Operator may not have spaces around it.
    brew_re = re.compile(r'(?P<command>\w+)\s+(?P<package>\w+)\s*(?P<operator>>=|<=|==)\s*(?P<version_text>[\d.-_]+)')

    def __init__(self, line, kind):
        # type: (Line, Text) -> None
        """Parse and verify brew package is installed.

        :param line: the Line with the deceleration of the dependency.
        :param kind: the detected dependency kind.
        """
        super(Brew, self).__init__(line, kind)
        self.command = None
        self.operator = None
        self.package = None
        self.version = None
        self.version_text = None
        self.installed_version = None

    def parse(self):
        """Parse this dependency."""
        text = self.line.text
        match = self.brew_re.match(text)
        if not match:
            raise MalformedDependency("Expression does not compile in {}: {}".format(self.__class__.__name__,
                                                                                     self.line))
        self.__dict__.update(match.groupdict())

        self.version = Version(self.version_text)

    def verify(self):
        """Verify the packages in brew match this dependency."""
        try:
            brew_package_config = brew_cmd(['/usr/local/bin/brew', 'info', self.package, "--json=v1"])
        except OSError:
            raise MissingDependencyError(self, "Can't find brew command")
        version = None
        for brew_package in brew_package_config:
            name = brew_package['name']
            linked_keg = brew_package["linked_keg"]

            install_info = brew_package.get('installed')
            for versions in install_info:
                if linked_keg == versions['version']:
                    version = versions['version']
            if name == self.package:
                break
        if not version:
            # The package is not installed at all.
            raise MissingDependencyError(self, "nothing")
        self.installed_version = Version(version)
        return check_version(self.installed_version, self.operator, self.version)

    def inject(self):
        """Not implemented."""
        raise NotImplementedError()

    def __str__(self):
        """Dependency kind, package and version, for printing in error messages."""
        return "{} {} {}".format(self.str_kind, self.package, self.version)


class Xcode(Dependency):
    """Verify and Inject Xcode version dependencies."""

    # xcode <operator> <version>.  Operator may not have spaces around it.
    xcode_dep_re = re.compile(r'(?P<command>\w+)\s+(?P<operator>>=|<=|==)\s*(?P<version_text>[\d.-_]+)')

    def __init__(self, line, kind):
        # type: (Line, Text) -> None
        """Parse and xcode version installed.

        :param line: the Line with the deceleration of the dependency.
        :param kind: the detected dependency kind.
        """
        super(Xcode, self).__init__(line, kind)
        self.command = None
        self.operator = None
        self.version = None
        self.version_text = None
        self.installed_version = None

    def parse(self):
        """Parse this dependency."""
        text = self.line.text
        match = self.xcode_dep_re.match(text)
        if not match:
            raise MalformedDependency("Expression does not compile in {}: {}".format(self.__class__.__name__,
                                                                                     self.line))
        self.__dict__.update(match.groupdict())

        self.version = Version(self.version_text)

    def verify(self):
        """Verify the installed Xcode matches this dependency."""
        installed_version_output = subprocess.check_output(['/usr/bin/xcrun', 'xcodebuild', "-version"])
        installed_version_re = re.compile(r"^Xcode\s(?P<version_text>[\d/.]+)")
        match = installed_version_re.match(installed_version_output)
        if not match:
            raise MissingDependencyError(self, "Did not find Xcode version in output:" + installed_version_output)
        version = match.groupdict().get('version_text')
        if not version:
            # The package is not installed at all.
            raise AssertionError("No version text found.")
        self.installed_version = Version(version)
        return check_version(self.installed_version, self.operator, self.version)

    def inject(self):
        """Not implemented."""
        raise NotImplementedError()

    def __str__(self):
        """Dependency kind, package and version, for printing in error messages."""
        return "{} {}".format(self.str_kind, self.version)


class Sdk(Dependency):
    """Verify and Inject Sdk version dependencies."""

    # sdk <operator> <version>.  Operator may not have spaces around it.
    sdk_dep_re = re.compile(r'(?P<command>\w+)\s+(?P<sdk>[\w/.]+)\s*'
                            r'(?P<operator>>=|<=|==)\s*(?P<version_text>[\d.-_]+)')

    def __init__(self, line, kind):
        # type: (Line, Text) -> None
        """Parse and sdk version installed.

        :param line: the Line with the deceleration of the dependency.
        :param kind: the detected dependency kind.
        """
        super(Sdk, self).__init__(line, kind)
        self.command = None
        self.sdk = None
        self.operator = None
        self.version = None
        self.version_text = None
        self.installed_version = None

    def parse(self):
        """Parse this dependency."""
        text = self.line.text
        match = self.sdk_dep_re.match(text)
        if not match:
            raise MalformedDependency("Expression does not compile in {}: {}".format(self.__class__.__name__,
                                                                                     self.line))
        self.__dict__.update(match.groupdict())

        self.version = Version(self.version_text)

    def verify(self):
        """Verify the installed Sdk matches this dependency."""
        installed_version_output = subprocess.check_output(['/usr/bin/xcrun', 'xcodebuild', "-showsdks"])
        installed_version_re = re.compile(r".*-sdk\s+(?P<sdk_text>\S+)")

        matches = [installed_version_re.match(l).groupdict()['sdk_text']
                   for l in installed_version_output.split('\n') if installed_version_re.match(l)]

        if not matches:
            raise MissingDependencyError(self, "Did not find Sdk version in output:" + installed_version_output)

        extract_version_names = re.compile(r'(?P<pre>\D*)(?P<version_text>[\d+/.]*)(?P<post>.*)')

        sdks = [extract_version_names.match(sdk_text).groupdict()
                for sdk_text in matches if extract_version_names.match(sdk_text)]

        installed_sdks = collections.defaultdict(list)
        for sdk in sdks:
            name = sdk['pre']
            if sdk.get('post'):
                name += "." + sdk.get('post')
            if sdk.get('version_text'):
                version = Version(sdk['version_text'].rstrip('.'))
            else:
                continue
            installed_sdks[name].append(version)

        if self.sdk not in installed_sdks.keys():
            raise MissingDependencyError(self, "{} not found in installed SDKs.".format(self.sdk))

        self.installed_version = installed_sdks[self.sdk]

        satisfied = [check_version(s, self.operator, self.version) for s in self.installed_version]
        return any(satisfied)

    def inject(self):
        """Not implemented."""
        raise NotImplementedError()

    def __str__(self):
        """Dependency kind, package and version, for printing in error messages."""
        return "{} {}".format(self.str_kind, self.version)


class Pip(Dependency):
    """Verify and Inject pip package dependencies."""

    # pip <package> <operator> <version>.  Operator may not have spaces around it.
    pip_re = re.compile(r'(?P<command>\w+)\s+(?P<package>\w+)\s*(?P<operator>>=|<=|==)\s*(?P<version_text>[\d.-_]+)')

    def __init__(self, line, kind):
        # type: (Line, Text) -> None
        """Parse and verify pip package is installed.

        :param line: the Line with the deceleration of the dependency.
        :param kind: the detected dependency kind.
        """
        super(Pip, self).__init__(line, kind)
        self.command = None
        self.operator = None
        self.package = None
        self.version = None
        self.version_text = None
        self.installed_version = None

    def parse(self):
        """Parse this dependency."""
        text = self.line.text
        match = self.pip_re.match(text)
        if not match:
            raise MalformedDependency("Expression does not compile in {}: {}".format(self.__class__.__name__,
                                                                                     self.line))
        self.__dict__.update(match.groupdict())

        self.version = Version(self.version_text)

    def verify(self):
        """Verify the packages in pip match this dependency."""

        try:
            pip_version = subprocess.check_output(["/usr/bin/env", "python", "-m", "pip", "--version"])
            pip_tokens = pip_version.split()
            assert pip_tokens[0] == "pip"
            pip_version = Version(pip_tokens[1])

            if pip_version < Version("9.0.0"):
                raise MissingDependencyError(self, "Version of pip too old.")

            pip_package_config = json.loads(subprocess.check_output(["/usr/bin/env",
                                                                     "python", "-m", "pip", "list", "--format=json"]))
        except (subprocess.CalledProcessError, OSError):
            raise MissingDependencyError(self, "Cannot find pip")

        installed = {p['name']: p['version'] for p in pip_package_config}  # type: Dict[Text, Text]

        package = installed.get(self.package)

        if not package:
            # The package is not installed at all.
            raise MissingDependencyError(self, "not in package list")
        self.installed_version = Version(package)
        return check_version(self.installed_version, self.operator, self.version)

    def inject(self):
        """Not implemented."""
        raise NotImplementedError()

    def __str__(self):
        """Dependency kind, package and version, for printing in error messages."""
        return "{} {} {}".format(self.str_kind, self.package, self.version)


class Device(Dependency):
    """Verify correct device is attached to this machine."""

    # device somelongudidstring.
    # We will filter dashes if they are added.
    device_re = re.compile(r'(?P<command>\w+)\s+(?P<udid>.*)')

    def __init__(self, line, kind):
        # type: (Line, Text) -> None
        """Parse and verify device is attached.

        :param line: the Line with the deceleration of the dependency.
        :param kind: the detected dependency kind.
        """
        super(Device, self).__init__(line, kind)
        self.command = None
        self.udid = None
        self.installed_version = None

    def parse(self):
        """Parse this dependency."""
        text = self.line.text
        match = self.device_re.match(text)
        if not match:
            raise MalformedDependency("Expression does not compile in {}: {}".format(self.__class__.__name__,
                                                                                     self.line))
        self.__dict__.update(match.groupdict())
        # Sometimes people put dashes in these, lets not compare with dashes.
        self.udid = self.udid.replace("-", "")

    def verify(self):
        """Verify the device is attached."""

        try:
            instruments_output = subprocess.check_output(["xcrun", "instruments", "-s", "devices"]).decode("utf-8")
        except (subprocess.CalledProcessError, OSError):
            raise MissingDependencyError(self, "Cannot find instruments")
        # Convert udids with dashes to without for comparison.
        cleaned_instruments_output = instruments_output.replace(u"-", u"")
        if self.udid not in cleaned_instruments_output:
            # The device is not in instruments.
            raise MissingDependencyError(self, "")
        return True

    def inject(self):
        """Not implemented."""
        raise NotImplementedError()

    def __str__(self):
        """Dependency kind, package and version, for printing in error messages."""
        return "{} {} {}".format(self.str_kind, self.udid, "")


dependencies_implementations = {'brew': Brew,
                                'os_version': HostOSVersion,
                                'config_manager': ConMan,
                                'xcode': Xcode,
                                'sdk': Sdk,
                                'pip': Pip,
                                'device': Device,
                                }


def dependency_factory(line):
    """Given a line, create a concrete dependency for it.

    :param line: The line with the dependency info
    :return: Some subclass of Dependency, based on what was in the line.
    """
    # type: Text -> Dependency
    kind = line.text.split()[0]
    try:
        return dependencies_implementations[kind](line, kind)
    except KeyError:
        raise MalformedDependency("Don't know about {} kind of dependency.".format(kind))


class Line(object):
    """A preprocessed line. Understands file and line number as well as comments."""

    def __init__(self, filename, line_number, text, comment):
        # type: (Text, int, Text, Text) -> None
        """Raw Line information, split into the dependency deceleration and comment.

        :param filename: the input filename.
        :param line_number: the line number in the input file.
        :param text: Non-comment part of the line.
        :param comment: Text from the comment part of the line if any.
        """
        self.filename = filename
        self.line_number = line_number
        self.text = text
        self.comment = comment

    def __repr__(self):
        """Reconstruct the line for pretty printing."""
        return "{}:{}: {}{}".format(os.path.basename(self.filename),
                                    self.line_number,
                                    self.text,
                                    " # " + self.comment if self.comment else "")


# For stripping comments out of lines.
comment_re = re.compile(r'(?P<main_text>.*)#(?P<comment>.*)')


# noinspection PyUnresolvedReferences
def _parse_dep_file(lines, filename):
    # type: (List[Text], Text) -> List[Line]
    process_lines = []
    for num, text in enumerate(lines):
        if "#" in text:
            bits = comment_re.match(text)
            main_text = bits.groupdict().get('main_text')
            comment = bits.groupdict().get('comment')
        else:
            main_text = text
            comment = None
        if main_text:
            main_text = main_text.strip()
        if comment:
            comment = comment.strip()
        process_lines.append(Line(filename, num, main_text, comment))

    return process_lines


def parse_dependencies(file_names):
    """Program logic: read files, verify dependencies.

    For each input file, read lines and create dependencies. Verify each dependency.

    :param file_names: files to read dependencies from.
    :return: The list of dependencies, each verified.
    """
    # type: (List[Text]) -> List[Type[Dependency]]
    preprocessed_lines = []
    for file_name in file_names:
        with open(file_name, 'r') as f:
            lines = f.readlines()
            preprocessed_lines.extend(_parse_dep_file(lines, file_name))

    dependencies = [dependency_factory(l) for l in preprocessed_lines if l.text]
    [d.parse() for d in dependencies]
    for d in dependencies:
        try:
            met = d.verify()
            if met:
                d.verify_pass()
            else:
                d.verify_fail()

        except MissingDependencyError as exec_info:
            print("Error:", exec_info)

    return dependencies


def main():
    """Parse arguments and trigger dependency verification."""
    parser = argparse.ArgumentParser(description='Verify and install dependencies.')
    parser.add_argument('command', help="What to do.")

    parser.add_argument('dependencies',  nargs='+', help="Path to dependency files.")

    args = parser.parse_args()

    full_file_paths = [os.path.abspath(path) for path in args.dependencies]

    parse_dependencies(full_file_paths)

    return True


if __name__ == '__main__':
    main()
