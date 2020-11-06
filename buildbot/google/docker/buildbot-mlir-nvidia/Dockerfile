#===-- Dockerfile --------------------------------------------------------===//
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===----------------------------------------------------------------------===//
# Docker image used for the mlir-nvidia builder
# 
# Environment variables configurable at runtime:
#    BUILDBOT_PORT - server port to connect to
#===----------------------------------------------------------------------===//

# Use the image from NVIDIA as base
FROM nvidia/cuda:10.2-base-ubuntu18.04


# install build tools
RUN apt-get update; \
    apt-get install -y software-properties-common apt-transport-https ca-certificates \
      clang-8 lld-8 ninja-build git wget gnupg ccache \
      python python-pip python-psutil pybind11-dev ;\
    update-alternatives --install /usr/bin/clang clang /usr/bin/clang-8 100 ;\
    update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-8 100 ;\
    update-alternatives --install /usr/bin/lld lld /usr/bin/lld-8 100

# install cuda
# avoid popups for keyboard configurations
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y cuda

# Ubuntu ships with old cmake version, install the latest one
# from https://apt.kitware.com/
RUN wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | \
       gpg --dearmor - | \
       tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null ;\
    apt-add-repository 'deb https://apt.kitware.com/ubuntu/ bionic main' ;\
    apt-get update ;\
    apt-get install -y cmake

# Get the Vulkan SDK from LunarG. The CUDA meta package already pulls in NVIDIA
# Vulkan ICD.
RUN wget -qO - http://packages.lunarg.com/lunarg-signing-key-pub.asc 2>/dev/null | \
       apt-key add - ;\
    wget -qO /etc/apt/sources.list.d/lunarg-vulkan-1.2.141-bionic.list \
       http://packages.lunarg.com/vulkan/1.2.141/lunarg-vulkan-1.2.141-bionic.list;\
    apt-get update ;\
    apt-get install -y vulkan-sdk

# install (old) build bot version
# this version of build bot requires python2!
RUN pip install buildbot-slave==0.8.11

# Volume to mount secrets into the container
VOLUME /secrets

# create user account, some test fail if run as root
RUN useradd buildbot --create-home
WORKDIR /home/buildbot

# copy startup script
COPY run.sh /home/buildbot/
RUN chmod a+rx /home/buildbot/run.sh

USER buildbot
ENV WORKER_NAME="mlir-nvidia"

# Allow the server port of this agent to be configurable during deployment.
# This way we can connect the same image to production and integration. 
# Ports:
#   9990 - production
#   9994 - integration
ENV BUILDBOT_PORT="9990"

# Set up buildbot host and maintainer info.
RUN mkdir -p "${WORKER_NAME}/info/" ;\
    echo "Christian Kühnel <kuhnel@google.com>" > "${WORKER_NAME}/info/admin"

CMD ./run.sh
