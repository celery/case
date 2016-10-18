from __future__ import absolute_import, unicode_literals

import importlib
import inspect
import logging
import os
import platform
import sys
import time
import types

from contextlib import contextmanager
from functools import wraps
from six import reraise, string_types, iteritems as items
from six.moves import builtins

from .utils import WhateverIO, decorator, get_logger_handlers, noop

try:
    from importlib import reload
except ImportError:
    try:
        from imp import reload
    except ImportError:
        reload = reload

try:
    from unittest import mock
except ImportError:
    import mock  # noqa

PY3 = sys.version_info[0] >= 3
if PY3:
    open_fqdn = 'builtins.open'
    module_name_t = str
else:
    open_fqdn = '__builtin__.open'  # noqa
    module_name_t = bytes  # noqa

__all__ = [
    'ANY', 'ContextMock', 'MagicMock', 'Mock', 'MockCallbacks',
    'call', 'patch', 'sentinel',

    'wrap_logger', 'environ', 'sleepdeprived', 'mask_modules', 'mute',
    'stdouts', 'replace_module_value', 'sys_version', 'pypy_version',
    'platform_pyimp', 'sys_platform', 'reset_modules', 'module',
    'open', 'restore_logging', 'module_exists', 'create_patcher',
]

ANY = mock.ANY
call = mock.call
sentinel = mock.sentinel


def create_patcher(*partial_path):

    def patcher(name, *args, **kwargs):
        return patch(".".join(partial_path + (name, )), *args, **kwargs)
    return patcher


class MockMixin(object):

    def on_nth_call_do(self, side_effect, n=1):
        """Change Mock side effect after ``n`` calls.

        Example::

            mock.on_nth_call_do(RuntimeError, n=3)

        """
        def on_call(*args, **kwargs):
            if self.call_count >= n:
                self.side_effect = side_effect
            return self.return_value
        self.side_effect = on_call
        return self

    def on_nth_call_do_raise(self, excA, excB, n=1):
        """Change exception raised after ``n`` calls.

        Mock will raise excA until called `n` times, which after
        it will raise excB'.

        Example::

            >>> mock.on_nth_call_do_raise(KeyError(), RuntimError(), n=3)
            >>> mock()
            KeyError()
            >>> mock()
            KeyError()
            >>> mock()
            KeyError()
            >>> mock()
            RuntimeError()

        """
        def on_call(*args, **kwargs):
            if self.call_count >= n:
                self.side_effect = excB
            raise excA
        self.side_effect = on_call
        return self

    def on_nth_call_return(self, retval, n=1):
        """Change Mock to return specific return value after ``n`` calls.

        Example::

            mock.on_nth_call_return('STOP', n=3)

        """

        def on_call(*args, **kwargs):
            if self.call_count >= n:
                self.return_value = retval
            return self.return_value
        self.side_effect = on_call
        return self

    def _mock_update_attributes(self, attrs={}, **kwargs):
        for key, value in items(attrs):
            setattr(self, key, value)

    def assert_not_called(_mock_self):  # noqa
        """assert that the mock was never called."""
        self = _mock_self
        if self.call_count != 0:
            msg = ("Expected '%s' to not have been called. Called %s times." %
                   (self._mock_name or 'mock', self.call_count))
            raise AssertionError(msg)

    def assert_called(_mock_self):  # noqa
        """assert that the mock was called at least once."""
        self = _mock_self
        if self.call_count == 0:
            msg = ("Expected '%s' to have been called." %
                   self._mock_name or 'mock')
            raise AssertionError(msg)

    def assert_called_once(_mock_self):  # noqa
        """assert that the mock was called only once."""
        self = _mock_self
        if not self.call_count == 1:
            msg = ("Expected '%s' to have been called once. Called %s times." %
                   (self._mock_name or 'mock', self.call_count))
            raise AssertionError(msg)


class Mock(mock.Mock, MockMixin):

    def __init__(self, *args, **kwargs):
        super(Mock, self).__init__(*args, **kwargs)
        self._mock_update_attributes(**kwargs)


class MagicMock(mock.MagicMock, MockMixin):

    def __init__(self, *args, **kwargs):
        super(MagicMock, self).__init__(*args, **kwargs)
        self._mock_update_attributes(**kwargs)


class _ContextMock(Mock):
    """Dummy class implementing __enter__ and __exit__
    as the :keyword:`with` statement requires these to be implemented
    in the class, not just the instance."""

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass


