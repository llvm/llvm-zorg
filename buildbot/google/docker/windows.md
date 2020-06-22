# Overview

Running a Windows buildbot differs from Linux a bit. So this document will give 
hints on the differences.

# Create VM
To create a new Dockerfile and you do not have a local Windows machine, create 
a VM in the the cloud.

* Use the latest Windows image with "Desktop experience" in the description.
* Use something with at least 16 cores, to get reasonable build speed while 
  testing your images.
* Get 200GB of persistent SSD, this is much faster than the normal presistent 
  storage.
* In the "Cloud API access scopes" select "Read Write" for "Storage" to be able
  to upload docker images form the VM.

# setup your workstation
For frequent access to your Windows VM it's conveneint to install Remmina, a 
remote desktop client for Linux, to connect the the Windows VM. 

# Configure the VM
1. install [Chocolately](https://chocolatey.org/docs/installation) as package 
   manager.
1. Install your development tools, a good starting point is:
    ```
    choco install -y git vscode googlechrome arcanist vim
    ``
1. Setup your github account and push access. Start "Git bash" and run 
   `ssh-keygen`, upload your public key to Github.
1. Setup your Phabricator account for `arc diff`.
1. `git clone ssh://git@github.com/llvm/llvm-zorg.git`
1. To install docker, run in an powershell with admin rights:
    ```powershell
    Install-PackageProvider -Name NuGet -Force
    Install-Module -Name DockerMsftProvider -Repository PSGallery -Force
    Install-Package -Name docker -ProviderName DockerMsftProvider -Force
    sc.exe config docker start=delayed-auto
    ```
    Then reboot your VM to start the Docker service.
1. Maybe disable Windows Defender anti vrius "realtime protection" to get better
   IO performance.
1. Install [Google Cloud SDK](https://cloud.google.com/sdk/install). Installing
   via chocolately is sometimes broken. Then run `gcloud auth login` and 
   `gcloud auth configure-docker` to be able to push images to the registry.
1. Create a file `token` somewhere and store your worker password there. You 
   will need this to test your worker locally.

# General Hints

## Get ideas from LLVM premerge-checks
[Premerge-testing](https://github.com/google/llvm-premerge-checks/) is also 
running LLVM builds on Windows. You might be able to get some ideas from there.

## Bash on Windows
Git on Windows includes a bash. Right-click the Start menu und launch a
"Windows Powershell (Admin)" (with admin rights, as docker requires that) and 
run `bash` from there. Then you should be able to use the helper scripts 
(e.g. `build_run.sh`) on Windows as well.

## Resource Usage
If Windows seems stuck, use the `Resource Monitor` to check what the processes
are doing. If you need even more insight, e.g. debugging builds or test, use the
`Process Explorer` (`choco install procexp`) to figure out what's going on.

## Windows base image with Visual Studio 2019
Reuse the `windows-base-vscode2019` image, it contains everything you need to
build and test with Visual Studio 2019.
