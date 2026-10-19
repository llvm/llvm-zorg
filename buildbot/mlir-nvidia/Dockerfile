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
FROM docker.io/nvidia/cuda:13.4.3-cudnn-devel-ubuntu22.04

# install extra build tools
ENV TZ=Etc/UTC
ENV DEBIAN_FRONTEND=noninteractive
# GCC 7 is still used by the secondary builder but is no longer in Jammy.
# Keep Focal packages below Jammy's priority so other tools use Jammy versions.
RUN case "$(dpkg --print-architecture)" in \
       amd64) ubuntu_archive=http://archive.ubuntu.com/ubuntu ;; \
       arm64) ubuntu_archive=http://ports.ubuntu.com/ubuntu-ports ;; \
     esac \
  && echo "deb ${ubuntu_archive} focal main universe" \
       > /etc/apt/sources.list.d/gcc7-focal.list \
  && printf 'Package: *\nPin: release n=focal\nPin-Priority: 100\n' \
       > /etc/apt/preferences.d/gcc7-focal \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    ccache \
    clang-14 \
    cuda-compat-13-4 \
    # dumb-init recommended in
    # https://hub.docker.com/r/buildbot/buildbot-worker/dockerfile
    dumb-init \
    gcc-7 \
    g++-7 \
    git \
    gnupg \
    libpython3-dev \
    lld-14 \
    ninja-build \
    python3 \
    python3-pip \
    python3-psutil \
    software-properties-common \
    wget \
  && update-alternatives --install /usr/bin/clang clang /usr/bin/clang-14 100 \
  && update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-14 100 \
  && update-alternatives --install /usr/bin/ld.lld lld /usr/bin/lld-14 100 \
  && rm -rf /var/lib/apt/lists/*

# The worker's Tesla T4 uses an R535 host driver. Use CUDA's forward-compatible
# driver libraries for CUDA 13.4, including JIT compilation of new PTX.
ENV LD_LIBRARY_PATH=/usr/local/cuda/compat:${LD_LIBRARY_PATH}

# LTS releases often bundle obsolete pip versions that cannot access newest
# Linux binary wheels. This pinned version is not special: it was just current
# at the time this was added. Refer to compatibility table:
# https://github.com/pypa/manylinux
RUN python3 -m pip install --upgrade pip==23.1.2

# Ubuntu ships with an old CMake version. Install the latest stable release
# from Kitware's official binary distribution.
ARG CMAKE_VERSION=4.4.4
RUN cd /tmp \
  && case "$(uname -m)" in \
       x86_64) cmake_sha256=e5bb807f7728cb60cd8b27ebc97a2edb469b68655f21e844a600c3575b76f5bb ;; \
       aarch64) cmake_sha256=a1b6cc63636a0e55c63257cf3315a8a5f129e42fade25db1afea4ff8ab06f25e ;; \
       *) echo "Unsupported CMake architecture: $(uname -m)" >&2; exit 1 ;; \
     esac \
  && wget -q "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-$(uname -m).tar.gz" \
  && echo "${cmake_sha256}  cmake-${CMAKE_VERSION}-linux-$(uname -m).tar.gz" \
       | sha256sum --check - \
  && tar -xzf "cmake-${CMAKE_VERSION}-linux-$(uname -m).tar.gz" \
       --strip-components=1 -C /usr/local \
  && rm "cmake-${CMAKE_VERSION}-linux-$(uname -m).tar.gz"

# Get the Vulkan SDK from LunarG.
RUN wget -qO - https://packages.lunarg.com/lunarg-signing-key-pub.asc 2>/dev/null \
  | apt-key add - \
  && wget -qO /etc/apt/sources.list.d/lunarg-vulkan-1.3.283-jammy.list \
       https://packages.lunarg.com/vulkan/1.3.283/lunarg-vulkan-1.3.283-jammy.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends vulkan-sdk \
  && rm -rf /var/lib/apt/lists/*


# The VM mounts its NVIDIA driver libraries at /usr/local/nvidia/lib64.
# Register both Vulkan and EGL so the matching host driver can initialize.
RUN mkdir -p /etc/vulkan/icd.d /usr/share/glvnd/egl_vendor.d \
  && printf '%s\n' \
       '{"file_format_version":"1.0.0","ICD":{"library_path":"/usr/local/nvidia/lib64/libGLX_nvidia.so.0","api_version":"1.3.0"}}' \
       > /etc/vulkan/icd.d/nvidia_icd.json \
  && printf '%s\n' \
       '{"file_format_version":"1.0.0","ICD":{"library_path":"/usr/local/nvidia/lib64/libEGL_nvidia.so.0"}}' \
       > /usr/share/glvnd/egl_vendor.d/10_nvidia.json

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
