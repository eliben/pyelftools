#-------------------------------------------------------------------------------
# elftools: common/py3compat.py
#
# Python 3 compatibility code
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys
PY3 = sys.version_info[0] == 3


if PY3:
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO

    import collections
    OrderedDict = collections.OrderedDict

    _iterkeys = "keys"
    _iteritems = "items"
else:
    import cStringIO
    StringIO = BytesIO = cStringIO.StringIO

    from .ordereddict import OrderedDict

    _iterkeys = "iterkeys"
    _iteritems = "iteritems"


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return getattr(d, _iterkeys)()

def iteritems(d):
    """Return an iterator over the items of a dictionary."""
    return getattr(d, _iteritems)()

