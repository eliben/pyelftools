#-------------------------------------------------------------------------------
# elftools: common/utils.py
#
# Miscellaneous utilities for elftools
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from .exceptions import ELFParseError, ELFError, DWARFError
from ..construct import ConstructError


def struct_parse(struct, stream, stream_pos=None):
    """ Convenience function for using the given struct to parse a stream.
        If stream_pos is provided, the stream is seeked to this position before
        the parsing is done. Otherwise, the current position of the stream is
        used.
        Wraps the error thrown by construct with ELFParseError.
    """
    try:
        if stream_pos is not None:
            stream.seek(stream_pos)
        return struct.parse_stream(stream)
    except ConstructError as e:
        raise ELFParseError(e.message)
    

def elf_assert(cond, msg=''):
    """ Assert that cond is True, otherwise raise ELFError(msg)
    """
    _assert_with_exception(cond, msg, ELFError)


def dwarf_assert(cond, msg=''):
    """ Assert that cond is True, otherwise raise DWARFError(msg)
    """
    _assert_with_exception(cond, msg, DWARFError)


def _assert_with_exception(cond, msg, exception_type):
    if not cond:
        raise exception_type(msg)


from contextlib import contextmanager

@contextmanager
def preserve_stream_pos(stream):
    """ Usage:
            
            # stream has some position FOO (return value of stream.tell())
            with preserve_stream_pos(stream):
                # do stuff that manipulates the stream
            # stream still has position FOO
    """
    saved_pos = stream.tell()
    yield
    stream.seek(saved_pos)
