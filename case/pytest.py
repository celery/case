from __future__ import absolute_import, unicode_literals

import pytest
import sys

from functools import partial, wraps
from six import iteritems as items

from . import mock

sentinel = object()


class fixture_with_options(object):
    """Pytest fixture with options specified in separate decrorator.

    The decorated fixture MUST take the request fixture as first argument,
    but is free to use other fixtures.

    Example:
        @fixture_with_options()
        def sftp(request,
                 username='test_username',
                 password='test_password'):
            return {'username': username, 'password': password}

        @sftp.options(username='foo', password='bar')
        def test_foo(sftp):
            assert sftp['username'] == 'foo'
            assert sftp['password'] == 'bar'
    """

    def __init__(self, marker_name=None):
        self.marker_name = marker_name

    def __call__(self, fun):
        marker_name = self.marker_name or fun.__name__

        @pytest.fixture()
        @wraps(fun)
        def _inner(request, *args, **kwargs):
            marker = request.node.get_marker(marker_name)
            return fun(request, *args, **dict(marker.kwargs, **kwargs))
        _inner.options = partial(getattr(pytest.mark, marker_name))
        _inner.__wrapped__ = fun
        return _inner


class _patching(object):

    def __init__(self, monkeypatch, request):
        self.monkeypatch = monkeypatch
        self.request = request

    def __getattr__(self, name):
        return getattr(self.monkeypatch, name)

    def __call__(self, path, value=sentinel, name=None,
                 new=mock.MagicMock, **kwargs):
        value = self._value_or_mock(value, new, name, path, **kwargs)
        self.monkeypatch.setattr(path, value)
        return value

    def _value_or_mock(self, value, new, name, path, **kwargs):
        if value is sentinel:
            value = new(name=name or path.rpartition('.')[2])
        for k, v in items(kwargs):
            setattr(value, k, v)
        return value

    def setattr(self, target, name=sentinel, value=sentinel, **kwargs):
        # alias to __call__ with the interface of pytest.monkeypatch.setattr
        if value is sentinel:
            value, name = name, None
        return self(target, value, name=name)

    def setitem(self, dic, name, value=sentinel, new=mock.MagicMock, **kwargs):
        # same as pytest.monkeypatch.setattr but default value is MagicMock
        value = self._value_or_mock(value, new, name, dic, **kwargs)
        self.monkeypatch.setitem(dic, name, value)
        return value

    def modules(self, *mods):
        modules = []
        for mod in mods:
            mod = mod.split('.')
            modules.extend(reversed([
                '.'.join(mod[:-i] if i else mod) for i in range(len(mod))
            ]))
        modules = sorted(set(modules))
        return _wrap_context(mock.module(*modules), self.request)


def _wrap_context(context, request):
    ret = context.__enter__()

    def fin():
        context.__exit__(*sys.exc_info())
    request.addfinalizer(fin)
    return ret


@pytest.fixture()
def patching(monkeypatch, request):
    """Monkeypath.setattr shortcut.

    Example:
        .. code-block:: python

        def test_foo(patching):
            # execv value here will be mock.MagicMock by default.
            execv = patching('os.execv')

            patching('sys.platform', 'darwin')  # set concrete value
            patching.setenv('DJANGO_SETTINGS_MODULE', 'x.settings')

            # val will be of type mock.MagicMock by default
            val = patching.setitem('path.to.dict', 'KEY')
    """
    return _patching(monkeypatch, request)


class _stdouts(object):

    def __init__(self, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture()
def stdouts(request):
    return _stdouts(*_wrap_context(mock.stdouts(), request))
