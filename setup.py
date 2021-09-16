# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import io
import os
import qlib_server

from setuptools import find_packages, setup
from packaging import version

# Package meta-QLibServer.
NAME = "qlib_server"
DESCRIPTION = "Server of the Quantitative-research Library -- QLib"
REQUIRES_PYTHON = ">=3.5.0"
VERSION = qlib_server.__version__

# Inspect qlib package
try:
    REQUIRED_QLIB_VERSION = "0.4.0"
    import qlib

    ver = qlib.__version__
    _QLIB_INSTALLED = version.parse(ver) >= version.parse(REQUIRED_QLIB_VERSION)
except ImportError:
    _QLIB_INSTALLED = False

if not _QLIB_INSTALLED:
    print("Required qlib version >= {} is not detected!".format(REQUIRED_QLIB_VERSION))
    print("Please install the latest version of qlib first.")
    exit(-1)

# What packages are required for this module to be executed?
REQUIRED = [
    "Flask>=1.0.2",
    "Flask-SocketIO>=3.1.2",
    "gevent>=1.3.7",
    "pika>=0.12.0",
    "redis>=3.0.1",
    "python-redis-lock>=3.3.1",
    "schedule>=0.6.0",
    "tqdm>=4.31.1",
    "fabric2",
    "loguru",
    "fire",
]

here = os.path.abspath(os.path.dirname(__file__))

with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = "\n" + f.read()

# Where the magic happens:
setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    python_requires=REQUIRES_PYTHON,
    packages=find_packages(exclude=("tests",)),
    # if your package is a single module, use this instead of 'packages':
    # py_modules=['qlib'],
    entry_points={
        # 'console_scripts': ['mycli=mymodule:cli'],
    },
    ext_modules=[],
    install_requires=REQUIRED,
    include_package_data=True,
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        # 'License :: OSI Approved :: MIT License',
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
