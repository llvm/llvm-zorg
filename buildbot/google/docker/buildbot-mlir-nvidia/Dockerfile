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
    python3 python3-pip python3-psutil \
    # dumb-init recommended in
    # https://hub.docker.com/r/buildbot/buildbot-worker/dockerfile
    dumb-init;\
    update-alternatives --install /usr/bin/clang clang /usr/bin/clang-8 100 ;\
    update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-8 100 ;\
    update-alternatives --install /usr/bin/lld lld /usr/bin/lld-8 100

# LTS releases often bundle obsolete pip versions that cannot access newest
# Linux binary wheels. This pinned version is not special: it was just current
# at the time this was added. Refer to compatibility table:
# https://github.com/pypa/manylinux
RUN python3 -m pip install --upgrade pip==21.0.1

# Refer to mlir/lib/Bindings/Python/requirements.txt. Listed explicitly here
# and version pinned for consistency as this is a bot.
RUN python3 -m pip install numpy==1.19.3 pybind11==2.6.0 PyYAML==5.4.1

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

# Install build bot (server was at 2.8.5-dev at time of writing).
RUN pip3 install buildbot-worker==2.8.4

# Workaround permissions issues when writing to named volumes
# https://github.com/docker/compose/issues/3270#issuecomment-206214034
RUN mkdir -p /vol/test /vol/ccache /vol/worker ; \
    chmod -R 777 /vol

# Volume to mount secrets into the container.
VOLUME /vol/secrets
# Volume to store data for local, manual testing of the container.
VOLUME /vol/test
# Volume to store ccache.
VOLUME /vol/ccache
ENV CCACHE_DIR=/vol/ccache
# Volume for worker working directory.
VOLUME /vol/worker

# Create user account, some tests fail if run as root.
RUN useradd buildbot --create-home
WORKDIR /vol/worker

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
ENV BUILDBOT_PORT="9994"

CMD /home/buildbot/run.sh
