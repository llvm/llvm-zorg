FROM debian:12 AS rel

ENV DEBIAN_FRONTEND=noninteractive
ENV LLVM_MAJOR_VERSION=23

RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      automake \
      binutils-dev \
      ca-certificates \
      ccache \
      curl \
      dos2unix \
      g++-multilib \
      gawk \
      gcc-multilib \
      git \
      gnupg \
      libgcrypt-dev \
      libgss-dev \
      liblzma-dev \
      libssl-dev \
      libtool \
      libxml2-dev \
      lsb-release \
      m4 \
      ninja-build \
      pkg-config \
      procps \
      python-is-python3 \
      python3 \
      python3-dev \
      python3-distutils \
      python3-pip \
      python3-venv \
      software-properties-common \
      sudo \
      tmux \
      wget \
      zlib1g-dev && \
    echo "deb http://deb.debian.org/debian bookworm-backports main" > /etc/apt/sources.list.d/bookworm-backports.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends -t bookworm-backports cmake cmake-data && \
    bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)" _ ${LLVM_MAJOR_VERSION} && \
    ln -sf /usr/bin/clang-${LLVM_MAJOR_VERSION} /usr/bin/clang && \
    ln -sf /usr/bin/clang++-${LLVM_MAJOR_VERSION} /usr/bin/clang++ && \
    ln -sf /usr/bin/clang-${LLVM_MAJOR_VERSION} /usr/bin/cc && \
    ln -sf /usr/bin/clang++-${LLVM_MAJOR_VERSION} /usr/bin/c++ && \
    ln -sf /usr/bin/ld.lld-${LLVM_MAJOR_VERSION} /usr/bin/ld && \
    ln -sf /usr/bin/ld.lld-${LLVM_MAJOR_VERSION} /usr/bin/ld.lld && \
    rm -rf /var/lib/apt/lists/*

RUN cat <<'EOF' > /etc/ccache.conf
sloppiness = pch_defines,time_macros
depend_mode = true
run_second_cpp = true
hash_dir = true
EOF

RUN python3 -m pip install --no-cache-dir --break-system-packages pipenv buildbot-worker==2.9.0 && \
    mkdir /tmp/mlgo-pipenv && \
    cd /tmp/mlgo-pipenv && \
    curl -fsSL https://raw.githubusercontent.com/google/ml-compiler-opt/refs/heads/main/Pipfile.lock.3.11 -o Pipfile.lock && \
    pipenv sync --extra-pip-args="--break-system-packages" --categories "packages dev-packages" --system && \
    cd / && \
    rm -rf /tmp/mlgo-pipenv /root/.cache && \
    curl -fsSL https://raw.githubusercontent.com/llvm/llvm-project/main/llvm/tools/llvm-ir2vec/Bindings/requirements.txt -o /tmp/ir2vec-reqs.txt && \
    python3 -m pip install --no-cache-dir --break-system-packages -r /tmp/ir2vec-reqs.txt && \
    rm -f /tmp/ir2vec-reqs.txt

COPY startup.sh liveness.sh ./
ENTRYPOINT /startup.sh

FROM rel as dev

COPY build_tflite.sh /tmp/build_tflite.sh
RUN bash /tmp/build_tflite.sh && rm /tmp/build_tflite.sh
ENV TFLITE_CMAKE=/tflite/tflite.cmake
