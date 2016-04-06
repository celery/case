from __future__ import absolute_import, unicode_literals

from sphinx.ext import autodoc as _autodoc
from sphinx.util import inspect


def wrapped_getargspec(fun, *args, **kwargs):
    while 1:
        try:
            wrapped = fun.__wrapped__
            if wrapped is fun:
                break
            fun = wrapped
        except AttributeError:
            break
    return inspect.getargspec(fun, *args, **kwargs)
_autodoc.getargspec = wrapped_getargspec


def setup(app):
    app.require_sphinx('1.0')
