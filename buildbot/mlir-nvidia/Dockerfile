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

# Use the image from NVIDIA
FROM nvidia/cuda:12.1.1-devel-ubuntu20.04

# install extra build tools
ENV TZ=Etc/UTC
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    ccache \
    clang-10 \
    # dumb-init recommended in
    # https://hub.docker.com/r/buildbot/buildbot-worker/dockerfile
    dumb-init \
    git \
    gnupg \
    libpython3-dev \
    lld-10 \
    ninja-build \
    python3 \
    python3-pip \
    python3-psutil \
    software-properties-common \
    wget \
  && update-alternatives --install /usr/bin/clang clang /usr/bin/clang-10 100 \
  && update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-10 100 \
  && update-alternatives --install /usr/bin/ld.lld lld /usr/bin/lld-10 100 \
  && rm -rf /var/lib/apt/lists/*

# LTS releases often bundle obsolete pip versions that cannot access newest
# Linux binary wheels. This pinned version is not special: it was just current
# at the time this was added. Refer to compatibility table:
# https://github.com/pypa/manylinux
RUN python3 -m pip install --upgrade pip==23.1.2

# Refer to mlir/lib/Bindings/Python/requirements.txt. Listed explicitly here
# and version pinned for consistency as this is a bot.
RUN python3 -m pip install numpy==1.24.3 pybind11==2.10.4 PyYAML==5.3.1

# Ubuntu ships with old cmake version, install the latest one
# from https://apt.kitware.com/
RUN wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null \
  | gpg --dearmor - \
  | \
  tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null \
  && apt-add-repository 'deb https://apt.kitware.com/ubuntu/ bionic main' \
  && apt-get update \
  && apt-get install -y --no-install-recommends cmake \
  && rm -rf /var/lib/apt/lists/*

# Get the Vulkan SDK from LunarG.
RUN wget -qO - http://packages.lunarg.com/lunarg-signing-key-pub.asc 2>/dev/null \
  | apt-key add - \
  && wget -qO /etc/apt/sources.list.d/lunarg-vulkan-1.2.141-bionic.list \
       https://packages.lunarg.com/vulkan/1.3.243/lunarg-vulkan-1.3.243-focal.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends vulkan-sdk \
  && rm -rf /var/lib/apt/lists/*


# Right now the container-optimized OS on Google Cloud does not have the Vulkan
# components in the installed driver, install them in the container. This creates
# a coupling with the actual driver running on the VM unfortunately.
RUN apt-get update \
  && apt-get install -y --no-install-recommends libnvidia-gl-470-server \
  && rm -rf /var/lib/apt/lists/*

# Install build bot (server was at 2.8.5-dev at time of writing).
RUN pip3 install buildbot-worker==2.8.4

# Create user account, some tests fail if run as root.
RUN useradd buildbot --create-home
WORKDIR /vol/worker
RUN mkdir -p /vol/worker \
  && chown buildbot /vol/worker

# Configure ccache (default is 5GB caching)
RUN mkdir /home/buildbot/.ccache/ \
  && echo "max_size = 30.0G" > /home/buildbot/.ccache/ccache.conf \
  && chown -R buildbot /home/buildbot/.ccache

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