def ContextMock(*args, **kwargs):
    """Mock that mocks :keyword:`with` statement contexts."""
    obj = _ContextMock(*args, **kwargs)
    obj.attach_mock(_ContextMock(), '__enter__')
    obj.attach_mock(_ContextMock(), '__exit__')
    obj.__enter__.return_value = obj
    # if __exit__ return a value the exception is ignored,
    # so it must return None here.
    obj.__exit__.return_value = None
    return obj


def _patch_sig1(target,
                new=None, spec=None, create=None,
                spec_set=None, autospec=None, new_callable=None, **kwargs):
    # signature for mock.patch,
    # used to inject new `new_callable` argument default.
    return new, autospec, new_callable


def _patch_sig2(target, attribute,
                new=None, spec=None, create=False, spec_set=None,
                autospec=None, new_callable=None, **kwargs):
    # signature for mock.patch.multiple + mock.patch.object,
    # used to inject new `new_callable` argument default.
    return new, autospec, new_callable


def _create_patcher(fun, signature):

    @wraps(fun)
    def patcher(*args, **kwargs):
        new, autospec, new_callable = signature(*args, **kwargs)
        if new is None and autospec is None and new_callable is None:
            kwargs.setdefault('new_callable', MagicMock)
        return fun(*args, **kwargs)

    return patcher
patch = _create_patcher(mock.patch, _patch_sig1)
patch.dict = mock.patch.dict
patch.multiple = _create_patcher(mock.patch.multiple, _patch_sig2)
patch.object = _create_patcher(mock.patch.object, _patch_sig2)
patch.stopall = mock.patch.stopall
patch.TEST_PREFIX = mock.patch.TEST_PREFIX


def _bind(f, o):
    @wraps(f)
    def bound_meth(*fargs, **fkwargs):
        return f(o, *fargs, **fkwargs)
    return bound_meth


if PY3:  # pragma: no cover
    def _get_class_fun(meth):
        return meth

    def module_name(s):
        if isinstance(s, bytes):
            return s.decode()
        return s
else:
    def _get_class_fun(meth):  # noqa
        return meth.__func__

    def module_name(s):  # noqa
        if isinstance(s, unicode):
            return s.encode()
        return s


class MockCallbacks(object):

    def __new__(cls, *args, **kwargs):
        r = Mock(name=cls.__name__)
        _get_class_fun(cls.__init__)(r, *args, **kwargs)
        for key, value in items(vars(cls)):
            if key not in ('__dict__', '__weakref__', '__new__', '__init__'):
                if inspect.ismethod(value) or inspect.isfunction(value):
                    r.__getattr__(key).side_effect = _bind(value, r)
                else:
                    r.__setattr__(key, value)
        return r


@decorator
def wrap_logger(logger, loglevel=logging.ERROR):
    """Wrap :class:`logging.Logger` with a StringIO() handler.

    yields a StringIO handle.

    Example::

        with mock.wrap_logger(logger, loglevel=logging.DEBUG) as sio:
            ...
            sio.getvalue()

    """
    old_handlers = get_logger_handlers(logger)
    sio = WhateverIO()
    siohandler = logging.StreamHandler(sio)
    logger.handlers = [siohandler]

    try:
        yield sio
    finally:
        logger.handlers = old_handlers


@decorator
def environ(env_name, env_value):
    """Mock environment variable value.

    Example::

        @mock.environ('DJANGO_SETTINGS_MODULE', 'proj.settings')
        def test_other_settings(self):
            ...

    """
    sentinel = object()
    prev_val = os.environ.get(env_name, sentinel)
    os.environ[env_name] = env_value
    try:
        yield
    finally:
        if prev_val is sentinel:
            os.environ.pop(env_name, None)
        else:
            os.environ[env_name] = prev_val


@decorator
def sleepdeprived(module=time):
    """Mock time.sleep to do nothing.

    Example::

        @mock.sleepdeprived()  # < patches time.sleep
        @mock.sleepdeprived(celery.result)  # < patches celery.result.sleep

    """
    old_sleep, module.sleep = module.sleep, noop
    try:
        yield
    finally:
        module.sleep = old_sleep


