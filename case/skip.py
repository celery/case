from __future__ import absolute_import, unicode_literals

import importlib
import os
import sys

from functools import partial

from nose import SkipTest

from .utils import decorator, symbol_by_name

__all__ = [
    'todo',
    'if_darwin', 'unless_darwin',
    'if_environ', 'unless_environ',
    'if_module', 'unless_module',
    'if_jython', 'unless_jython',
    'if_platform', 'unless_platform',
    'if_pypy', 'unless_pypy',
    'if_python3', 'unless_python3',
    'if_win32', 'unless_win32',
    'if_symbol', 'unless_symbol',
    'if_python_version_after', 'if_python_version_before',
]


@decorator
def if_python_version_before(*version, **kwargs):
    if sys.version_info < version:
        raise SkipTest('python >= {0}: {1}'.format(
            '.'.join(version), kwargs.get('reason') or 'incompatible'))
    yield


@decorator
def if_python_version_after(*version, **kwargs):
    if sys.version_info >= version:
        raise SkipTest('python >= {0}: {1}'.format(
            '.'.join(version), kwargs.get('reason') or 'incompatible'))
    yield
if_python3 = partial(if_python_version_after, 3)
unless_python3 = partial(if_python_version_before, 3)


@decorator
def if_environ(env_var_name):
    if os.environ.get(env_var_name):
        raise SkipTest('envvar {0} set'.format(env_var_name))
    yield


@decorator
def unless_environ(env_var_name):
    if not os.environ.get(env_var_name):
        raise SkipTest('envvar {0} not set'.format(env_var_name))
    yield


@decorator
def _skip_test(reason, sign):
    raise SkipTest('{0}: {1}'.format(sign, reason))
todo = partial(_skip_test, sign='TODO')
skip = partial(_skip_test, sign='SKIP')


@decorator
def if_module(module, name=None, import_errors=(ImportError,)):
    try:
        importlib.import_module(module)
    except import_errors:
        pass
    else:
        raise SkipTest('module available: {0}'.format(name or module))
    yield


@decorator
def unless_module(module, name=None, import_errors=(ImportError,)):
    try:
        importlib.import_module(module)
    except import_errors:
        raise SkipTest('module not installed: {0}'.format(name or module))
    yield


@decorator
def if_symbol(symbol, name=None,
              import_errors=(AttributeError, ImportError)):
    try:
        symbol_by_name(symbol)
    except import_errors:
        pass
    else:
        raise SkipTest('symbol exists: {0}'.format(name or symbol))
    yield


@decorator
def unless_symbol(symbol, name=None,
                  import_errors=(AttributeError, ImportError)):
    try:
        symbol_by_name(symbol)
    except import_errors:
        raise SkipTest('missing symbol: {0}'.format(name or symbol))
    yield


@decorator
def if_platform(platform_name, name=None):
    if sys.platform.startswith(platform_name):
        raise SkipTest('does not work on {0}'.format(platform_name or name))
    yield
if_jython = partial(if_platform, 'java', name='Jython')
if_win32 = partial(if_platform, 'win32', name='Windows')
if_darwin = partial(if_platform, 'darwin', name='OS X')


@decorator
def unless_platform(platform_name, name=None):
    if not sys.platform.startswith(platform_name):
        raise SkipTest('only applicable on {0}'.format(platform_name or name))
    yield
unless_jython = partial(unless_platform, 'java', name='Jython')
unless_win32 = partial(unless_platform, 'win32', name='Windows')
unless_darwin = partial(unless_platform, 'darwin', name='OS X')


@decorator
def if_pypy():
    if getattr(sys, 'pypy_version_info', None):
        raise SkipTest('does not work on PyPy')
    yield


@decorator
def unless_pypy():
    if not hasattr(sys, 'pypy_version_info'):
        raise SkipTest('only applicable on PyPy')
    yield
