"""Utilities for accessing stuff from llvmlab."""

import json
import os
import re
import shutil
import time

from . import shell
from . import util
from . import gcs

from util import fatal


class BuilderMap(object):
    # Expire the buildermap after 24 hours.
    expiration_time = 24 * 60 * 60

    @classmethod
    def frompath(klass, path):
        with open(path) as f:
            data = json.load(f)
        return klass(data['builders'], data['timestamp'])

    def __init__(self, builders, timestamp):
        self.builders = builders
        self.timestamp = timestamp

    def topath(self, path):
        with open(path, 'w') as f:
            data = {'builders': self.builders,
                    'timestamp': self.timestamp}
            json.dump(data, f, indent=2)

    def is_expired(self):
        return time.time() > self.timestamp + self.expiration_time

BUILD_NAME_REGEX = re.compile(
    r"((apple-)?clang)-([0-9]+)(\.([0-9]+))?(\.([0-9]+))?"
    r"-([A-Z][A-Za-z]+)(\.(.*))?")


class Build(object):
    @staticmethod
    def frombasename(str, url=None):

        str = os.path.basename(str)
        revision = revision_prefix = sha = timestamp = build = None

        # Check if this is a BNI style build.
        m = BUILD_NAME_REGEX.match(str)
        if m:
            name, _, major_str, _, minor_str, _, micro_str, build, \
                _, suffix = m.groups()
            revision = [int(major_str)]
            if minor_str:
                revision.append(int(minor_str))
                if micro_str:
                    revision.append(int(micro_str))
            return Build(name, None, tuple(revision), None, None, build, suffix)

        if '.' in str:
            str, suffix = str.split('.', 1)
        else:
            suffix = None

        m = re.match(r'(.*)-b([0-9]+)', str)
        if m:
            str, build = m.groups()
            build = int(build)

        m = re.match(r'(.*)-t([0-9-]{8,10}_[0-9-]{6,8})', str)
        if m:
            str, timestamp = m.groups()

        m = re.match(r'(.*)-d([0-9]+)-(.*)', str)
        if m:
            str, revision, sha = m.groups()
            revision = int(revision)
            revision_prefix = 'd'

        m = re.match(r'(.*)-r([0-9]+)', str)
        if m:
            str, revision = m.groups()
            revision = int(revision)
            revision_prefix = 'r'

        return Build(str, revision_prefix, revision, sha, timestamp,
                     build, suffix, url)

    @staticmethod
    def fromdata(data):
        return Build(data['name'], data['revision'], data['timestamp'],
                     data['build'], data['suffix'])

    def todata(self):
        return {'name': self.name,
                'revision': self.revision,
                'sha': self.sha,
                'timestamp': self.timestamp,
                'build': self.build,
                'suffix': self.suffix}

    def __init__(self, name, revision_prefix, revision, sha, timestamp,
                 build, suffix, url):
        self.name = name
        self.revision_prefix = revision_prefix
        self.revision = revision
        self.sha = sha
        self.timestamp = timestamp
        self.build = build
        self.suffix = suffix
        self.url = url

    def tobasename(self, include_suffix=True):
        basename = self.name
        if self.revision is not None:
            if isinstance(self.revision, (tuple, list)):
                basename += '-' + '.'.join(str(r) for r in self.revision)
            else:
                assert isinstance(self.revision, int)
                basename += '-%s%d' % (self.revision_prefix, self.revision)
        if self.sha is not None:
            basename += '-%s' % self.sha
        if self.timestamp is not None:
            basename += '-t%s' % self.timestamp
        if self.build is not None:
            if isinstance(self.build, str):
                basename += '-' + self.build
            else:
                basename += '-b%d' % self.build
        if include_suffix and self.suffix is not None:
            basename += '.%s' % self.suffix
        return basename

    def __repr__(self):
        return "%s%r" % (self.__class__.__name__,
                         (self.name, self.revision, self.sha, self.timestamp,
                          self.build, self.suffix))

    def __cmp__(self, other):
        return cmp((self.revision, self.timestamp,
                    self.build, self.suffix, self.name),
                   ((other.revision, other.timestamp,
                    other.build, other.suffix, other.name)))


