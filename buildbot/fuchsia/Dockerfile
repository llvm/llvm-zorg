# Use an official Ubuntu image as the base.
FROM ubuntu:jammy as base

ARG DEBIAN_FRONTEND=noninteractive

# Install build tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    ccache \
    curl \
    dumb-init \
    git \
    gpg \
    lsb-release \
    ninja-build \
    python-is-python3 \
    python3 \
    python3-pip \
    python3-psutil \
    software-properties-common \
    unzip \
    # Clean apt cache to reduce image size.
    && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Install latest CMake release.
RUN curl -fsSL https://apt.kitware.com/keys/kitware-archive-latest.asc | \
    gpg --dearmor -o /usr/share/keyrings/kitware-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ jammy main" | \
    tee /etc/apt/sources.list.d/kitware.list && \
    apt-get update && apt-get install -y --no-install-recommends cmake && \
    rm -rf /var/lib/apt/lists/*

ARG LLVM_VERSION=17

# Install latest LLVM release.
RUN curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key | \
    gpg --dearmor -o /usr/share/keyrings/llvm-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/llvm-archive-keyring.gpg] http://apt.llvm.org/jammy/ llvm-toolchain-jammy-${LLVM_VERSION} main" | \
    tee /etc/apt/sources.list.d/llvm.list && \
    apt-get update && apt-get install -y --no-install-recommends clang-${LLVM_VERSION} lld-${LLVM_VERSION} && \
    rm -rf /var/lib/apt/lists/*

# Configure default versions of LLVM tools.
RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-${LLVM_VERSION} 100 ;\
    update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-${LLVM_VERSION} 100 ;\
    update-alternatives --install /usr/bin/ld.lld ld.lld /usr/bin/ld.lld-${LLVM_VERSION} 100

# Configure LLVM tools.
ENV CC=clang
ENV CXX=clang++
ENV LD=ld.lld

# Workaround permissions issues when writing to named volumes.
# https://github.com/docker/compose/issues/3270#issuecomment-206214034
RUN mkdir -p /vol/ccache && chmod -R 1777 /vol

# Volume to store ccache.
VOLUME /vol/ccache
ENV CCACHE_DIR=/vol/ccache

# Install CIPD.
ARG CIPD_PLATFORM=linux-amd64

RUN curl -fsSL -o /usr/local/bin/cipd "https://chrome-infra-packages.appspot.com/client?platform=${CIPD_PLATFORM}&version=latest" && \
    chmod +x /usr/local/bin/cipd

ARG FUCHSIA_VERSION=14

# Install Fuchsia SDK.
RUN cipd install -root /usr/local/fuchsia/sdk fuchsia/sdk/core/${CIPD_PLATFORM} f${FUCHSIA_VERSION}

# Use the base image to build the image for buildbot.
FROM base as buildbot

ARG BUILDBOT_VERSION=3.9.2

# Install buildbot.
RUN pip3 --no-cache-dir install twisted[tls] && \
    pip3 install buildbot_worker==${BUILDBOT_VERSION}

RUN useradd -d /var/lib/buildbot -r -s /usr/sbin/nologin buildbot
WORKDIR /var/lib/buildbot

COPY buildbot.tac .

RUN mkdir -p info && \
    echo "LLVM infra <llvm-infra@google.com>" > info/admin && \
    echo "$(lsb_release -d | cut -f 2-)," \
         "$(clang --version | head -n1)," \
         "$(ld.lld --version)," \
         "$(cmake --version | head -n1)," \
         "ninja version $(ninja --version)" > info/host

RUN chown -R buildbot:buildbot /var/lib/buildbot
USER buildbot

# By default, start the Buildbot worker.
CMD ["twistd", "--pidfile=", "-ny", "buildbot.tac"]

# Use the base image to build the image for buildkite.
FROM base as buildkite

# Install the Buildkite agent.
RUN curl -fsSL https://keys.openpgp.org/vks/v1/by-fingerprint/32A37959C2FA5C3C99EFBC32A79206696452D198 | \
    gpg --dearmor -o /usr/share/keyrings/buildkite-agent-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/buildkite-agent-archive-keyring.gpg] https://apt.buildkite.com/buildkite-agent stable main" | \
    tee /etc/apt/sources.list.d/buildkite-agent.list && \
    apt-get update && apt-get install -y --no-install-recommends buildkite-agent

# Create user account, some tests fail if run as root.
WORKDIR /var/lib/buildkite-agent

USER buildkite-agent

# By default, start the Buildkite agent (this requires a token).
CMD ["buildkite-agent", "start"]
