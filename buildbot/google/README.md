# LLVM buildbot workers configuration

This folder contains some of the configuration of the buildbots managed
at Google. The workers are deployed on Google Cloud.

# The cloud stack

To deploy build bots workers, we need to create a bunch of virtual machines 
on Google Cloud. There are multiple ways to do this. *Terraform* is convenient 
as it offers to declare the required machines in config files and then 
create/update the machines in the cloud. 

This way we have version control over the infrastructure 
and we can review changes before applying them. In case something goes wrong, 
we can easily revert changes. It also allows us to copy & paste parts of the 
infrastructure for additional machines.

Internally, Terraform is using *Kubernetes* to manage the deployment of software 
to machines. The software installed on the build machines is defined
in *Docker* images. An image is a (layered) file system with all the tools and
settings required for the worker. 

The images are stored in a "registry" (gcr.io in this case) and are then 
pulled from the machines where they are executed. The 
images can be versioned so that we can pick exactly which version of the image
we want to run.

The contents of a Docker image is again defined in a config file called 
`Dockerfile`. A Dockerfile is a sort of script defining on how to install and
configure the software for a machine. We keep those files in this repository as 
well so we can review changes and revert changes if something breaks.

The docker images also allow contributors to reproduce a failing test locally, 
as they will get the same machine configuration as used on the server.

# Folder structure

* `docker` - Dockerfiles for the workers and some scripting
* `terraform` - cluster configuration and deployment
* `config.sh` - variables used in other scripts
* `gcloud_config.sh` - configure cloud tooling

# Setting up a new buildbot worker

These are the step-by-step instructions to set up a new buildbot in this framwork.
In general follow the 
[instructions in the LLVM documentation](https://llvm.org/docs/HowToAddABuilder.html) 
and a look at the dockumentation in the subfolders of 
[this page](https://github.com/llvm/llvm-zorg/tree/master/buildbot/google).

In addition to that, these are the specific steps to use this framework to host
your worker:

1. Clone [llvm-zorg](https://github.com/llvm/llvm-zorg/) and make sure you have 
   write access there.
1. Make sure you have access to the Google-internal `Sanizier-Bots` project on 
   GCP. If you don't have access, contact Christian Kühnel.
1. Make yourself familiar with the basics of Docker, Kubernetes and Terraform. 
   You will mostly be doing copy-and-paste, but it's helpful to understand the
   basic concept of these tools.
1. Create a docker image in which you can build the config you want and store it
   next to the [existing images](https://github.com/llvm/llvm-zorg/tree/master/buildbot/google/docker).
   Feel free to copy-and-paste from the these imagess. 
   There are also [some other images](https://github.com/llvm/llvm-project/search?q=dockerfile) 
   in the llvm-project repo, that might be useful.
1. Upload your image to the internal docker registry using the `build_deploy.sh` 
   [script](https://github.com/llvm/llvm-zorg/blob/master/buildbot/google/docker/build_deploy.sh).
   The image will then be deployed from this registry.
1. Extend the 
   [terraform configuration](https://github.com/llvm/llvm-zorg/tree/master/buildbot/google/terraform) 
   to create a machine that matches your needs and a deployment to run the your
   container on that machine. Then deploy the new configuration using terraform.
1. Check on GCP to see if your new node pool and deployment were as expected. 
   Also check the logs for anything unexpected.
1. Follow the [LLVM instructions](https://llvm.org/docs/HowToAddABuilder.html) 
   to get your worker connected to the server. 
   It's recommended to first connect to the staging server (port 9994) until 
   your worker is stable and then move it to the production server (port 9990).