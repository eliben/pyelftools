#-------------------------------------------------------------------------------
# elftools: common/construct_utils.py
#
# Some complementary construct utilities
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..construct28 import Subconstruct, ConstructError, RangeError
from ..construct28.lib import ListContainer

class RepeatUntilExcluding(Subconstruct):
    """ A version of construct's RepeatUntil that doesn't include the last
        element (which casued the repeat to exit) in the return value.

        Only parsing is currently implemented.

        P.S. removed some code duplication
    """
    __slots__ = ["predicate"]
    def __init__(self, predicate, subcon):
        super(RepeatUntilExcluding, self).__init__(subcon)
        self.predicate = predicate
    def _parse(self, stream, context, path):
        obj = ListContainer()
        try:
            while True:
                subobj = self.subcon._parse(stream, context, path)
                if self.predicate(subobj, context):
                    break
                obj.append(subobj)
        except ConstructError as ex:
            raise RangeError("missing terminator", ex)
        return obj
    def _build(self, obj, stream, context):
        raise NotImplementedError('no building')
    def _sizeof(self, context):
        raise SizeofError("can't calculate size")
