FROM docker.io/ubuntu:24.04

# Make sure apt-get doesn't prompt for stuff like our time zone, etc.
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update; \
    apt-get install -y --no-install-recommends \
        gosu tini \
        locales openssh-client gnupg ca-certificates apt-transport-https \
        zip wget curl git \
        gdb build-essential  \
        ninja-build \
        libelf-dev libffi-dev gcc-multilib libmpfr-dev libpfm4-dev \
        cmake \
        # for llvm-libc tests that build mpfr and gmp from source
        autoconf automake libtool \
        python3 python3-psutil python3-pip python3-setuptools \
        lsb-release software-properties-common \
        swig python3-dev libedit-dev libncurses5-dev libxml2-dev liblzma-dev golang rsync jq \
        # for libc++ tests that use the timezone database of the chrono header
        tzdata \
        # for llvm installation script
        sudo

# LLVM must be installed after prerequsite packages.
ENV LLVM_VERSION=18
RUN echo 'install llvm ${LLVM_VERSION}' && \
    wget --no-verbose https://apt.llvm.org/llvm.sh && \
    chmod +x llvm.sh && \
    ./llvm.sh ${LLVM_VERSION} && \
    apt-get update && \
    apt-get install -y clang-${LLVM_VERSION} clang-format-${LLVM_VERSION} clang-tidy-${LLVM_VERSION} lld-${LLVM_VERSION} && \
    ln -s /usr/bin/clang-${LLVM_VERSION} /usr/bin/clang && \
    ln -s /usr/bin/clang++-${LLVM_VERSION} /usr/bin/clang++ && \
    ln -s /usr/bin/clang-tidy-${LLVM_VERSION} /usr/bin/clang-tidy && \
    ln -s /usr/bin/clang-tidy-diff-${LLVM_VERSION}.py /usr/bin/clang-tidy-diff && \
    ln -s /usr/bin/clang-format-${LLVM_VERSION} /usr/bin/clang-format && \
    ln -s /usr/bin/clang-format-diff-${LLVM_VERSION} /usr/bin/clang-format-diff && \
    ln -s /usr/bin/lld-${LLVM_VERSION} /usr/bin/lld && \
    ln -s /usr/bin/lldb-${LLVM_VERSION} /usr/bin/lldb && \
    ln -s /usr/bin/ld.lld-${LLVM_VERSION} /usr/bin/ld.lld && \
    clang --version

RUN echo 'configure locale' && \
    sed --in-place '/en_US.UTF-8/s/^#//' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

COPY *.sh /usr/local/bin/
RUN chmod og+rx /usr/local/bin/*.sh

# Install bazelisk.
ENV BAZELISK_VERSION=v1.28.1
RUN wget --no-verbose -O /usr/bin/bazelisk https://github.com/bazelbuild/bazelisk/releases/download/${BAZELISK_VERSION}/bazelisk-linux-amd64; \
  chmod +x /usr/bin/bazelisk; \
  bazelisk --version

# Build and install buildifier and buildozer
RUN git clone https://github.com/bazelbuild/buildtools.git /tmp/buildtools; \
  cd /tmp/buildtools; \
  bazelisk build --noshow_progress --ui_event_filters=-debug,-info //buildifier //buildozer; \
  cp /tmp/buildtools/bazel-bin/buildifier/buildifier_/buildifier /usr/local/bin/; \
  cp /tmp/buildtools/bazel-bin/buildozer/buildozer_/buildozer /usr/local/bin/; \
  /usr/local/bin/buildifier --version; \
  /usr/local/bin/buildozer --version

RUN echo 'install buildkite' ;\
    apt-get install -y apt-transport-https gnupg;\
    sh -c 'echo deb https://apt.buildkite.com/buildkite-agent stable main > /etc/apt/sources.list.d/buildkite-agent.list' ;\
    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 32A37959C2FA5C3C99EFBC32A79206696452D198 ;\
    apt-get update ;\
    apt-get install -y buildkite-agent; \
    apt-get clean;

COPY --chown=buildkite-agent:buildkite-agent pre-checkout /etc/buildkite-agent/hooks

# Change sh client for buildkite-agent.
RUN chsh -s /bin/bash buildkite-agent
# buildkite working directory
VOLUME /var/lib/buildkite-agent

ENTRYPOINT ["entrypoint.sh"]
CMD ["gosu", "buildkite-agent", "buildkite-agent", "start", "--no-color", "--tags-from-gcp"]
