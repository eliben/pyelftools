#-------------------------------------------------------------------------------
# elftools: dwarf/die.py
#
# DWARF Debugging Information Entry
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple

from ..common.py3compat import OrderedDict
from ..common.utils import struct_parse, preserve_stream_pos


# AttributeValue - describes an attribute value in the DIE: 
#
# name:
#   The name (DW_AT_*) of this attribute
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
# offset:
#   Offset of this attribute's value in the stream (absolute offset, relative
#   the beginning of the whole stream)
#
AttributeValue = namedtuple(
    'AttributeValue', 'name form value raw_value offset')


class DIE(object):
    """ A DWARF debugging information entry. On creation, parses itself from
        the stream. Each DIE is held by a CU.
        
        Accessible attributes:
        
            tag:
                The DIE tag
        
            size:
                The size this DIE occupies in the section
            
            offset:
                The offset of this DIE in the stream
            
            attributes:
                An ordered dictionary mapping attribute names to values. It's 
                ordered to preserve the order of attributes in the section
            
            has_children:
                Specifies whether this DIE has children
            
            abbrev_code:
                The abbreviation code pointing to an abbreviation entry (not
                that this is for informational pusposes only - this object 
                interacts with its abbreviation table transparently).
        
        See also the public methods.
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
        self.abbrev_code = None
        self.size = 0
        self._children = []
        self._parent = None
        
        self._parse_DIE()   
    
    def is_null(self):
        """ Is this a null entry?
        """
        return self.tag is None
    
    def get_parent(self):
        """ The parent DIE of this DIE. None if the DIE has no parent (i.e. a 
            top-level DIE).
        """
        return self._parent
    
    def iter_children(self):
        """ Yield all children of this DIE
        """
        return iter(self._children)
    
    def iter_siblings(self):
        """ Yield all siblings of this DIE
        """
        if self._parent:
            for sibling in self._parent.iter_children():
                if sibling is not self:
                    yield sibling
        else:
            raise StopIteration()

    # The following methods are used while creating the DIE and should not be
    # interesting to consumers
    #
    def add_child(self, die):
        self._children.append(die)
    
    def set_parent(self, die):
        self._parent = die

    #------ PRIVATE ------#
    
    def __repr__(self):
        s = 'DIE %s, size=%s, has_chidren=%s\n' % (
            self.tag, self.size, self.has_children)
        for attrname, attrval in self.attributes.iteritems():
            s += '    |%-18s:  %s\n' % (attrname, attrval)
        return s
    
    def __str__(self):
        return self.__repr__()
    
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
        self.abbrev_code = struct_parse(
            structs.Dwarf_uleb128(''), self.stream, self.offset)
        
        # This may be a null entry
        if self.abbrev_code == 0:
            self.size = self.stream.tell() - self.offset
            return
        
        with preserve_stream_pos(self.stream):
            abbrev_decl = self.cu.get_abbrev_table().get_abbrev(
                self.abbrev_code)
        self.tag = abbrev_decl['tag']
        self.has_children = abbrev_decl.has_children()

        # Guided by the attributes listed in the abbreviation declaration, parse
        # values from the stream.
        #
        for name, form in abbrev_decl.iter_attr_specs():
            attr_offset = self.stream.tell()
            raw_value = struct_parse(structs.Dwarf_dw_form[form], self.stream)

            value = self._translate_attr_value(form, raw_value)            
            self.attributes[name] = AttributeValue(
                name=name,
                form=form,
                value=value,
                raw_value=raw_value,
                offset=attr_offset)
        
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
    

