# Laniakea Spark
[![Build & Test](https://github.com/lkhq/laniakea-spark/actions/workflows/python.yml/badge.svg)](https://github.com/lkhq/laniakea-spark/actions/workflows/python.yml)

Spark is the generic Laniakea job runner and package build executor.
It is able to perform a variety of tasks on Laniakea on build-farms, like building
packages or distribution ISO images.

Spark instances communicate with Lighthouse servers via ZeroMQ to fetch new jobs and
report information. They auto-register with the master system, if they were provided
with the right credentials for the respective instance.

## Setup Instructions

Minimum required Debian release: 11.0 (Bullseye)

### Dependencies

```Bash
sudo apt install \
	python3-debian \
	python3-zmq \
	python3-setuptools \
	python3-firehose \
	gnupg \
	dput-ng \
	debspawn
```

You can find more information on how to set up Spark instances at
[the Laniakea documentation](https://laniakea-hq.readthedocs.io/latest/general/worker-setup.html)
or check out our [Ansible provisioning templates](https://github.com/lkhq/spark-setup).
