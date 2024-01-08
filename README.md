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

### Install dependencies
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

### Add lkspark user and group
```Bash
adduser --system --home=/var/lib/lkspark lkspark
addgroup lkspark
chown lkspark:lkspark /var/lib/lkspark
```

### Write spark.toml

Create `/etc/laniakea/spark.toml` with the respective information for your deployment:
```toml
LighthouseServer = 'tcp://master.example.org:5570'
AcceptedJobs = [
    'package-build',
    'os-image-build'
]
MachineOwner = 'ACME Inc.'
GpgKeyID = 'DEADBEEF<gpg_fingerprint>'
```

### Create RSA sign-only GnuPG key as lkspark user

TODO

### Make Debspawn images

TODO

### Restart spark

TODO

### Add GPG key to master

TODO

### Add server key to Spark

TODO

### Generate client certificate

TODO

### Add client certificate to master

TODO
