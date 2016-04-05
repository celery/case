from __future__ import absolute_import, unicode_literals

import inspect
import logging
import os
import platform
import sys
import time
import types

from contextlib import contextmanager
from functools import partial, wraps
from six import reraise, string_types, iteritems as items
from six.moves import builtins

from .utils import WhateverIO, decorator, get_logger_handlers, noop

try:
    from unittest import mock
except ImportError:
    import mock  # noqa

PY3 = sys.version_info[0] > 3
if PY3:
    open_fqdn = 'builtins.open'
    module_name_t = str
else:
    open_fqdn = '__builtin__.open'  # noqa
    module_name_t = bytes  # noqa

__all__ = [
    'ANY', 'ContextMock', 'MagicMock', 'Mock', 'MockCallbacks',
    'call', 'patch', 'sentinel',

    'wrap_logger', 'environ', 'sleepdeprived', 'mask_modules',
    'stdouts', 'replace_module_value', 'pypy_version', 'platform_pyimp',
    'sys_platform', 'reset_modules', 'patch_modules', 'module', 'open',
    'restore_logging', 'module_exists',
]

ANY = mock.ANY
call = mock.call
patch = mock.patch
sentinel = mock.sentinel


class MockMixin(object):

    def on_nth_call_do(self, side_effect, n=1):

        def on_call(*args, **kwargs):
            if self.call_count >= n:
                self.side_effect = side_effect
            return self.return_value
        self.side_effect = on_call
        return self

    def on_nth_call_return(self, retval, n=1):

        def on_call(*args, **kwargs):
            if self.call_count >= n:
                self.return_value = retval
            return self.return_value
        self.side_effect = on_call
        return self

    def _mock_update_attributes(self, attrs={}, **kwargs):
        for key, value in items(attrs):
            setattr(self, key, value)


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
    obj = _ContextMock(*args, **kwargs)
    obj.attach_mock(_ContextMock(), '__enter__')
    obj.attach_mock(_ContextMock(), '__exit__')
    obj.__enter__.return_value = obj
    # if __exit__ return a value the exception is ignored,
    # so it must return None here.
    obj.__exit__.return_value = None
    return obj


def _bind(f, o):
    @wraps(f)
    def bound_meth(*fargs, **fkwargs):
        return f(o, *fargs, **fkwargs)
    return bound_meth


if PY3:  # pragma: no cover
    def _get_class_fun(meth):
        return meth
else:
    def _get_class_fun(meth):
        return meth.__func__


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

    For example:

        >>> with mask_modules('sys'):
        ...     try:
        ...         import sys
        ...     except ImportError:
        ...         print('sys not found')
        sys not found

        >>> import sys  # noqa
        >>> sys.version
        (2, 5, 2, 'final', 0)

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
    """Override `sys.stdout` and `sys.stderr` with `WhateverIO`."""
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
def replace_module_value(module, name, value=None):
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
pypy_version = partial(
    replace_module_value, sys, 'pypy_version_info',
)
platform_pyimp = partial(
    replace_module_value, platform, 'python_implementation',
)


@decorator
def sys_platform(value):
    prev, sys.platform = sys.platform, value
    try:
        yield
    finally:
        sys.platform = prev


@decorator
def reset_modules(*modules):
    prev = {k: sys.modules.pop(k) for k in modules if k in sys.modules}
    try:
        yield
    finally:
        sys.modules.update(prev)


@decorator
def patch_modules(*modules):
    prev = {}
    for mod in modules:
        prev[mod] = sys.modules.get(mod)
        sys.modules[mod] = types.ModuleType(module_name_t(mod))
    try:
        yield
    finally:
        for name, mod in items(prev):
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod


@decorator
def module(*names):
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
        mod = sys.modules[name] = MockModule(module_name_t(name))
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
    with patch(open_fqdn) as open_:
        with mock_context(open_) as context:
            if side_effect is not None:
                context.__enter__.side_effect = side_effect
            val = context.__enter__.return_value = typ()
            val.__exit__ = Mock()
            yield val


@decorator
def restore_logging():
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
    gen = []
    old_modules = []
    for module in modules:
        if isinstance(module, string_types):
            module = types.ModuleType(module_name_t(module))
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
