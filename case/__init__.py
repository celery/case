"""Python unittest Utilities"""
from __future__ import absolute_import, unicode_literals

from .case import Case
from .mock import ANY, ContextMock, MagicMock, Mock, call, patch, sentinel

from . import mock
from . import skip

VERSION = (1, 1, 4)
__version__ = '.'.join(map(str, VERSION[0:3])) + ''.join(VERSION[3:])
__author__ = 'Ask Solem'
__contact__ = 'ask@celeryproject.org'
__homepage__ = 'http://github.com/celery/case'
__docformat__ = 'restructuredtext'

# -eof meta-

__all__ = [
    b'Case',

    b'ANY', b'ContextMock', b'MagicMock', b'Mock',
    b'call', b'patch',  b'sentinel',

    b'mock', b'skip',
]
