#===-- Dockerfile --------------------------------------------------------===//
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===----------------------------------------------------------------------===//
# Docker image used for the clangd builder
#
# Environment variables configurable at runtime:
#    BUILDBOT_PORT - server port to connect to
#===----------------------------------------------------------------------===//

# Use an official Ubuntu image as the base.
FROM docker.io/ubuntu:18.04

# Install build tools.
RUN apt-get update && \
    apt-get install -y software-properties-common apt-transport-https ca-certificates \
    git wget gnupg unzip \
    # Install ccache for local caching of builds.
    ccache \
    # Install python for buildbot and LIT.
    python3.8 python3-pip python3-psutil && \
    # Update system packages
    apt-get upgrade -y && \
    # Clean apt cache to reduce image size.
    apt-get clean

# install latest LLVM release
RUN wget https://apt.llvm.org/llvm.sh && \
    chmod +x llvm.sh && \
    ./llvm.sh 18 && \
    rm -rf llvm.sh && \
    # clean apt cache to reduce image size
    apt-get clean

# Install newer CMake and Ninja, the versions in Ubuntu repositories are too old.
ENV CMAKE_VERSION=3.31.12
ENV CMAKE_SHA256=0dc2e9a6860f06bf10bd8fadc03e35d9eeb4df46e33763a7e480e987758f385c
ENV NINJA_VERSION=1.13.2
ENV NINJA_SHA256=5749cbc4e668273514150a80e387a957f933c6ed3f5f11e03fb30955e2bbead6
RUN cd /tmp && \
    wget -q "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-x86_64.tar.gz" && \
    wget -q "https://github.com/ninja-build/ninja/releases/download/v${NINJA_VERSION}/ninja-linux.zip" && \
    echo "${CMAKE_SHA256}  cmake-${CMAKE_VERSION}-linux-x86_64.tar.gz" | sha256sum -c - && \
    echo "${NINJA_SHA256}  ninja-linux.zip" | sha256sum -c - && \
    tar -xz --strip-components=1 -C /usr/local -f "cmake-${CMAKE_VERSION}-linux-x86_64.tar.gz" && \
    unzip -q -o ninja-linux.zip -d /usr/local/bin && \
    rm -f "cmake-${CMAKE_VERSION}-linux-x86_64.tar.gz" ninja-linux.zip && \
    cmake --version && \
    ninja --version

# configure default versions of LLVM tools and python needed for
# buildbot-worker. We deliberately do this after installing all the system
# packages, as apt-get install breaks if we change the Python from default to
# python3.8.
RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-18 100 ;\
    update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-18 100 ;\
    update-alternatives --install /usr/bin/ld.lld ld.lld /usr/bin/lld-18 100 ;\
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 100
# Configure LLVM tools.
ENV CC=clang
ENV CXX=clang++
ENV LD=LLD

# Build and install gRPC for clangd remote index, based on instructions
# https://github.com/llvm/llvm-project/tree/master/clang-tools-extra/clangd/index/remote#building-from-sources
# The grpc version shipped with Ubuntu 18.04 crashes on TSan checks.
ENV GRPC_INSTALL_PATH=/usr/local/lib/grpc
RUN cd /tmp ; \
    git clone -b v1.36.3 --depth 1  --recursive --shallow-submodules https://github.com/grpc/grpc && \
    cd grpc &&  mkdir build && cd build && \
    cmake -G Ninja -DgRPC_INSTALL=ON -DCMAKE_INSTALL_PREFIX=${GRPC_INSTALL_PATH} -DCMAKE_BUILD_TYPE=Release .. && \
    cmake --build . --target install && \
    # Clean up sources to reduce image size.
    cd / && rm -rf /tmp/grpc

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

# Copy startup script.
COPY run.sh /home/buildbot/
RUN chmod a+rx /home/buildbot/run.sh

USER buildbot
ENV WORKER_NAME="clangd-ubuntu-clang"

# Allow the server port of this agent to be configurable during deployment.
# This way we can connect the same image to production and integration.
# Ports:
#   9990 - production
#   9994 - integration
ENV BUILDBOT_PORT="9994"

# Run startup script.
CMD /home/buildbot/run.sh
