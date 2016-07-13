import importlib
import inspect
import logging
import sys

from contextlib import contextmanager
from functools import wraps
from typing import (
    Any, AnyStr, Callable, Dict, Mapping, Sequence, Tuple, cast,
)

__all__ = [
    'decorator', 'get_logger_handlers', 'noop',
    'symbol_by_name', 'want_str',
]


def want_str(s: AnyStr) -> str:
    if isinstance(s, bytes):
        return cast(bytes, s).decode()
    return s


class _CallableContext(object):

    def __init__(self, context: Any,
                 cargs: Tuple[Any, ...], ckwargs: Dict, fun: Callable) -> None:
        self.context = context
        self.cargs = cargs
        self.ckwargs = ckwargs
        self.fun = fun

    def __call__(self, *args, **kwargs) -> Any:
        return self.fun(*args, **kwargs)

    def __enter__(self) -> Any:
        self.ctx = self.context(*self.cargs, **self.ckwargs)
        return self.ctx.__enter__()

    def __exit__(self, *einfo) -> Any:
        if self.ctx:
            return self.ctx.__exit__(*einfo)


def decorator(predicate: Callable) -> Callable:
    context = contextmanager(predicate)

    @wraps(predicate)
    def take_arguments(*pargs, **pkwargs) -> Callable:

        @wraps(predicate)
        def decorator(cls) -> Callable:
            if inspect.isclass(cls):
                orig_setup = cls.setUp
                orig_teardown = cls.tearDown

                @wraps(cls.setUp)
                def around_setup(*args, **kwargs) -> None:
                    try:
                        contexts = args[0].__rb3dc_contexts__
                    except AttributeError:
                        contexts = args[0].__rb3dc_contexts__ = []
                    p = context(*pargs, **pkwargs)
                    p.__enter__()
                    contexts.append(p)
                    orig_setup(*args, **kwargs)
                cls.setUp = around_setup

                @wraps(cls.tearDown)
                def around_teardown(*args, **kwargs) -> None:
                    try:
                        contexts = args[0].__rb3dc_contexts__
                    except AttributeError:
                        pass
                    else:
                        for context in contexts:
                            context.__exit__(*sys.exc_info())
                    orig_teardown(*args, **kwargs)
                cls.tearDown = around_teardown

                return cls
            else:
                @wraps(cls)
                def around_case(self, *args, **kwargs) -> Any:
                    with context(*pargs, **pkwargs) as context_args:
                        context_args = context_args or ()
                        if not isinstance(context_args, tuple):
                            context_args = (context_args,)
                        return cls(*(self,) + args + context_args, **kwargs)
                return around_case

        if len(pargs) == 1 and callable(pargs[0]):
            fun, pargs = pargs[0], ()
            return decorator(fun)
        return cast(Callable, _CallableContext(
            context, pargs, pkwargs, decorator))
    return take_arguments


def get_logger_handlers(logger: logging.Logger) -> Sequence[logging.Handler]:
    return [
        h for h in cast(Any, logger).handlers
        if not isinstance(h, logging.NullHandler)
    ]


def symbol_by_name(name: Any, aliases: Mapping[str, str] = {},
                   imp: Callable = None, package: str = None,
                   sep: str = '.', default: Any = None, **kwargs) -> Any:
    """Get symbol by qualified name.

    The name should be the full dot-separated path to the class::

        modulename.ClassName

    Example::

        celery.concurrency.processes.TaskPool
                                    ^- class name

    or using ':' to separate module and symbol::

        celery.concurrency.processes:TaskPool

    If `aliases` is provided, a dict containing short name/long name
    mappings, the name is looked up in the aliases first.

    Examples:

        >>> symbol_by_name('celery.concurrency.processes.TaskPool')
        <class 'celery.concurrency.processes.TaskPool'>

        >>> symbol_by_name('default', {
        ...     'default': 'celery.concurrency.processes.TaskPool'})
        <class 'celery.concurrency.processes.TaskPool'>

        # Does not try to look up non-string names.
        >>> from celery.concurrency.processes import TaskPool
        >>> symbol_by_name(TaskPool) is TaskPool
        True

    """
    if not isinstance(name, str):
        return name
    return _symbol_by_name(
        name, aliases, imp, package, sep, default, **kwargs)


def _symbol_by_name(name: str, aliases: Mapping[str, str] = {},
                    imp: Callable = None, package: str = None,
                    sep: str = '.', default: Any = None, **kwargs) -> Any:
    if imp is None:
        imp = importlib.import_module
    name = aliases.get(name) or name
    sep = ':' if ':' in name else sep
    module_name, _, cls_name = name.rpartition(sep)
    if not module_name:
        cls_name, module_name = None, package if package else cls_name
    try:
        try:
            module = imp(module_name, package=package, **kwargs)
        except ValueError as exc:
            raise ValueError(
                "Couldn't import {0!r}: {1}".format(name, exc)).with_traceback(
                    sys.exc_info()[2])
        return getattr(module, cls_name) if cls_name else module
    except (ImportError, AttributeError):
        if default is None:
            raise
    return default


def noop(*args, **kwargs):
    pass
