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
from ..common.utils import struct_parse, preserve_stream_pos


# Describes an attribute value in the DIE: 
#
# form: 
#   The DW_FORM_* name of this attribute
#
# value:
#   The value parsed from the section and translated accordingly to the form
#   (e.g. for a DW_FORM_strp it's the actual string taken from the string table)
#
# raw_value:
#   Raw value as parsed from the section - used for debugging and presentation
#   (e.g. for a DW_FORM_strp it's the raw string offset into the table)
#
AttributeValue = namedtuple('AttributeValue', 'form value raw_value')


class DIE(object):
    """ A DWARF debugging information entry. On creation, parses itself from
        the stream. Each DIE is held by a CU.
        
        Accessible attributes:
        
            tag:
                The DIE tag
        
            length:
                The size this DIE occupies in the section
            
            attributes:
                An ordered dictionary mapping attribute names to values. It's 
                ordered to enable both efficient name->value mapping and
                preserve the order of attributes in the section
    """
    def __init__(self, cu, stream, offset):
        """ cu:
                CompileUnit object this DIE belongs to. Used to obtain context
                information (structs, abbrev table, etc.)
                        
            stream, offset:
                The stream and offset into it where this DIE's data is located
        """
        self.cu = cu
        self.dwarfinfo = self.cu.dwarfinfo # get DWARFInfo context
        self.stream = stream
        self.offset = offset
        self.attributes = OrderedDict()
        self._parse_DIE()
    
    def _parse_DIE(self):
        """ Parses the DIE info from the section, based on the abbreviation
            table of the CU
        """
        print self.offset, self.cu.structs.dwarf_format
        structs = self.cu.structs
        
        # A DIE begins with the abbreviation code. Read it and use it to 
        # obtain the abbrev declaration for this DIE.
        # Note: here and elsewhere, preserve_stream_pos is used on operations
        # that manipulate the stream by reading data from it.
        #
        abbrev_code = struct_parse(
            structs.Dwarf_uleb128(''), self.stream, self.offset)
        with preserve_stream_pos(self.stream):
            abbrev = self.cu.get_abbrev_table().get_abbrev(abbrev_code)
        
        print '**', abbrev_code, abbrev, abbrev.decl
        
        # Guided by the attributes listed in the abbreviation declaration, parse
        # values from the stream.
        #
        for name, form in abbrev.iter_attr_specs():
            print '** parsing at stream + ', self.stream.tell()
            raw_value = struct_parse(structs.Dwarf_dw_form[form], self.stream)
            print '**', name, form, raw_value
            #~ print structs.Dwarf_dw_form[form]


