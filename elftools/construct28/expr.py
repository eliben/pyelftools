import operator

if not hasattr(operator, "div"):
    operator.div = operator.truediv

opnames = {
    operator.add : "+",
    operator.sub : "-",
    operator.mul : "*",
    operator.div : "/",
    operator.floordiv : "//",
    operator.mod : "%",
    operator.pow : "**",
    operator.xor : "^",
    operator.lshift : "<<",
    operator.rshift : ">>",
    operator.and_ : "and",
    operator.or_ : "or",
    operator.not_ : "not",
    operator.neg : "-",
    operator.pos : "+",
    operator.contains : "in",
    operator.gt : ">",
    operator.ge : ">=",
    operator.lt : "<",
    operator.le : "<=",
    operator.eq : "==",
    operator.ne : "!=",
}


class ExprMixin(object):
    __slots__ = ()
    def __add__(self, other):
        return BinExpr(operator.add, self, other)
    def __sub__(self, other):
        return BinExpr(operator.sub, self, other)
    def __mul__(self, other):
        return BinExpr(operator.mul, self, other)
    def __floordiv__(self, other):
        return BinExpr(operator.floordiv, self, other)
    def __truediv__(self, other):
        return BinExpr(operator.div, self, other)
    __div__ = __floordiv__
    def __mod__(self, other):
        return BinExpr(operator.mod, self, other)
    def __pow__(self, other):
        return BinExpr(operator.pow, self, other)
    def __xor__(self, other):
        return BinExpr(operator.xor, self, other)
    def __rshift__(self, other):
        return BinExpr(operator.rshift, self, other)
    def __lshift__(self, other):
        return BinExpr(operator.rshift, self, other)
    def __and__(self, other):
        return BinExpr(operator.and_, self, other)
    def __or__(self, other):
        return BinExpr(operator.or_, self, other)

    def __radd__(self, other):
        return BinExpr(operator.add, other, self)
    def __rsub__(self, other):
        return BinExpr(operator.sub, other, self)
    def __rmul__(self, other):
        return BinExpr(operator.mul, other, self)
    def __rfloordiv__(self, other):
        return BinExpr(operator.floordiv, other, self)
    def __rtruediv__(self, other):
        return BinExpr(operator.div, other, self)
    __rdiv__ = __rfloordiv__
    def __rmod__(self, other):
        return BinExpr(operator.mod, other, self)
    def __rpow__(self, other):
        return BinExpr(operator.pow, other, self)
    def __rxor__(self, other):
        return BinExpr(operator.xor, other, self)
    def __rrshift__(self, other):
        return BinExpr(operator.rshift, other, self)
    def __rlshift__(self, other):
        return BinExpr(operator.rshift, other, self)
    def __rand__(self, other):
        return BinExpr(operator.and_, other, self)
    def __ror__(self, other):
        return BinExpr(operator.or_, other, self)

    def __neg__(self):
        return UniExpr(operator.neg, self)
    def __pos__(self):
        return UniExpr(operator.pos, self)
    def __invert__(self):
        return UniExpr(operator.not_, self)
    __inv__ = __invert__

    def __contains__(self, other):
        return BinExpr(operator.contains, self, other)
    def __gt__(self, other):
        return BinExpr(operator.gt, self, other)
    def __ge__(self, other):
        return BinExpr(operator.ge, self, other)
    def __lt__(self, other):
        return BinExpr(operator.lt, self, other)
    def __le__(self, other):
        return BinExpr(operator.le, self, other)
    def __eq__(self, other):
        return BinExpr(operator.eq, self, other)
    def __ne__(self, other):
        return BinExpr(operator.ne, self, other)

class UniExpr(ExprMixin):
    __slots__ = ["op", "operand"]
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand
    def __repr__(self):
        return "%s %r" % (opnames[self.op], self.operand)
    def __call__(self, objorcontext, *args):
        operand = self.operand(objorcontext) if callable(self.operand) else self.operand
        return self.op(operand)

class BinExpr(ExprMixin):
    __slots__ = ["op", "lhs", "rhs"]
    def __init__(self, op, lhs, rhs):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs
    def __repr__(self):
        return "(%r %s %r)" % (self.lhs, opnames[self.op], self.rhs)
    def __call__(self, objorcontext, *args):
        lhs = self.lhs(objorcontext) if callable(self.lhs) else self.lhs
        rhs = self.rhs(objorcontext) if callable(self.rhs) else self.rhs
        return self.op(lhs, rhs)

class Path(ExprMixin):
    __slots__ = ["__name", "__parent"]
    def __init__(self, name, parent=None):
        self.__name = name
        self.__parent = parent
    def __repr__(self):
        if self.__parent is None:
            return self.__name
        return "%r.%s" % (self.__parent, self.__name)
    def __call__(self, context, *args):
        if self.__parent is None:
            return context
        context2 = self.__parent(context)
        return context2[self.__name]
    def __getattr__(self, name):
        return Path(name, self)
    def __getitem__(self, name):
    	return Path(name, self)

this = Path("this")


class FuncExpr(ExprMixin):
    def __init__(self, func, operand):
        self.func = func
        self.operand = operand
    def __repr__(self):
        return "%s_(%r)" % (self.func.__name__, self.operand)
    def __call__(self, context, *args):
        operand = self.operand(context) if callable(self.operand) else self.operand
        return self.func(operand)

class PathFunc(ExprMixin):
    def __init__(self, func):
        self.func = func
    def __repr__(self):
        return "%s_" % (self.func.__name__)
    def __call__(self, operand, *args):
        return FuncExpr(self.func, operand) if callable(operand) else operand

len_ = PathFunc(len)
sum_ = PathFunc(sum)
min_ = PathFunc(min)
max_ = PathFunc(max)
abs_ = PathFunc(abs)


class Path2(ExprMixin):
    def __init__(self, name=None, parent=None):
        self.__name = name
        self.__parent = parent
    def __repr__(self):
        return "obj_"
    def __call__(self, obj, *args):
        if self.__parent is None:
            return obj
        obj2 = self.__parent(obj)
        return obj2[self.__name]
    def __getattr__(self, name):
        return Path2(name, self)

obj_ = Path2()


class PathConst(ExprMixin):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return "%s_" % (self.value)
    def __call__(self, operand, *args):
        return self.value

True_ = PathConst(True)
False_ = PathConst(False)

