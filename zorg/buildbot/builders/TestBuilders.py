from buildbot import process, steps
from buildbot.steps.shell import Configure, ShellCommand

def getRandomFailFactory(probability=.5):
    p = float(probability)
    command = ["python", "-c",
               """import sys, random; """ +
               """sys.exit(random.random() < %.2f)""" % p]

    f = process.factory.BuildFactory()
    f.addStep(steps.shell.ShellCommand(name="fail.random", command=command,
                                       haltOnFailure=True,
                                       description="fail.random",
                                       workdir="."))
    return f
