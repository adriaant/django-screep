#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

requirements = [
    'Django>=1.6,<1.7',
    'South',
    'django-model-utils',
    'gevent',
    'lxml',
    'reppy',
    'six'
]

test_requirements = [
    'pytest-django'.
    'factory_boy',
    'coverage'
]

setup(
    name='django-screep',
    version='0.1.0',
    description='A reusable Django app for scraping webpages linked to from sitemaps',
    long_description=readme + '\n\n' + history,
    author='Adriaan Tijsseling',
    author_email='adriaangt@gmail.com',
    url='https://github.com/adriaant/django-screep',
    packages=['screep'],
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=False,
    keywords='django, scraping',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
