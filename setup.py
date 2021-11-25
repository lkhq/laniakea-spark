#!/usr/bin/env python3

from setuptools import setup

from spark import __appname__, __version__

packages = [
    'spark',
    'spark.utils',
    'spark.runners',
]

scripts = {
    'console_scripts': [
        'lk-spark = spark.cli:daemon',
    ],
}

data_files = [
    ('/var/lib/lkspark/',
     ['data/ws/README'])
]

long_description = ""

install_requires = [
    'toml>=0.10',
    'pyzmq>=16',
    'python-debian>=0.1.28',
    'firehose>=0.5'
]

setup(
    name=__appname__,
    version=__version__,
    scripts=[],
    packages=packages,
    data_files=data_files,

    author="Matthias Klumpp",
    author_email="matthias@tenstral.net",
    long_description=long_description,
    description='Job runner for Laniakea',
    license="LGPL-3.0+",
    url="https://laniakea-hq.rtfd.io",

    python_requires='>=3.9',
    platforms=['any'],
    zip_safe=False,
    entry_points=scripts,
    install_requires=install_requires,
)
