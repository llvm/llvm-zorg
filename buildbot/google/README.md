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
