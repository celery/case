#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools

import os
import re
import sys
import codecs

if sys.version_info < (2, 6):
    raise Exception('case requires Python 2.6 or higher.')

NAME = 'case'

# -*- Classifiers -*-

classes = """
    Development Status :: 5 - Production/Stable
    Programming Language :: Python
    Programming Language :: Python :: 2
    Programming Language :: Python :: 2.7
    Programming Language :: Python :: 2.6
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3.3
    Programming Language :: Python :: 3.4
    Programming Language :: Python :: 3.5
    License :: OSI Approved :: BSD License
    Intended Audience :: Developers
    Operating System :: OS Independent
"""
classifiers = [s.strip() for s in classes.split('\n') if s]

# -*- Distribution Meta -*-

re_meta = re.compile(r'__(\w+?)__\s*=\s*(.*)')
re_doc = re.compile(r'^"""(.+?)"""')


def add_default(m):
    attr_name, attr_value = m.groups()
    return ((attr_name, attr_value.strip("\"'")),)


def add_doc(m):
    return (('doc', m.groups()[0]),)

pats = {re_meta: add_default, re_doc: add_doc}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'case/__init__.py')) as meta_fh:
    meta = {}
    for line in meta_fh:
        if line.strip() == '# -eof meta-':
            break
        for pattern, handler in pats.items():
            m = pattern.match(line.strip())
            if m:
                meta.update(handler(m))

# -*- Parsing Requirement Files -*-

py_version = sys.version_info
is_jython = sys.platform.startswith('java')
is_pypy = hasattr(sys, 'pypy_version_info')


def strip_comments(l):
    return l.split('#', 1)[0].strip()


def _pip_requirement(req):
    if req.startswith('-r '):
        _, path = req.split()
        return reqs(*path.split('/'))
    return [req]


def _reqs(*f):
    return [
        _pip_requirement(r) for r in (
            strip_comments(l) for l in open(
                os.path.join(os.getcwd(), 'requirements', *f)).readlines()
        ) if r]


def reqs(*f):
    return [req for subreq in _reqs(*f) for req in subreq]

# -*- Install Requires -*-

install_requires = reqs('default.txt')

if sys.version_info[0] >= 3:
    if is_pypy:
        install_requires.extend(reqs('pypy3.txt'))
else:
    install_requires.extend(reqs('py2.txt'))
    if sys.version_info < (2, 7):
        install_requires.extend(reqs('py26.txt'))

# -*- Tests Requires -*-

tests_require = reqs('test.txt')

# -*- Long Description -*-

if os.path.exists('README.rst'):
    long_description = codecs.open('README.rst', 'r', 'utf-8').read()
else:
    long_description = 'See http://pypi.python.org/pypi/case/'

# -*- %%% -*-

setuptools.setup(
    name=NAME,
    version=meta['version'],
    description=meta['doc'],
    keywords='test unit testing pytest unittest mock patch',
    author=meta['author'],
    author_email=meta['contact'],
    url=meta['homepage'],
    platforms=['any'],
    license='BSD',
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite='nose.collector',
    classifiers=classifiers,
    long_description=long_description,
    entry_points={
        'pytest11': ['case = case.pytest'],
    },
    packages=setuptools.find_packages(
        exclude=['ez_setup', 'tests', 'tests.*'],
    ),
)
