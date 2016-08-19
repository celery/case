=====================================================================
 Python unittest utilities
=====================================================================

|build-status| |coverage| |license| |wheel| |pyversion| |pyimp|

:Version: 1.3.0
:Web: http://case.readthedocs.org/
:Download: http://pypi.python.org/pypi/case/
:Source: http://github.com/celery/case/
:Keywords: testing utilities, python, unittest, mock

About
=====

.. _case-installation:

Installation
============

You can install case either via the Python Package Index (PyPI)
or from source.

To install using `pip`,::

    $ pip install -U case

To install using `easy_install`,::

    $ easy_install -U case

.. _case-installing-from-source:

Downloading and installing from source
--------------------------------------

Download the latest version of case from
http://pypi.python.org/pypi/case/

You can install it by doing the following,::

    $ tar xvfz case-0.0.0.tar.gz
    $ cd case-0.0.0
    $ python setup.py build
    # python setup.py install

The last command must be executed as a privileged user if
you are not currently using a virtualenv.

.. _case-installing-from-git:

Using the development version
-----------------------------

With pip
~~~~~~~~

You can install the latest snapshot of case using the following
pip command::

    $ pip install https://github.com/celery/case/zipball/master#egg=case

.. |build-status| image:: https://secure.travis-ci.org/celery/case.png?branch=master
    :alt: Build status
    :target: https://travis-ci.org/celery/case

.. |coverage| image:: https://codecov.io/github/celery/case/coverage.svg?branch=master
    :target: https://codecov.io/github/celery/case?branch=master

.. |license| image:: https://img.shields.io/pypi/l/case.svg
    :alt: BSD License
    :target: https://opensource.org/licenses/BSD-3-Clause

.. |wheel| image:: https://img.shields.io/pypi/wheel/case.svg
    :alt: Case can be installed via wheel
    :target: http://pypi.python.org/pypi/case/

.. |pyversion| image:: https://img.shields.io/pypi/pyversions/case.svg
    :alt: Supported Python versions.
    :target: http://pypi.python.org/pypi/case/

.. |pyimp| image:: https://img.shields.io/pypi/implementation/case.svg
    :alt: Support Python implementations.
    :target: http://pypi.python.org/pypi/case/

