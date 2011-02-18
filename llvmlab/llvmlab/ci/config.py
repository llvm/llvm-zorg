"""
Configuration information for the CI infrastructure, for use by the dashboard.
"""

from llvmlab import util

class Phase(util.simple_repr_mixin):
    """
    A Phase object represents a single phase of the CI process, which is
    essentially a name for a group of builders which get reported in aggregate.
    """

    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        return Phase(data['name'], data['number'],
                     data['phase_builder'], data['builder_names'],
                     data['description'])

    def todata(self):
        return { 'version' : 0,
                 'name' : self.name,
                 'number' : self.number,
                 'phase_builder' : self.phase_builder,
                 'builder_names' : self.builder_names,
                 'description' : self.description}

    def __init__(self, name, number, phase_builder, builder_names, description):
        self.name = name
        self.number = number
        self.phase_builder = phase_builder
        self.builder_names = builder_names
        self.description = description

class Builder(util.simple_repr_mixin):
    """
    A Builder object stores information for an individual builder which
    participates in some phase.
    """

    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        return Builder(data['name'])

    def todata(self):
        return { 'version' : 0,
                 'name' : self.name }

    def __init__(self, name):
        self.name = name


class PublishedBuild(util.simple_repr_mixin):
    """
    A PublishedBuild records what artifacts we publicize on the primary
    dashboard home page.
    """

    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        return PublishedBuild(data['product'], data['os'],
                              data['arch'], data['archive_name'])

    def todata(self):
        return { 'version' : 0,
                 'product' : self.product,
                 'os' : self.os,
                 'arch' : self.arch,
                 'archive_name' : self.archive_name }

    def __init__(self, product, os, arch, archive_name):
        self.product = product
        self.os = os
        self.arch = arch
        self.archive_name = archive_name


class Config(util.simple_repr_mixin):
    """
    The Config object holds the current representation of the lab CI
    organization.
    """

    # FIXME: How much do we care about dealing with having the dashboard react
    # to changes in the CIConfig? Might get messy...

    @staticmethod
    def fromdata(data):
        version = data['version']
        if version != 0:
            raise ValueError, "Unknown version"

        return Config([Phases.fromdata(item)
                       for item in data['phases']],
                      [Builder.fromdata(item)
                       for item in data['builders']],
                      [PublishedBuild.fromdata(item)
                       for item in data['published_builds']])

    def todata(self):
        return { 'version' : 0,
                 'phases' : [item.todata()
                             for item in self.phases],
                 'builders' : [item.todata()
                               for item in self.builders],
                 'published_builds' : [item.todata()
                                       for item in self.published_builds] }

    def __init__(self, phases, builders, published_builds, validation_builder):
        self.phases = phases
        self.builders = builders
        self.published_builds = published_builds
        self.validation_builder = validation_builder
