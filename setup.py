#!/usr/bin/env python3

from spark import __appname__, __version__
from setuptools import setup

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

data_files = [('/etc/schroot/spark/',
                 ['data/schroot/copyfiles',
                  'data/schroot/fstab',
                  'data/schroot/nssdatabases']),
              ('/var/lib/lkspark/',
                 ['data/ws/README'])
             ]

long_description = ""

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
    url="https://lkorigin.github.io/",
    platforms=['any'],
    entry_points=scripts,
)
