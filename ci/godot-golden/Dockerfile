# The Linux golden image (client_rendering.md §6.5; T12, CR-B3, EX-B3). Goldens are gated only here, because a
# software rasterizer pinned to one build gives the same pixels on every runner, where GPUs and drivers don't.
# Build from the repository root:  docker build --platform linux/amd64 -f ci/godot-golden/Dockerfile -t overdrive-golden .
#
# Every input is pinned: the base image by digest (ubuntu:24.04, linux/amd64 manifest), every package by version from
# a dated Ubuntu snapshot (the live archive drops superseded versions, so a version pin alone breaks within weeks),
# Godot by SHA-256 (ci/godot.env), and Python packages by constraints/py3.12.txt.
FROM ubuntu@sha256:77eb101c607d6e3d4f5ad0c8a02c2136c689b98aba1f359e6502ba517e5c57ec

ARG SNAPSHOT=20261101T000000Z
ARG MESA=25.2.8-0ubuntu0.24.04.4
ENV DEBIAN_FRONTEND=noninteractive

# apt checks every index and package against the Ubuntu archive's signing key, so TLS adds no integrity here. The
# base image has no CA bundle, so the first update skips peer verification only to install the pinned one.
RUN sed -i -e "s#http://archive.ubuntu.com/ubuntu/\?#https://snapshot.ubuntu.com/ubuntu/${SNAPSHOT}#" \
           -e "s#http://security.ubuntu.com/ubuntu/\?#https://snapshot.ubuntu.com/ubuntu/${SNAPSHOT}#" \
           /etc/apt/sources.list.d/ubuntu.sources \
 && grep -q "snapshot.ubuntu.com/ubuntu/${SNAPSHOT}" /etc/apt/sources.list.d/ubuntu.sources \
 && ! grep -q "^URIs: http://" /etc/apt/sources.list.d/ubuntu.sources \
 && apt-get -o Acquire::https::Verify-Peer=false update \
 && apt-get -o Acquire::https::Verify-Peer=false install -y --no-install-recommends ca-certificates=20260816ubuntu0.24.04.1 \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      libgl1-mesa-dri=${MESA} libglx-mesa0=${MESA} libegl-mesa0=${MESA} mesa-libgallium=${MESA} \
      libllvm20=1:20.1.2-0ubuntu1~24.04.3 libgl1=1.7.0-1build1 \
      xvfb=2:21.1.12-1ubuntu1.9 xauth=1:1.1.2-1build1 \
      libfontconfig1=2.15.0-1.1ubuntu2 libxcursor1=1:1.2.1-1build1 libxinerama1=2:1.1.4-3build1 \
      libxrandr2=2:1.5.2-2build1 libxi6=2:1.8.1-1build1 \
      libxkbcommon0=1.6.0-1build1 libdbus-1-3=1.14.10-4ubuntu4.1 \
      curl=8.5.0-2ubuntu10.16 unzip=6.0-28ubuntu4.1 \
      python3=3.12.3-0ubuntu2.1 python3-venv=3.12.3-0ubuntu2.1 \
 && rm -rf /var/lib/apt/lists/*

# llvmpipe, Mesa's CPU rasterizer, with a fixed SIMD width: by default its JIT picks the width from the host CPU, and
# GitHub's runner pool mixes CPU types (CR-B3). The renderer's name reports the width; this file is the source,
# and scripts/golden_compare.py::VECTOR_BITS refuses a run whose name doesn't say 256 bits.
ENV LIBGL_ALWAYS_SOFTWARE=1 \
    GALLIUM_DRIVER=llvmpipe \
    LP_NATIVE_VECTOR_WIDTH=256

COPY ci/godot.env ci/install_godot.sh /opt/ci/
# The installer detects the platform (linux-x86_64 here) and refuses a download whose SHA-256 differs.
RUN godot="$(/opt/ci/install_godot.sh /opt/godot)" && ln -s "$godot" /usr/local/bin/godot

COPY constraints/py3.12.txt /opt/ci/py3.12.txt
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --only-binary :all: -c /opt/ci/py3.12.txt numpy scipy pillow
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /repo
