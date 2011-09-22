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


# AttributeValue - describes an attribute value in the DIE: 
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
        
            size:
                The size this DIE occupies in the section
            
            attributes:
                An ordered dictionary mapping attribute names to values. It's 
                ordered to enable both efficient name->value mapping and
                preserve the order of attributes in the section
            
            has_children:
                Specifies whether this DIE has children
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
        self.tag = None
        self.has_children = None
        self.size = 0
        
        self._parse_DIE()   
    
    def is_null(self):
        """ Is this a null entry?
        """
        return self.tag is None
    
    def _parse_DIE(self):
        """ Parses the DIE info from the section, based on the abbreviation
            table of the CU
        """
        structs = self.cu.structs
        
        # A DIE begins with the abbreviation code. Read it and use it to 
        # obtain the abbrev declaration for this DIE.
        # Note: here and elsewhere, preserve_stream_pos is used on operations
        # that manipulate the stream by reading data from it.
        #
        abbrev_code = struct_parse(
            structs.Dwarf_uleb128(''), self.stream, self.offset)
        
        # This may be a null entry
        if abbrev_code == 0:
            self.size = self.stream.tell() - self.offset
            return
        
        with preserve_stream_pos(self.stream):
            abbrev_decl = self.cu.get_abbrev_table().get_abbrev(abbrev_code)
        self.tag = abbrev_decl['tag']
        self.has_children = abbrev_decl.has_children()
        
        # Guided by the attributes listed in the abbreviation declaration, parse
        # values from the stream.
        #
        for name, form in abbrev_decl.iter_attr_specs():
            print '**', self.stream.tell()
            raw_value = struct_parse(structs.Dwarf_dw_form[form], self.stream)
            value = self._translate_attr_value(form, raw_value)            
            self.attributes[name] = AttributeValue(form, value, raw_value)
        
        self.size = self.stream.tell() - self.offset

    def _translate_attr_value(self, form, raw_value):
        """ Translate a raw attr value according to the form
        """
        value = None
        if form == 'DW_FORM_strp':
            with preserve_stream_pos(self.stream):
                value = self.dwarfinfo.get_string_from_table(raw_value)
        elif form == 'DW_FORM_flag':
            value = not raw_value == 0
        elif form == 'DW_FORM_indirect':
            form = raw_value
            raw_value = struct_parse(
                structs.Dwarf_dw_form[form], self.stream)
            # Let's hope this doesn't get too deep :-)
            return self._translate_attr_value(form, raw_value)
        else:
            value = raw_value
        return value
        
         