def load_builder_map(reload=False):
    """
    load_builder_map() -> BuilderMap

    Load a map of builder names to the server url that holds those artifacts.
    """

    prefs = util.get_prefs()

    # Load load the builder map if present (and not reloading)
    data_path = os.path.join(prefs.path, "ci")
    buildermap_path = os.path.join(data_path, "build_map.json")
    if not reload and os.path.exists(buildermap_path):
        buildermap = BuilderMap.frompath(buildermap_path)

        # If the buildermap is not out-of-date, return it.
        if not buildermap.is_expired():
            return buildermap

    # Otherwise, we didn't have a buildermap or it is out of date, compute it.
    builders = {}
    for build in gcs.fetch_builders():
        builders[build] = build

    # Create the buildermap and save it.
    buildermap = BuilderMap(builders, time.time())
    if not os.path.exists(data_path):
        shell.mkdir_p(data_path)
    buildermap.topath(buildermap_path)

    return buildermap


def fetch_builders():
    """
    fetch_builders() -> [builder-name, ...]

    Get a list of available builders.
    """

    # Handle only_use_cache setting.
    prefs = util.get_prefs()
    if prefs.getboolean("ci", "only_use_cache"):
        cache_path = os.path.join(prefs.path, "ci", "build_cache")
        return sorted(os.listdir(cache_path))

    # Otherwise, fetch the builder map.
    return sorted(load_builder_map().builders.keys())


def fetch_builds(name):
    """
    fetch_builds(name) -> [(path, revision, build), ...]

    Get a list of available builds for the named builder.
    """
    # Handle only_use_cache setting.
    prefs = util.get_prefs()
    if prefs.getboolean("ci", "only_use_cache"):
        cache_path = os.path.join(prefs.path, "ci", "build_cache")
        cache_build_path = os.path.join(cache_path, name)
        items = os.listdir(cache_build_path)
        assert False, "Unimplemented?" + str(items)
    # Otherwise, load the builder map.
    buildermap = load_builder_map()

    # If the builder isn't in the builder map, do a forced load of the builder
    # map.
    if name not in buildermap.builders:
        buildermap = load_builder_map(reload=True)

    # If the builder doesn't exist, report an error.
    builder_artifacts = buildermap.builders.get(name)
    if builder_artifacts is None:
        fatal("unknown builder name: %r" % (name,))

    # Otherwise, load the builder list.
    server_builds = gcs.fetch_builds(builder_artifacts)
    builds = []
    for path in server_builds['items']:
        build = Build.frombasename(path['name'], path['mediaLink'])

        # Ignore any links which don't at least have a revision component.
        if build.revision is not None:
            builds.append(build)

    # If there were no builds, report an error.
    if not builds:
        fatal("builder %r may be misconfigured (no items)" % (name,))

    # Sort the builds, to make sure we return them ordered properly.
    builds.sort()

    return builds


def fetch_build_to_path(builder, build, root_path, builddir_path):
    path = build.tobasename()

    # Check whether we are using a build cache and get the cached build path if
    # so.
    prefs = util.get_prefs()
    cache_build_path = None
    if prefs.getboolean("ci", "cache_builds"):
        cache_path = os.path.join(prefs.path, "ci", "build_cache")
        cache_build_path = os.path.join(cache_path, builder, path)

    # Copy the build from the cache or download it.
    if cache_build_path and os.path.exists(cache_build_path):
        shutil.copy(cache_build_path, root_path)
    else:
        # Load the builder map.
        buildermap = load_builder_map()

        # If the builder isn't in the builder map, do a forced reload of the
        # builder map.
        if builder not in buildermap.builders:
            buildermap = load_builder_map(reload=True)

        # If the builder doesn't exist, report an error.
        builder_artifacts = buildermap.builders.get(builder)
        if builder_artifacts is None:
            fatal("unknown builder name: %r" % (builder,))

        # Otherwise create the build url.
        gcs.get_compiler(build.url, root_path)

        # Copy the build into the cache, if enabled.
        if cache_build_path is not None:
            shell.mkdir_p(os.path.dirname(cache_build_path))
            shutil.copy(root_path, cache_build_path)

    # Create the directory for the build.
    os.mkdir(builddir_path)

    # Extract the build.
    if shell.execute(['tar', '-xf', root_path, '-C', builddir_path]):
        fatal('unable to extract %r to %r' % (root_path, builddir_path))
