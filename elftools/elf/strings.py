#-------------------------------------------------------------------------------
# elftools: elf/strings.py
#
# ELF string table
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.utils import parse_cstring_from_stream


class StringTable(object):
    def __init__(self, stream, position, size=None):
        self.__stream = stream  # Avoid attribute conflict with Section class
        self._position = position
        # size not currently used, but could be used for error checking

    def get_string(self, offset):
        """ Get the string stored at the given offset in this string table.
        """
        s = parse_cstring_from_stream(self.__stream, self._position + offset)
        return s
