from __future__ import absolute_import, unicode_literals

import importlib
import os
import sys

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
    """Skip test if Python version is less than ``*version``.

    Example::

        # skips test if running on Python < 3.1
        @skip.if_python_version_before(3, 1)

    """
    if sys.version_info < version:
        raise SkipTest('python < {0}: {1}'.format(
            '.'.join(map(str, version)),
            kwargs.get('reason') or 'incompatible'))
    yield


@decorator
def if_python_version_after(*version, **kwargs):
    """Skip test if Python version is greater or equal to ``*version``.

    Example::

        # skips test if running on Python >= 3.5
        @skip.if_python_version_after(3, 5)

    """
    if sys.version_info >= version:
        raise SkipTest('python >= {0}: {1}'.format(
            '.'.join(map(str, version)),
            kwargs.get('reason') or 'incompatible'))
    yield


def if_python3(*version, **kwargs):
    """Skip test if Python version is 3 or later.

    Example::

        @skip.if_python3(reason='does not have buffer type')

    """
    return if_python_version_after(3, *version, **kwargs)


def unless_python3(*version, **kwargs):
    """Skip test if Python version is Python 2 or earlier.

    Example::

        @skip.unless_python3()

    """
    return if_python_version_before(3, *version, **kwargs)


@decorator
def if_environ(env_var_name):
    """Skip test if environment variable ``env_var_name`` is defined.

    Example::

        @skip.if_environ('SKIP_SLOW_TESTS')

    """
    if os.environ.get(env_var_name):
        raise SkipTest('envvar {0} set'.format(env_var_name))
    yield


@decorator
def unless_environ(env_var_name):
    """Skip test if environment variable ``env_var_name`` is undefined.

    Example::

        @skip.unless_environ('LOCALE')

    """
    if not os.environ.get(env_var_name):
        raise SkipTest('envvar {0} not set'.format(env_var_name))
    yield


@decorator
def _skip_test(reason, sign):
    raise SkipTest('{0}: {1}'.format(sign, reason))


def todo(reason):
    """Skip test flagging case as TODO.

    Example::

        @skip.todo(reason='broken test')

    """
    return _skip_test(reason, sign='TODO')


def skip(reason):
    return _skip_test(reason, sign='SKIP')


@decorator
def if_module(module, name=None, import_errors=(ImportError,)):
    """Skip test if ``module`` can be imported.

    :param module: Module to import.
    :keyword name: Alternative module name to use in reason.
    :keyword import_errors: Tuple of import errors to check for.
        Default is ``(ImportError,)``.

    Example::

        @skip.if_module('librabbitmq')

    """
    try:
        importlib.import_module(module)
    except import_errors:
        pass
    else:
        raise SkipTest('module available: {0}'.format(name or module))
    yield


@decorator
def unless_module(module, name=None, import_errors=(ImportError,)):
    """Skip test if ``module`` can not be imported.

    :param module: Module to import.
    :keyword name: Alternative module name to use in reason.
    :keyword import_errors: Tuple of import errors to check for.
        Default is ``(ImportError,)``.

    Example::

        @skip.unless_module('librabbitmq')

    """
    try:
        importlib.import_module(module)
    except import_errors:
        raise SkipTest('module not installed: {0}'.format(name or module))
    yield


@decorator
def if_symbol(symbol, name=None,
              import_errors=(AttributeError, ImportError)):
    """Skip test if ``symbol`` can be imported.

    :param module: Symbol to import.
    :keyword name: Alternative symbol name to use in reason.
    :keyword import_errors: Tuple of import errors to check for.
        Default is ``(AttributeError, ImportError,)``.

    Example::

        @skip.if_symbol('django.db.transaction:on_commit')

    """
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
    """Skip test if ``symbol`` cannot be imported.

    :param module: Symbol to import.
    :keyword name: Alternative symbol name to use in reason.
    :keyword import_errors: Tuple of import errors to check for.
        Default is ``(AttributeError, ImportError,)``.

    Example::

        @skip.unless_symbol('django.db.transaction:on_commit')

    """
    try:
        symbol_by_name(symbol)
    except import_errors:
        raise SkipTest('missing symbol: {0}'.format(name or symbol))
    yield


@decorator
def if_platform(platform_name, name=None):
    """Skip test if :data:`sys.platform` name matches ``platform_name``.

    :param platform_name: Name to match with :data:`sys.platform`.
    :keyword name: Alternative name to use in reason.

    Example::

        @skip.if_platform('netbsd', name='NetBSD')

    """
    if sys.platform.startswith(platform_name):
        raise SkipTest('does not work on {0}'.format(platform_name or name))
    yield


def if_jython():
    """Skip test if running under Jython.

    Example::

        @skip.if_jython()

    """
    return if_platform('java', name='Jython')


def if_win32():
    """Skip test if running under Windows.

    Example::

        @skip.if_win32()

    """
    return if_platform('win32', name='Windows')


def if_darwin():
    """Skip test if running under OS X.

    Example::

        @skip.if_darwin()

    """
    return if_platform('darwin', name='OS X')


@decorator
def unless_platform(platform_name, name=None):
    """Skip test if :data:`sys.platform` name does not match ``platform_name``.

    :param platform_name: Name to match with :data:`sys.platform`.
    :keyword name: Alternative name to use in reason.

    Example::

        @skip.unless_platform('netbsd', name='NetBSD')

    """
    if not sys.platform.startswith(platform_name):
        raise SkipTest('only applicable on {0}'.format(platform_name or name))
    yield


def unless_jython():
    """Skip test if not running under Jython."""
    return unless_platform('java', name='Jython')


def unless_win32():
    """Skip test if not running under Windows."""
    return unless_platform('win32', name='Windows')


def unless_darwin():
    """Skip test if not running under OS X."""
    return unless_platform('darwin', name='OS X')


@decorator
def if_pypy(reason='does not work on PyPy'):
    """Skip test if running on PyPy.

    Example::

        @skip.if_pypy()

    """
    if getattr(sys, 'pypy_version_info', None):
        raise SkipTest(reason)
    yield


@decorator
def unless_pypy(reason='only applicable for PyPy'):
    """Skip test if not running on PyPy.

    Example::

        @skip.unless_pypy()

    """
    if not hasattr(sys, 'pypy_version_info'):
        raise SkipTest(reason)
    yield
