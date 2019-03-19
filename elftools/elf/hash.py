#-------------------------------------------------------------------------------
# elftools: elf/hash.py
#
# ELF hash table sections
#
# Andreas Ziegler (andreas.ziegler@fau.de)
# This code is in the public domain
#-------------------------------------------------------------------------------

from ..common.utils import struct_parse


class HashSection(object):
    """ Minimal part of an ELF hash section to find the number of symbols in the
        symbol table - useful for super-stripped binaries without section
        headers where only the start of the symbol table is known from the
        dynamic segment. The layout and contents are nicely described at
        https://flapenguin.me/2017/04/24/elf-lookup-dt-hash/.
    """
    def __init__(self, stream, offset, elffile):
        self._stream = stream
        self._offset = offset
        self._elffile = elffile
        self.params = struct_parse(self._elffile.structs.Elf_Hash,
                                   self._stream,
                                   self._offset)

    def get_number_of_symbols(self):
        """ Get the number of symbols from the hash table parameters.
        """
        return self.params['nchains']


class GNUHashSection(object):
    """ Minimal part of a GNU hash section to find the number of symbols in the
        symbol table - useful for super-stripped binaries without section
        headers where only the start of the symbol table is known from the
        dynamic segment. The layout and contents are nicely described at
        https://flapenguin.me/2017/05/10/elf-lookup-dt-gnu-hash/.
    """
    def __init__(self, stream, offset, elffile):
        self._stream = stream
        self._offset = offset
        self._elffile = elffile
        self.params = struct_parse(self._elffile.structs.Gnu_Hash,
                                   self._stream,
                                   self._offset)

    def get_number_of_symbols(self):
        """ Get the number of symbols in the hash table by finding the bucket
            with the highest symbol index and walking to the end of its chain.
        """
        # Element sizes in the hash table
        wordsize = self._elffile.structs.Elf_word('').sizeof()
        xwordsize = self._elffile.structs.Elf_xword('').sizeof()

        # Find highest index in buckets array
        max_idx = max(self.params['buckets'])
        if max_idx < self.params['symoffset']:
            return self.params['symoffset']

        # Position the stream at the start of the corresponding chain
        chain_pos = self._offset + 4 * wordsize + \
            self.params['bloom_size'] * xwordsize + \
            self.params['nbuckets'] * wordsize + \
            (max_idx - self.params['symoffset']) * wordsize

        # Walk the chain to its end (lowest bit is set)
        while True:
            cur_hash = struct_parse(self._elffile.structs.Elf_word('elem'),
                                    self._stream,
                                    chain_pos)
            if cur_hash & 1:
                return max_idx + 1

            max_idx += 1
            chain_pos += wordsize
