"""
Various containers exposed to the user.
"""

from construct.lib.py3compat import *


globalfullprinting = None


def setglobalfullprinting(enabled):
    r"""
    Sets full printing for all Container instances. When enabled, Container str produces full content of bytes and strings, otherwise and by default, it produces truncated output.

    :param enabled: bool to enable or disable full printing, or None to default
    """
    global globalfullprinting
    globalfullprinting = enabled


def getglobalfullprinting():
    """Used internally."""
    return bool(globalfullprinting)


def recursion_lock(retval="<recursion detected>", lock_name="__recursion_lock__"):
    """Used internally."""
    def decorator(func):
        def wrapper(self, *args, **kw):
            if getattr(self, lock_name, False):
                return retval
            setattr(self, lock_name, True)
            try:
                return func(self, *args, **kw)
            finally:
                delattr(self, lock_name)

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


class Container(dict):
    r"""
    Generic ordered dictionary that allows both key and attribute access, and preserve key order by insertion. Also it uses __call__ method to chain add keys, because **kw does not preserve order.

    Struct and Sequence, and few others parsers returns a container, since their members have order so do keys.

    Example::

        Container([ ("name","anonymous"), ("age",21) ])

        Container(name="anonymous")(age=21)

        # Note that this syntax does NOT work before python 3.6 due to unordered keyword arguments:
        Container(name="anonymous", age=21)

        Container(container2)
    """
    __slots__ = ["__keys_order__", "__recursion_lock__"]

    def __init__(self, *args, **kw):
        object.__setattr__(self, "__keys_order__", [])
        if isinstance(args, dict):
            for k, v in args.items():
                self[k] = v
            return
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v
            else:
                for k, v in arg:
                    self[k] = v
        for k, v in kw.items():
            self[k] = v

    def __getstate__(self):
        return self.__keys_order__

    def __setstate__(self, state):
        self.__keys_order__ = state

    def __getattr__(self, name):
        try:
            if name in self.__slots__:
                try:
                    return object.__getattribute__(self, name)
                except AttributeError as e:
                    if name == "__keys_order__":
                        object.__setattr__(self, "__keys_order__", [])
                        return []
                    else:
                        raise e
            else:
                return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setitem__(self, key, val):
        if key in self.__slots__:
            object.__setattr__(self, key, val)
        else:
            if key not in self:
                if not hasattr(self, "__keys_order__"):
                    object.__setattr__(self, "__keys_order__", [key])
                else:
                    self.__keys_order__.append(key)
            dict.__setitem__(self, key, val)

    def __delitem__(self, key):
        """Removes an item from the Container in linear time O(n)."""
        if key in self.__slots__:
            object.__delattr__(self, key)
        else:
            dict.__delitem__(self, key)
            self.__keys_order__.remove(key)

    __delattr__ = __delitem__
    __setattr__ = __setitem__

    def __call__(self, **kw):
        """Chains adding new entries to the same container. See ctor."""
        for k,v in kw.items():
            self.__setitem__(k, v)
        return self

    def clear(self):
        dict.clear(self)
        del self.__keys_order__[:]

    def pop(self, key, *default):
        """Removes and returns the value for a given key, raises KeyError if not found."""
        val = dict.pop(self, key, *default)
        self.__keys_order__.remove(key)
        return val

    def popitem(self):
        """Removes and returns the last key and value from order."""
        k = self.__keys_order__.pop()
        v = dict.pop(self, k)
        return k, v

    def update(self, seqordict, **kw):
        if isinstance(seqordict, dict):
            for k, v in seqordict.items():
                self[k] = v
        else:
            for k, v in seqordict:
                self[k] = v
        dict.update(self, kw)

    def copy(self):
        return Container(self.items())

    __update__ = update
    __copy__ = copy

    def __len__(self):
        return len(self.__keys_order__)

    def keys(self):
        return iter(self.__keys_order__)

    def values(self):
        return (self[k] for k in self.__keys_order__)

    def items(self):
        return ((k, self[k]) for k in self.__keys_order__)

    __iter__ = keys

    def __eq__(self, other):
        if not isinstance(other, dict):
            return False
        if len(self) != len(other):
            return False
        for k,v in self.items():
            if k not in other or v != other[k]:
                return False
        for k,v in other.items():
            if k not in self or v != self[k]:
                return False
        return True

    def _search(self, compiled_pattern, search_all):
        items = []
        for key in self.keys():
            try:
                if type(self[key]) == Container or type(self[key]) == ListContainer:
                    ret = self[key]._search(compiled_pattern, search_all)
                    if ret is not None:
                        if search_all:
                            items.extend(ret)
                        else:
                            return ret
                elif compiled_pattern.match(key):
                    if search_all:
                        items.append(self[key])
                    else:
                        return self[key]
            except:
                pass
        if search_all:
            return items
        else:
            return None

    def search(self, pattern):
        import re
        compiled_pattern = re.compile(pattern)
        return self._search(compiled_pattern, False)

    def search_all(self, pattern):
        import re
        compiled_pattern = re.compile(pattern)
        return self._search(compiled_pattern, True)

    @recursion_lock()
    def __repr__(self):
        parts = ["Container"]
        for k,v in self.items():
            if not isinstance(k,str) or not k.startswith("_"):
                parts.extend(["(",str(k),"=",repr(v),")"])
        if len(parts) == 1:
            parts.append("()")
        return "".join(parts)

    @recursion_lock()
    def __str__(self, indentation="\n    "):
        fullprinting = getglobalfullprinting()
        printingcap = 64
        text = ["Container: "]
        for k,v in self.items():
            if not isinstance(k,str) or not k.startswith("_"):
                text.extend([indentation, str(k), " = "])
                if isinstance(v, stringtypes) and fullprinting:
                    if len(v) <= printingcap:
                        text.append("%s (total %d)" % (v[:printingcap], len(v)))
                    else:
                        text.append("%s... (truncated, total %d)" % (v[:printingcap], len(v)))
                else:
                    text.append(indentation.join(str(v).split("\n")))
        return "".join(text)


