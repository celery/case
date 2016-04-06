from __future__ import absolute_import, unicode_literals

import re
import sys
import types
import warnings

from contextlib import contextmanager
from functools import partial
from six import string_types, itervalues as values, iteritems as items

from . import mock

try:
    import unittest  # noqa
    unittest.skip
    from unittest.util import safe_repr, unorderable_list_difference
except AttributeError:
    import unittest2 as unittest  # noqa
    from unittest2.util import safe_repr, unorderable_list_difference  # noqa

__all__ = ['Case']


# -- adds assertWarns from recent unittest2, not in Python 2.7.

class _AssertRaisesBaseContext(object):

    def __init__(self, expected, test_case, callable_obj=None,
                 expected_regex=None):
        self.expected = expected
        self.failureException = test_case.failureException
        self.obj_name = None
        if isinstance(expected_regex, string_types):
            expected_regex = re.compile(expected_regex)
        self.expected_regex = expected_regex


def _is_magic_module(m):
    # some libraries create custom module types that are lazily
    # lodaded, e.g. Django installs some modules in sys.modules that
    # will load _tkinter and other shit when touched.

    # pyflakes refuses to accept 'noqa' for this isinstance.
    cls, modtype = type(m), types.ModuleType
    try:
        variables = vars(cls)
    except TypeError:
        return True
    else:
        return (cls is not modtype and (
            '__getattr__' in variables or
            '__getattribute__' in variables))


class _AssertWarnsContext(_AssertRaisesBaseContext):
    """A context manager used to implement TestCase.assertWarns* methods."""

    def __enter__(self):
        # The __warningregistry__'s need to be in a pristine state for tests
        # to work properly.
        warnings.resetwarnings()
        for v in list(values(sys.modules)):
            # do not evaluate Django moved modules and other lazily
            # initialized modules.
            if v and not _is_magic_module(v):
                # use raw __getattribute__ to protect even better from
                # lazily loaded modules
                try:
                    object.__getattribute__(v, '__warningregistry__')
                except AttributeError:
                    pass
                else:
                    object.__setattr__(v, '__warningregistry__', {})
        self.warnings_manager = warnings.catch_warnings(record=True)
        self.warnings = self.warnings_manager.__enter__()
        warnings.simplefilter('always', self.expected)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.warnings_manager.__exit__(exc_type, exc_value, tb)
        if exc_type is not None:
            # let unexpected exceptions pass through
            return
        try:
            exc_name = self.expected.__name__
        except AttributeError:
            exc_name = str(self.expected)
        first_matching = None
        for m in self.warnings:
            w = m.message
            if not isinstance(w, self.expected):
                continue
            if first_matching is None:
                first_matching = w
            if (self.expected_regex is not None and
                    not self.expected_regex.search(str(w))):
                continue
            # store warning for later retrieval
            self.warning = w
            self.filename = m.filename
            self.lineno = m.lineno
            return
        # Now we simply try to choose a helpful failure message
        if first_matching is not None:
            raise self.failureException(
                '%r does not match %r' % (
                    self.expected_regex.pattern, str(first_matching)))
        if self.obj_name:
            raise self.failureException(
                '%s not triggered by %s' % (exc_name, self.obj_name))
        else:
            raise self.failureException('%s not triggered' % exc_name)


