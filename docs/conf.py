# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, print_function

from sphinx_celery import conf

globals().update(conf.build_config(
    'case', __file__,
    project='Case',
    # version_dev='2.0',
    # version_stable='1.0',
    canonical_url='http://case.readthedocs.org',
    webdomain='celeryproject.org',
    github_project='celery/case',
    author='Ask Solem & contributors',
    author_name='Ask Solem',
    copyright='2016',
    publisher='Celery Project',
    html_logo='images/celery_128.png',
    html_favicon='images/favicon.ico',
    html_prepend_sidebars=['sidebardonations.html'],
    extra_extensions=[],
    include_intersphinx={'python', 'sphinx'},
))