# Taken from
# http://bitbucket.org/runeh/snippets/src/tip/missing_modules.py
@decorator
def mask_modules(*modnames):
    """Ban some modules from being importable inside the context

    For example::

        >>> with mask_modules('sys'):
        ...     try:
        ...         import sys
        ...     except ImportError:
        ...         print('sys not found')
        sys not found

        >>> import sys  # noqa
        >>> sys.version
        (2, 5, 2, 'final', 0)

    Or as a decorator::

        @mask_modules('sys')
        def test_foo(self):
            ...

    """
    realimport = builtins.__import__

    def myimp(name, *args, **kwargs):
        if name in modnames:
            raise ImportError('No module named %s' % name)
        else:
            return realimport(name, *args, **kwargs)

    builtins.__import__ = myimp
    try:
        yield
    finally:
        builtins.__import__ = realimport


@decorator
def stdouts():
    """Override `sys.stdout` and `sys.stderr` with `StringIO`
    instances.

    Decorator example::

        @mock.stdouts
        def test_foo(self, stdout, stderr):
            something()
            self.assertIn('foo', stdout.getvalue())

    Context example::

        with mock.stdouts() as (stdout, stderr):
            something()
            self.assertIn('foo', stdout.getvalue())

    """
    prev_out, prev_err = sys.stdout, sys.stderr
    prev_rout, prev_rerr = sys.__stdout__, sys.__stderr__
    mystdout, mystderr = WhateverIO(), WhateverIO()
    sys.stdout = sys.__stdout__ = mystdout
    sys.stderr = sys.__stderr__ = mystderr

    try:
        yield mystdout, mystderr
    finally:
        sys.stdout = prev_out
        sys.stderr = prev_err
        sys.__stdout__ = prev_rout
        sys.__stderr__ = prev_rerr


@decorator
def mute():
    """Redirect `sys.stdout` and `sys.stderr` to /dev/null, silencent them.
    Decorator example::
        @mock.mute
        def test_foo(self):
            something()
    Context example::
        with mock.mute():
            something()
    """
    prev_out, prev_err = sys.stdout, sys.stderr
    prev_rout, prev_rerr = sys.__stdout__, sys.__stderr__
    devnull = open(os.devnull, 'w')
    mystdout, mystderr = devnull, devnull
    sys.stdout = sys.__stdout__ = mystdout
    sys.stderr = sys.__stderr__ = mystderr

    try:
        yield
    finally:
        sys.stdout = prev_out
        sys.stderr = prev_err
        sys.__stdout__ = prev_rout
        sys.__stderr__ = prev_rerr


@decorator
def replace_module_value(module, name, value=None):
    """Mock module value, given a module, attribute name and value.

    Decorator example::

        @mock.replace_module_value(module, 'CONSTANT', 3.03)
        def test_foo(self):
            ...

    Context example::

        with mock.replace_module_value(module, 'CONSTANT', 3.03):
            ...

    """
    has_prev = hasattr(module, name)
    prev = getattr(module, name, None)
    if value:
        setattr(module, name, value)
    else:
        try:
            delattr(module, name)
        except AttributeError:
            pass
    try:
        yield
    finally:
        if prev is not None:
            setattr(module, name, prev)
        if not has_prev:
            try:
                delattr(module, name)
            except AttributeError:
                pass


def sys_version(value=None):
    """Mock :data:`sys.version_info`

    Decorator example::

        @mock.sys_version((3, 6, 1))
        def test_foo(self):
            ...

    Context example::

        with mock.sys_version((3, 6, 1)):
            ...

    """
    return replace_module_value(sys, 'version_info', value)


def pypy_version(value=None):
    """Mock :data:`sys.pypy_version_info`

    Decorator example::

        @mock.pypy_version((3, 6, 1))
        def test_foo(self):
            ...

    Context example::

        with mock.pypy_version((3, 6, 1)):
            ...

    """
    return replace_module_value(sys, 'pypy_version_info', value)


def platform_pyimp(value=None):
    """Mock :data:`platform.python_implementation`

    Decorator example::

        @mock.platform_pyimp('PyPy')
        def test_foo(self):
            ...

    Context example::

        with mock.platform_pyimp('PyPy'):
            ...

    """
    return replace_module_value(platform, 'python_implementation', value)


@decorator
def sys_platform(value=None):
    """Mock :data:`sys.platform`

    Decorator example::

        @mock.sys_platform('darwin')
        def test_foo(self):
            ...

    Context example::

        with mock.sys_platform('darwin'):
            ...

    """

    prev, sys.platform = sys.platform, value
    try:
        yield
    finally:
        sys.platform = prev


