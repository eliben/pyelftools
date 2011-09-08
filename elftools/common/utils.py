#-------------------------------------------------------------------------------
# elftools: common/utils.py
#
# Miscellaneous utilities for elftools
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from .exceptions import ELFParseError, ELFError


def struct_parse(struct, stream, stream_pos=None):
    """ Convenience function for using the given struct to parse a stream (at
        its current location).
        If stream_pos is provided, the stream is seeked to this position before
        the parsing is done.
        Wraps the error thrown by construct with our own error.
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
    if not cond:
        raise ELFError(msg)

