# Laniakea Spark
[![Build & Test](https://github.com/lkhq/laniakea-spark/actions/workflows/python.yml/badge.svg)](https://github.com/lkhq/laniakea-spark/actions/workflows/python.yml)

Spark is the generic Laniakea job runner and package build executor.
It is able to perform a variety of tasks on dedicated builder machines,
like building packages, distribution ISO images or performing longer QA tasks.

Spark instances communicate with Lighthouse servers via ZeroMQ to fetch new jobs and
report information. They auto-register with the master system, if they were provided
with the right credentials for the respective instance.

## Quick Setup

### Dependencies

```bash
sudo apt install \
	python3-debian \
	python3-zmq \
	python3-setuptools \
	python3-firehose \
	python3-pkgconfig \
	gnupg \
	dput-ng \
	debspawn
```

### Installation

Install the Python package using pip:

```bash
pip install git+https://github.com/lkhq/laniakea-spark.git
```

Or for development installation:

```bash
git clone https://github.com/lkhq/laniakea-spark.git
cd laniakea-spark
pip install -e .
```

**⚠️ Important: System Configuration**

After installing the Python package, you must run the system configuration installer:

```bash
sudo python3 install-sysdata.py
```

This script installs essential system files that cannot be installed via pip:
- **Systemd service unit**: `/lib/systemd/system/laniakea-spark.service`
- **Sudo configuration**: `/etc/sudoers.d/10laniakea-spark`

Without running this step, the Spark daemon will not function properly.

After installation, enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable laniakea-spark.service
sudo systemctl start laniakea-spark.service
```

## Lanieakea Integration

You can find more information on how to set up Spark instances at
[the Laniakea documentation](https://laniakea-hq.readthedocs.io/latest/general/worker-setup.html)
or check out our [Ansible provisioning templates](https://github.com/lkhq/spark-setup).
