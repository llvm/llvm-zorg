import buildbot
from buildbot.steps.shell import ShellCommand
from buildbot.process.properties import WithProperties

def addDarwinChrootSetup(f, build_root_images=[],
                         build_root_name="BuildRoot", clean_build_root=False,
                         dirs_to_clean=[]):
    # Destroy the old build root, if requested.
    if clean_build_root:
        f.addStep(ShellCommand(name="rm.buildroot",
                               command=["sudo", "rm", "-rf", build_root_name],
                               haltOnFailure=False,
                               description="rm build root",
                               workdir="."))

    # Clear out any requested directories.
    for i,name in enumerate(dirs_to_clean):
        f.addStep(ShellCommand(name="rm.buildroot_dir.%d" % i,
                               command=["sudo", "rm", "-rf", name],
                               description=["rm build root",repr(name)],
                               haltOnFailure=True,
                               workdir=build_root_name))

    # Unmount /dev, so we don't try to restore it.
    #
    # FIXME: This shouldn't fail, except that it might not exist.
    f.addStep(ShellCommand(name="chroot.init.umount.devfs",
                           command=["sudo", "umount", "dev"],
                           warnOnFailure=True,
                           flunkOnFailure=False,
                           haltOnFailure=False,
                           description="umount devfs",
                           workdir=build_root_name))

    # For each image...
    for i,image in enumerate(build_root_images):
        # Setup the build root we will build projects in.
        f.addStep(ShellCommand(
                name="attach.buildroot",
                command=("hdiutil attach -noverify -plist -mountrandom . %s | "
                         "tee mount_info.plist") % image,
                description="attach build root image",
                haltOnFailure=True,
                workdir="mounts"))

        mount_point_property = "mount_point.%d" % i
        f.addStep(buildbot.steps.shell.SetProperty(
                name="get.mount_point.%d" % i,
                property=mount_point_property,
                command=["python", "-c", """\
import plistlib
data = plistlib.readPlist(open("mount_info.plist"))
items = [i['mount-point'] for i in data.get('system-entities',[])
         if 'mount-point' in i]
if len(items) != 1:
  raise SystemExit,'unable to determine mount point!'
print items[0]
"""],
                description="get mount point",
                haltOnFailure=True,
                workdir="mounts"))

        # Restore the build root.
        cmd = ["sudo", "rsync", "-arv"]
        if i == 0:
            cmd.append("--delete")
        cmd.extend([WithProperties("%%(%s)s/" % mount_point_property), "./"])
        f.addStep(ShellCommand(
                name="init.buildroot.%d" % i,
                command=cmd,
                warnOnFailure=True,
                flunkOnFailure=False,
                haltOnFailure=False,
                description="init build root",
                workdir=build_root_name))

        # Unmount the image.
        f.addStep(ShellCommand(
                name="detach.buildroot.%d" % i,
                command=["hdiutil", "detach",
                         WithProperties("%%(%s)s" % mount_point_property)],
                warnOnFailure=True,
                flunkOnFailure=False,
                haltOnFailure=False,
                description="detach build root image",
                workdir="."))

    # Remove the buildroot shared cache.
    f.addStep(ShellCommand(name="chroot.init.rm.cache",
                           command=["sudo", "rm", "-rf", "var/db/dyld"],
                           haltOnFailure=True,
                           description="rm chroot shared cache",
                           workdir=build_root_name))

    # Initialize /dev/.
    f.addStep(ShellCommand(name="chroot.init.mount.devfs",
                           command=["sudo", "mount", "-t", "devfs",
                                    "devfs", "dev"],
                           haltOnFailure=True,
                           description="mount devfs",
                           workdir=build_root_name))
