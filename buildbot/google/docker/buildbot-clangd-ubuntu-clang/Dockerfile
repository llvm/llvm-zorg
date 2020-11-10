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
FROM ubuntu:18.04


# install build tools
RUN apt-get update; \
    apt-get install -y software-properties-common apt-transport-https ca-certificates \
    ninja-build git wget gnupg \
    # install ccache for local caching of builds
    ccache \
    # install python for buildbot and LIT
    python3 python3-pip python3-psutil \
    # clangd requires libgrpc and protobuf for remote index, see
    # https://github.com/llvm/llvm-project/tree/master/clang-tools-extra/clangd/index/remote#system-installed-libraries
    libgrpc++-dev libprotobuf-dev protobuf-compiler protobuf-compiler-grpc ; \
    # clean apt cache to reduce image size
    apt-get clean

# install latest LLVM release
RUN bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)"

# configure default versions of LLVM tools
RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-11 100 ;\
    update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-11 100 ;\
    update-alternatives --install /usr/bin/lld lld /usr/bin/lld-11 100

# Ubuntu ships with old cmake version, install the latest one
# from https://apt.kitware.com/
RUN wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | \
    gpg --dearmor - | \
    tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null ;\
    apt-add-repository 'deb https://apt.kitware.com/ubuntu/ bionic main' ;\
    apt-get update ;\
    apt-get install -y cmake

# install build bot (server was at 2.8.5-dev at time of writing)
RUN pip3 install buildbot-worker==2.8.4

# Workaround permissions issues when writing to named volumes
# https://github.com/docker/compose/issues/3270#issuecomment-206214034 
RUN mkdir -p /vol/test /vol/ccache /vol/worker ; \
    chmod -R 777 /vol

# Volume to mount secrets into the container
VOLUME /vol/secrets
# Volume to store data for local, manual testing of the container
VOLUME /vol//test
# Volume to store ccache
VOLUME /vol/ccache
ENV CCACHE_DIR=/vol/ccache
# Volume for worker working directory
VOLUME /vol/worker

# create user account, some test fail if run as root
RUN useradd buildbot --create-home
WORKDIR /vol/worker

# copy startup script
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

#configure LLVM tools
ENV CC=clang
ENV CXX=clang++
ENV LD=LLD

# run startup script
CMD /home/buildbot/run.sh
