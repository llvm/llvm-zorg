#===-- Dockerfile --------------------------------------------------------===//
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===----------------------------------------------------------------------===//
# Environment variables configurable at runtime:
#    BUILDBOT_PORT - server port to connect to
#===----------------------------------------------------------------------===//

FROM debian:sid

# Install build tools.
RUN apt-get update && \
    apt-get install -y \
        software-properties-common apt-transport-https ca-certificates \
        git wget gnupg \
        cmake ninja-build  \
        ccache \
        python3 python3-pip python3-psutil && \
    # Install clang-17 to make the minimal C++20 support in the toolchain.
    echo "deb http://apt.llvm.org/unstable/ llvm-toolchain-17 main" >> /etc/apt/sources.list.d/llvm-17.list && \
    wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key >> /etc/apt/trusted.gpg.d/llvm.asc && \
    apt-get update && \
    apt-get install -y clang-17 lld-17 && \
    apt-get clean

# Install build bot (server was at 2.8.4 at time of writing).
# We need --break-system-packages to install globally.
RUN pip3 install --break-system-packages buildbot-worker==2.8.4

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
ENV WORKER_NAME="clang-debian-cpp20"

# Allow the server port of this agent to be configurable during deployment.
# This way we can connect the same image to production and integration.
# Ports:
#   9990 - production
#   9994 - integration
ENV BUILDBOT_PORT="9994"

# Configure LLVM tools.
ENV CC=clang-17
ENV CXX=clang++-17
ENV LD=ld.lld-17

# Run startup script.
CMD /home/buildbot/run.sh
