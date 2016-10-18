"""Python unittest Utilities"""
from __future__ import absolute_import, unicode_literals

import re

from collections import namedtuple

from .case import Case
from .mock import ANY, ContextMock, MagicMock, Mock, call, patch, sentinel

from . import mock
from . import skip

__version__ = '1.4.0'
__author__ = 'Ask Solem'
__contact__ = 'ask@celeryproject.org'
__homepage__ = 'http://github.com/celery/case'
__docformat__ = 'restructuredtext'

# -eof meta-

version_info_t = namedtuple('version_info_t', (
    'major', 'minor', 'micro', 'releaselevel', 'serial'
))

# bumpversion can only search for {current_version}
# so we have to parse the version here.
_temp = re.match(
    r'(\d+)\.(\d+).(\d+)(.+)?', __version__).groups()
VERSION = version_info = version_info_t(
    int(_temp[0]), int(_temp[1]), int(_temp[2]), _temp[3] or '', '')
del(_temp)
del(re)

__all__ = [
    b'Case',

    b'ANY', b'ContextMock', b'MagicMock', b'Mock',
    b'call', b'patch', b'sentinel',

    b'mock', b'skip',
]
