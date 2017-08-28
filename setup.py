#!/usr/bin/python3
# coding: utf-8

import setuptools


setuptools.setup(
    name='pyregdict',
    version='0.1',
    description='Access to Windows Registry data as if a Unix file path.',
    author='Charles Aracil',
    author_email='charles.aracil+pyregdict@gmail.com',
    python_requires='>=3.6',
    install_requires=(),
    extras_require={},
    py_modules=['pyregdict', ],
    license=open('LICENSE').read(),
    long_description=open('README.md').read()
)
