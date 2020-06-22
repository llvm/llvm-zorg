This folder contains the Dockerfiles and scripts used for some of the 
buildbot workers. 

# Scripts

This folder also contains some scripts that are useful in working with the
docker images.

## build_run.sh
Build a docker image and run it locally

## build_deploy.sh
Build a docker image, increment the version number, tag it and upload it to
the registry. This updates the `VERSION` file to track the version numbers.

# Secrets

The buildbot workers need a password to authenticate with the buildbot server. 
This password needs to be kept a secert. The usual way to handle it is to store
the secrets in a secure place and during runtime mount that secure place into 
the container. The secret file shall just contain the password in plain text.

Kubernetes offers a [mechanism to handle secrets](https://kubernetes.io/docs/concepts/configuration/secret/).

# Setting up Windows VM for development
See [windows.md](windows.md).
