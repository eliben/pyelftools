#-------------------------------------------------------------------------------
# elftools: dwarf/die.py
#
# DWARF Debugging Information Entry
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple

from ..common.ordereddict import OrderedDict
from ..common.utils import struct_parse


# Describes an attribute value in the DIE: form and actual value
#
AttributeValue = namedtuple('AttributeValue', 'form value')


class DIE(object):
    """ A DWARF debugging information entry. On creation, parses itself from
        the stream. Each DIE is held by a CU.
        
        Accessible attributes:
        
            tag:
                The DIE tag
        
            length:
                The size this DIE occupies in the section
            
            attributes:
                An ordered dictionary mapping attribute names to values
    """
    def __init__(self, cu, stream, offset):
        """ cu:
                CompileUnit object this DIE belongs to. Used to obtain context
                information (structs, abbrev table, etc.)
            
            stream, offset:
                The stream and offset into it where this DIE's data is located
        """
        self.cu = cu
        self.stream = stream
        self.offset = offset
        self._parse_DIE()
    
    def _parse_DIE(self):
        """ Parses the DIE info from the section, based on the abbreviation
            table of the CU
        """
        saved_offset = self.offset
        structs = self.cu.structs
        
        # The DIE begins with the abbreviation code. Read it and use it to 
        # obtain the abbrev declaration for this DIE
        #
        abbrev_code = struct_parse(structs.Dwarf_uleb128(''), self.stream)
        abbrev = self.cu.get_abbrev_table().get_abbrev(abbrev_code)
        
        print abbrev_code, abbrev, abbrev.decl