class FlagsContainer(Container):
    r"""
    Container made to represent a FlagsEnum, only equality skips order. Provides pretty-printing for flags. Only set flags are displayed.
    """

    @recursion_lock()
    def __str__(self, indentation="\n    "):
        text = ["FlagsContainer: "]
        for k,v in self.items():
            if not k.startswith("_") and v:
                text.extend([indentation, k, " = "])
                lines = str(v).split("\n")
                text.append(indentation.join(lines))
        return "".join(text)


class ListContainer(list):
    r"""
    A generic container for lists. Provides pretty-printing.
    """

    @recursion_lock()
    def __str__(self, indentation="\n    "):
        text = ["ListContainer: "]
        for k in self:
            text.extend([indentation])
            lines = str(k).split("\n")
            text.append(indentation.join(lines))
        return "".join(text)

    def _search(self, compiled_pattern, search_all):
        items = []
        for item in self:
            try:
                ret = item._search(compiled_pattern, search_all)
            except:
                continue
            if ret is not None:
                if search_all:
                    items.extend(ret)
                else:
                    return ret
        if search_all:
            return items
        else:
            return None

    def search(self, pattern):
        import re
        compiled_pattern = re.compile(pattern)
        return self._search(compiled_pattern, False)

    def search_all(self, pattern):
        import re
        compiled_pattern = re.compile(pattern)
        return self._search(compiled_pattern, True)


class LazyContainer(object):
    r"""
    Lazy equivalent to Container. Works the same but parses subcons on first access whenever possible.
    """
    __slots__ = ["keysbackend", "offsetmap", "cached", "stream", "addoffset", "context"]

    def __init__(self, keysbackend, offsetmap, cached, stream, addoffset, context):
        self.keysbackend = keysbackend
        self.offsetmap = offsetmap
        self.cached = cached
        self.stream = stream
        self.addoffset = addoffset
        self.context = context

    def __getitem__(self, key):
        if key not in self.cached:
            at, sc = self.offsetmap[key]
            self.stream.seek(self.addoffset + at)
            self.cached[key] = sc._parse(self.stream, self.context, "lazy container")
            if len(self.cached) == len(self):
                self.offsetmap = None
                self.stream = None
        return self.cached[key]

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __len__(self):
        return len(self.keysbackend)

    def keys(self):
        return iter(self.keysbackend)

    def values(self):
        return (self[name] for name in self.keysbackend)

    def items(self):
        return ((name,self[name]) for name in self.keysbackend)

    __iter__ = keys

    def __eq__(self, other):
        if not isinstance(other, dict):
            return False
        if len(self) != len(other):
            return False
        for k,v in self.items():
            if k not in other or v != other[k]:
                return False
        for k,v in other.items():
            if k not in self.keysbackend or v != self[k]:
                return False
        return True

    def __str__(self):
        return "<LazyContainer: %d possible items, %d cached>" % (len(self),len(self.cached))


class LazyRangeContainer(ListContainer):
    r"""
    Lazy equivalent to ListContainer. Works the same but parses subcons on first access whenever possible.
    """
    __slots__ = ["subcon", "subsize", "count", "stream", "addoffset", "context", "cached", "offsetmap"]

    def __init__(self, subcon, subsize, count, stream, addoffset, context):
        self.subcon = subcon
        self.subsize = subsize
        self.count = count
        self.stream = stream
        self.addoffset = addoffset
        self.context = context
        self.cached = {}

    def __getitem__(self, index):
        if not 0 <= index < len(self):
            raise ValueError("index %d out of range 0-%d" % (index,len(self)-1))
        if index not in self.cached:
            self.stream.seek(self.addoffset + index * self.subsize)
            self.cached[index] = self.subcon._parse(self.stream, self.context, "lazy range container")
            if len(self.cached) == len(self):
                self.stream = None
        return self.cached[index]

    def __len__(self):
        return self.count

    def __iter__(self):
        return (self[i] for i in range(len(self)))

    def __eq__(self, other):
        return len(self)==len(other) and all(a==b for a,b in zip(self,other))

    def __repr__(self):
        return "<%s: %d possible items, %d cached>" % (self.__class__.__name__, len(self), len(self.cached))
        # return "<%s: %s>" % (self.__class__.__name__, ",".join(repr(e) for e in self))


class LazySequenceContainer(LazyRangeContainer):
    r"""
    Lazy equivalent to ListContainer. Works the same but parses subcons on first access whenever possible.
    """
    __slots__ = ["count", "offsetmap", "cached", "stream", "addoffset", "context"]

    def __init__(self, count, offsetmap, cached, stream, addoffset, context):
        self.count = count
        self.offsetmap = offsetmap
        self.cached = cached
        self.stream = stream
        self.addoffset = addoffset
        self.context = context

    def __getitem__(self, index):
        if not 0 <= index < len(self):
            raise ValueError("index %d out of range 0-%d" % (index,len(self)-1))
        if index not in self.cached:
            at,sc = self.offsetmap[index]
            self.stream.seek(self.addoffset + at)
            self.cached[index] = sc._parse(self.stream, self.context, "lazy sequence container")
            if len(self.cached) == len(self):
                self.offsetmap = None
                self.stream = None
        return self.cached[index]

    def __len__(self):
        return self.count