@decorator
def reset_modules(*modules):
    """Remove modules from :data:`sys.modules` by name,
    and reset back again when the test/context returns.

    Decorator example::

        @mock.reset_modules('celery.result', 'celery.app.base')
        def test_foo(self):
            pass

    Context example::

        with mock.reset_modules('celery.result', 'celery.app.base'):
            pass

    """
    prev = dict((k, sys.modules.pop(k))
                for k in modules if k in sys.modules)
    try:
        for k in modules:
            reload(importlib.import_module(k))
        yield
    finally:
        sys.modules.update(prev)


@decorator
def module(*names):
    """Mock one or modules such that every attribute is a :class:`Mock`."""
    prev = {}

    class MockModule(types.ModuleType):

        def __getattr__(self, attr):
            setattr(self, attr, Mock())
            return types.ModuleType.__getattribute__(self, attr)

    mods = []
    for name in names:
        try:
            prev[name] = sys.modules[name]
        except KeyError:
            pass
        mod = sys.modules[name] = MockModule(module_name(name))
        mods.append(mod)
    try:
        yield mods
    finally:
        for name in names:
            try:
                sys.modules[name] = prev[name]
            except KeyError:
                try:
                    del(sys.modules[name])
                except KeyError:
                    pass


@contextmanager
def mock_context(mock, typ=Mock):
    context = mock.return_value = Mock()
    context.__enter__ = typ()
    context.__exit__ = typ()

    def on_exit(*x):
        if x[0]:
            reraise(x[0], x[1], x[2])
    context.__exit__.side_effect = on_exit
    context.__enter__.return_value = context
    try:
        yield context
    finally:
        context.reset()


@decorator
def open(typ=WhateverIO, side_effect=None):
    """Patch builtins.open so that it returns StringIO object.

    :param typ: File object for open to return.
        Defaults to :class:`WhateverIO` which is the bastard child
        of :class:`io.StringIO` and :class:`io.BytesIO` accepting
        both bytes and unicode input.
    :param side_effect: Additional side effect for when the open context
        is entered.

    Decorator example::

        @mock.open()
        def test_foo(self, open_fh):
            something_opening_and_writing_a_file()
            self.assertIn('foo', open_fh.getvalue())

    Context example::

        with mock.open(io.BytesIO) as open_fh:
            something_opening_and_writing_bytes_to_a_file()
            self.assertIn(b'foo', open_fh.getvalue())

    """
    with patch(open_fqdn) as open_:
        with mock_context(open_) as context:
            if side_effect is not None:
                context.__enter__.side_effect = side_effect
            val = context.__enter__.return_value = typ()
            val.__exit__ = Mock()
            yield val


@decorator
def restore_logging():
    """Restore root logger handlers after test returns.

    Decorator example::

        @mock.restore_logging()
        def test_foo(self):
            setup_logging()

    Context example::

        with mock.restore_logging():
            setup_logging()

    """
    outs = sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__
    root = logging.getLogger()
    level = root.level
    handlers = root.handlers

    try:
        yield
    finally:
        sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__ = outs
        root.level = level
        root.handlers[:] = handlers


@decorator
def module_exists(*modules):
    """Patch one or more modules to ensure they exist.

    A module name with multiple paths (e.g. gevent.monkey) will
    ensure all parent modules are also patched (``gevent`` +
    ``gevent.monkey``).

    Decorator example::

        @mock.module_exists('gevent.monkey')
        def test_foo(self):
            pass

    Context example::

        with mock.module_exists('gevent.monkey'):
            gevent.monkey.patch_all = Mock(name='patch_all')
            ...

    """
    gen = []
    old_modules = []
    for module in modules:
        if isinstance(module, string_types):
            module = types.ModuleType(module_name(module))
        gen.append(module)
        if module.__name__ in sys.modules:
            old_modules.append(sys.modules[module.__name__])
        sys.modules[module.__name__] = module
        name = module.__name__
        if '.' in name:
            parent, _, attr = name.rpartition('.')
            setattr(sys.modules[parent], attr, module)
    try:
        yield
    finally:
        for module in gen:
            sys.modules.pop(module.__name__, None)
        for module in old_modules:
            sys.modules[module.__name__] = module