class CaseMixin(object):
    """Mixin class that adds the utility methods to any unittest TestCase
    class."""

    def patch(self, *path, **options):
        """Patch object until test case returns.

        Example::

            from case import Case

            class test_Frobulator(Case):

                def setup(self):
                    frobulate = self.patch('some.where.Frobulator.frobulate')

        """
        manager = mock.patch('.'.join(path), **options)
        patched = manager.start()
        self.addCleanup(manager.stop)
        return patched

    def mock_modules(self, *mods):
        """Mock modules for the duration of the test.

        See :func:`case.mock.module`

        """
        modules = []
        for mod in mods:
            mod = mod.split('.')
            modules.extend(reversed([
                '.'.join(mod[:-i] if i else mod) for i in range(len(mod))
            ]))
        modules = sorted(set(modules))
        return self.wrap_context(mock.module(*modules))

    def mask_modules(self, *modules):
        """Make modules for the duration of the test.

        See :func:`case.mock.mask_modules`.

        """
        self.wrap_context(mock.mask_modules(*modules))

    def wrap_context(self, context):
        """Wrap context so that the context exits when the test completes."""
        ret = context.__enter__()
        self.addCleanup(partial(context.__exit__, None, None, None))
        return ret

    def mock_environ(self, env_name, env_value):
        """Mock environment variable value for the duration of the test.

        See :func:`case.mock.environ`.

        """
        return self.wrap_context(mock.environ(env_name, env_value))


class Case(unittest.TestCase, CaseMixin):
    """Test Case

    Subclass of :class:`unittest.TestCase` adding convenience
    methods.

    **setup / teardown**

    New :meth:`setup` and :meth:`teardown` methods can be defined
    in addition to the core :meth:`setUp` + :meth:`tearDown`
    methods.

    Note: If you redefine the core :meth:`setUp` + :meth:`tearDown`
          methods you must make sure ``super`` is called.
          ``super`` is not necessary for the lowercase versions.

    **Python 2.6 compatibility**

    This class also implements :meth:`assertWarns`, :meth:`assertWarnsRegex`,
    :meth:`assertDictContainsSubset`, and :meth:`assertItemsEqual`
    which are not available in the original Python 2.6 unittest
    implementation.

    """
    DeprecationWarning = DeprecationWarning
    PendingDeprecationWarning = PendingDeprecationWarning

    def setUp(self):
        self.setup()

    def tearDown(self):
        self.teardown()

    def setup(self):
        pass

    def teardown(self):
        pass

    def assertWarns(self, expected_warning):
        return _AssertWarnsContext(expected_warning, self, None)

    def assertWarnsRegex(self, expected_warning, expected_regex):
        return _AssertWarnsContext(expected_warning, self,
                                   None, expected_regex)

    @contextmanager
    def assertDeprecated(self):
        with self.assertWarnsRegex(self.DeprecationWarning,
                                   r'scheduled for removal'):
            yield

    @contextmanager
    def assertPendingDeprecation(self):
        with self.assertWarnsRegex(self.PendingDeprecationWarning,
                                   r'scheduled for deprecation'):
            yield

    def assertDictContainsSubset(self, expected, actual, msg=None):
        missing, mismatched = [], []

        for key, value in items(expected):
            if key not in actual:
                missing.append(key)
            elif value != actual[key]:
                mismatched.append('%s, expected: %s, actual: %s' % (
                    safe_repr(key), safe_repr(value),
                    safe_repr(actual[key])))

        if not (missing or mismatched):
            return

        standard_msg = ''
        if missing:
            standard_msg = 'Missing: %s' % ','.join(map(safe_repr, missing))

        if mismatched:
            if standard_msg:
                standard_msg += '; '
            standard_msg += 'Mismatched values: %s' % (
                ','.join(mismatched))

        self.fail(self._formatMessage(msg, standard_msg))

    def assertItemsEqual(self, expected_seq, actual_seq, msg=None):
        missing = unexpected = None
        try:
            expected = sorted(expected_seq)
            actual = sorted(actual_seq)
        except TypeError:
            # Unsortable items (example: set(), complex(), ...)
            expected = list(expected_seq)
            actual = list(actual_seq)
            missing, unexpected = unorderable_list_difference(
                expected, actual)
        else:
            return self.assertSequenceEqual(expected, actual, msg=msg)

        errors = []
        if missing:
            errors.append(
                'Expected, but missing:\n    %s' % (safe_repr(missing),)
            )
        if unexpected:
            errors.append(
                'Unexpected, but present:\n    %s' % (safe_repr(unexpected),)
            )
        if errors:
            standardMsg = '\n'.join(errors)
            self.fail(self._formatMessage(msg, standardMsg))
