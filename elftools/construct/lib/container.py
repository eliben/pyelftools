"""
Various containers.
"""
from __future__ import annotations

from collections.abc import MutableMapping
from pprint import pformat
from typing import IO, TYPE_CHECKING, Any, Literal, TypeVar, overload

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Self  # 3.11+

    from typing_extensions import Concatenate, ParamSpec  # 3.10+

    from ..core import Construct
    from .hex import HexString

    _P = ParamSpec('_P')
    _R = TypeVar('_R')
    _T = TypeVar('_T')


__all__ = [
    "recursion_lock",
    "Container", "FlagsContainer", "ListContainer", "LazyContainer",
]


def recursion_lock(
    retval: _R,
    lock_name: str = "__recursion_lock__",
) -> Callable[[Callable[Concatenate[Any, _P], _T]], Callable[Concatenate[Any, _P], _T | _R]]:

    def decorator(
        func: Callable[Concatenate[Any, _P], _T],
    ) -> Callable[Concatenate[Any, _P], _T | _R]:
        def wrapper(self: Any, *args: _P.args, **kw: _P.kwargs) -> _T | _R:
            if getattr(self, lock_name, False):
                return retval
            setattr(self, lock_name, True)
            try:
                return func(self, *args, **kw)
            finally:
                setattr(self, lock_name, False)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator

class Container(MutableMapping[str, Any]):
    """
    A generic container of attributes.

    Containers are the common way to express parsed data.
    """

    def __init__(self, **kw: Any) -> None:
        self.__dict__ = kw

    # The core dictionary interface.

    @overload
    def __getitem__(self, name: Literal[
        "ch_addralign", "ch_size",
        "length",
        "n_descsz", "n_offset", "n_namesz",
        "sh_addralign", "sh_flags", "sh_size",
        "bloom_size", "nbuckets",
    ]) -> int: ...
    @overload
    def __getitem__(self, name: Literal[
        "ch_type",
        "sh_type",
        "n_name", "n_type",
        "tag", "vendor_name",
    ]) -> str: ...
    @overload
    def __getitem__(self, name: str) -> Any: ...
    def __getitem__(self, name: str) -> Any:
        return self.__dict__[name]

    def __delitem__(self, name: str) -> None:
        del self.__dict__[name]

    def __setitem__(self, name: str, value: Any) -> None:
        self.__dict__[name] = value

    def __iter__(self) -> Iterator[str]:
        return iter(self.__dict__)

    def __len__(self) -> int:
        return len(self.__dict__.keys())

    # Copy interface.

    def copy(self) -> Self:
        return self.__class__(**self.__dict__)

    __copy__ = copy

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, repr(self.__dict__))

    def __str__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, str(self.__dict__))

    if TYPE_CHECKING:
        # elftools.construct.debug Probe.printout()
        stream_position: int
        following_stream_data: str | HexString
        context: Container
        stack: ListContainer
        # allow arbitray attributes
        def __setattr__(self, name: str, value: object) -> None: ...
        def __getattr__(self, name: str) -> Any: ...

class FlagsContainer(Container):
    """
    A container providing pretty-printing for flags.

    Only set flags are displayed.
    """

    @recursion_lock("<...>")
    def __str__(self) -> str:
        d = dict((k, self[k]) for k in self
                 if self[k] and not k.startswith("_"))
        return "%s(%s)" % (self.__class__.__name__, pformat(d))

class ListContainer(list[Any]):
    """
    A container for lists.
    """

    __slots__ = ["__recursion_lock__"]

    @recursion_lock("[...]")
    def __str__(self) -> str:
        return pformat(self)

class LazyContainer:

    __slots__ = ["subcon", "stream", "pos", "context", "_value"]

    def __init__(self, subcon: Construct, stream: IO[bytes], pos: int, context: Container) -> None:
        self.subcon = subcon
        self.stream = stream
        self.pos = pos
        self.context = context
        self._value = NotImplemented

    def __eq__(self, other: object) -> bool:
        try:
            return self._value == other._value  # type: ignore[attr-defined]
        except AttributeError:
            return False

    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def __str__(self) -> str:
        return self.__pretty_str__()

    def __pretty_str__(self, nesting: int = 1, indentation: str = "    ") -> str:
        if self._value is NotImplemented:
            text = "<unread>"
        elif hasattr(self._value, "__pretty_str__"):
            text = self._value.__pretty_str__(nesting, indentation)
        else:
            text = str(self._value)
        return "%s: %s" % (self.__class__.__name__, text)

    def read(self) -> Any:
        self.stream.seek(self.pos)
        return self.subcon._parse(self.stream, self.context)

    def dispose(self) -> None:
        del self.subcon
        del self.stream
        del self.context
        del self.pos

    def _get_value(self) -> Any:
        if self._value is NotImplemented:
            self._value = self.read()
        return self._value

    value = property(_get_value)

    has_value = property(lambda self: self._value is not NotImplemented)
