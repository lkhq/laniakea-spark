#
# Docker file for Laniakea CI
#
FROM debian:sid

# prepare
RUN apt-get update -qq

# install build essentials
RUN apt-get install -yq git build-essential

# install dependencies for Spark
RUN apt-get install -yq --no-install-recommends \
    pkg-config \
    meson \
    libglib2.0-dev \
    libczmq-dev \
    libjson-glib-dev

# build & install 3rd-party libraries
RUN mkdir -p /build/

# finish
WORKDIR /build
