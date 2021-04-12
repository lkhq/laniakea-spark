# Laniakea Spark
[![Build & Test](https://github.com/lkhq/laniakea-spark/actions/workflows/python.yml/badge.svg)](https://github.com/lkhq/laniakea-spark/actions/workflows/python.yml)

The generic Laniakea job runner and package builder
Communicates with Lighthouse servers via ZeroMQ to fetch new jobs and report information.

## Setup

Minimum Debian release: 11.0 (Bullseye)

### Install dependencies
```Bash
sudo apt install schroot python3-debian python3-zmq python3-setuptools gnupg dput-ng debspawn
```
