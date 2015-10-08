.. _builders:

Adding your builder to llvmlab bisect
=====================================

llvmlab bisect compilers are stored on Google Cloud Storage.  There is a common
bucket called llvm-build-artifacts, within that there is a directory for each
build.  Builds can be uploaded in two ways, with authorized credentials with 
the gsutil tool, or if the builder is in lab.llvm.org, from the labmaster2
stageing server.

On the labmaster2 staging server any builds uploaded to:
``/Library/WebServer/Documents/artifacts/<buildername>/`` will be uploaded via
a cron job.  Your builders public key will need to be added to that machine.
Rsync or scp can be used to upload the files.

llvmbisect uses some regexes in llvmlab.py to parse the comiler information.
The tar file you upload will need to match those regexes. For example:
``clang-r249497-t13154-b13154.tar.gz``
