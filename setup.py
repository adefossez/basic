#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Inspired from https://github.com/kennethreitz/setup.py

from pathlib import Path

from setuptools import find_packages, setup

NAME = 'basic'
DESCRIPTION = ('Utility for handling basic types, '
               'convertible to and from JSON/BSON')
URL = 'https://github.com/adefossez/basic'
EMAIL = 'alexandredefossez@gmail.com'
AUTHOR = 'Alexandre Défossez'
REQUIRES_PYTHON = '>=3.6.0'
VERSION = "0.2"

HERE = Path(__file__).parent

REQUIRED = []

try:
    with open(HERE / "README.md", encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(),
    install_requires=REQUIRED,
    include_package_data=True,
    data_files=[("", ["LICENSE"])],
    license='Unlicense License',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
)
