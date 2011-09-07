def recursion_lock(retval, lock_name = "__recursion_lock__"):
    def decorator(func):
        def wrapper(self, *args, **kw):
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

class Container(object):
    """
    A generic container of attributes
    """
    __slots__ = ["__dict__", "__attrs__"]
    def __init__(self, **kw):
        self.__dict__.update(kw)
        object.__setattr__(self, "__attrs__", kw.keys())
    
    def __eq__(self, other):
        try:
            return self.__dict__ == other.__dict__
        except AttributeError:
            return False
    def __ne__(self, other):
        return not (self == other)
    
    def __delattr__(self, name):
        object.__delattr__(self, name)
        self.__attrs__.remove(name)
    def __setattr__(self, name, value):
        d = self.__dict__
        if name not in d:
            self.__attrs__.append(name)
        d[name] = value
    def __getitem__(self, name):
        return self.__dict__[name]
    def __delitem__(self, name):
        self.__delattr__(name)
    def __setitem__(self, name, value):
        self.__setattr__(name, value)
    def __update__(self, obj):
        for name in obj.__attrs__:
            self[name] = obj[name]
    def __copy__(self):
        new = self.__class__()
        new.__attrs__ = self.__attrs__[:]
        new.__dict__ = self.__dict__.copy()
        return new
    
    @recursion_lock("<...>")
    def __repr__(self):
        attrs = sorted("%s = %r" % (k, v) 
            for k, v in self.__dict__.iteritems() 
            if not k.startswith("_"))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(attrs))
    def __str__(self):
        return self.__pretty_str__()
    @recursion_lock("<...>")
    def __pretty_str__(self, nesting = 1, indentation = "    "):
        attrs = []
        ind = indentation * nesting
        for k in self.__attrs__:
            v = self.__dict__[k]
            if not k.startswith("_"):
                text = [ind, k, " = "]
                if hasattr(v, "__pretty_str__"):
                    text.append(v.__pretty_str__(nesting + 1, indentation))
                else:
                    text.append(repr(v))
                attrs.append("".join(text))
        if not attrs:
            return "%s()" % (self.__class__.__name__,)
        attrs.insert(0, self.__class__.__name__ + ":")
        return "\n".join(attrs)

class FlagsContainer(Container):
    """
    A container providing pretty-printing for flags. Only set flags are 
    displayed. 
    """
    def __pretty_str__(self, nesting = 1, indentation = "    "):
        attrs = []
        ind = indentation * nesting
        for k in self.__attrs__:
            v = self.__dict__[k]
            if not k.startswith("_") and v:
                attrs.append(ind + k)
        if not attrs:
            return "%s()" % (self.__class__.__name__,)
        attrs.insert(0, self.__class__.__name__+ ":")
        return "\n".join(attrs)

class ListContainer(list):
    """
    A container for lists
    """
    __slots__ = ["__recursion_lock__"]
    def __str__(self):
        return self.__pretty_str__()
    @recursion_lock("[...]")
    def __pretty_str__(self, nesting = 1, indentation = "    "):
        if not self:
            return "[]"
        ind = indentation * nesting
        lines = ["["]
        for elem in self:
            lines.append("\n")
            lines.append(ind)
            if hasattr(elem, "__pretty_str__"):
                lines.append(elem.__pretty_str__(nesting + 1, indentation))
            else:
                lines.append(repr(elem))
        lines.append("\n")
        lines.append(indentation * (nesting - 1))
        lines.append("]")
        return "".join(lines)

class AttrDict(object):
    """
    A dictionary that can be accessed both using indexing and attributes,
    i.e., 
        x = AttrDict()
        x.foo = 5
        print x["foo"]
    """
    __slots__ = ["__dict__"]
    def __init__(self, **kw):
        self.__dict__ = kw
    def __contains__(self, key):
        return key in self.__dict__
    def __nonzero__(self):
        return bool(self.__dict__)
    def __repr__(self):
        return repr(self.__dict__)
    def __str__(self):
        return self.__pretty_str__()
    def __pretty_str__(self, nesting = 1, indentation = "    "):
        if not self:
            return "{}"
        text = ["{\n"]
        ind = nesting * indentation
        for k in sorted(self.__dict__.keys()):
            v = self.__dict__[k]
            text.append(ind)
            text.append(repr(k))
            text.append(" : ")
            if hasattr(v, "__pretty_str__"):
                try:
                    text.append(v.__pretty_str__(nesting+1, indentation))
                except Exception:
                    text.append(repr(v))
            else:
                text.append(repr(v))
            text.append("\n")
        text.append((nesting-1) * indentation)
        text.append("}")
        return "".join(text)
    def __delitem__(self, key):
        del self.__dict__[key]
    def __getitem__(self, key):
        return self.__dict__[key]
    def __setitem__(self, key, value):
        self.__dict__[key] = value
    def __copy__(self):
        new = self.__class__()
        new.__dict__ = self.__dict__.copy()
        return new
    def __update__(self, other):
        if isinstance(other, dict):
            self.__dict__.update(other)
        else:
            self.__dict__.update(other.__dict__)

class LazyContainer(object):
    __slots__ = ["subcon", "stream", "pos", "context", "_value"]
    def __init__(self, subcon, stream, pos, context):
        self.subcon = subcon
        self.stream = stream
        self.pos = pos
        self.context = context
        self._value = NotImplemented
    def __eq__(self, other):
        try:
            return self._value == other._value
        except AttributeError:
            return False
    def __ne__(self, other):
        return not (self == other)
    def __str__(self):
        return self.__pretty_str__()
    def __pretty_str__(self, nesting = 1, indentation = "    "):
        if self._value is NotImplemented:
            text = "<unread>"
        elif hasattr(self._value, "__pretty_str__"):
            text = self._value.__pretty_str__(nesting, indentation)
        else:
            text = repr(self._value)
        return "%s: %s" % (self.__class__.__name__, text)
    def read(self):
        self.stream.seek(self.pos)
        return self.subcon._parse(self.stream, self.context)
    def dispose(self):
        self.subcon = None
        self.stream = None
        self.context = None
        self.pos = None
    def _get_value(self):
        if self._value is NotImplemented:
            self._value = self.read()
        return self._value
    value = property(_get_value)
    has_value = property(lambda self: self._value is not NotImplemented)









































