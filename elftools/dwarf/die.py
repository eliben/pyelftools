#-------------------------------------------------------------------------------
# elftools: dwarf/die.py
#
# DWARF Debugging Information Entry
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple, OrderedDict
import os

from ..common.exceptions import DWARFError
from ..common.py3compat import bytes2str, iteritems
from ..common.utils import struct_parse, preserve_stream_pos
from .enums import DW_FORM_raw2name


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
                The abbreviation code pointing to an abbreviation entry (note
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
        # Null DIE terminator. It can be used to obtain offset range occupied
        # by this DIE including its whole subtree.
        self._terminator = None
        self._parent = None

        self._parse_DIE()

    def is_null(self):
        """ Is this a null entry?
        """
        return self.tag is None

    def get_DIE_from_attribute(self, name):
        """ Return the DIE referenced by the named attribute of this DIE.
            The attribute must be in the reference attribute class.

            name:
                The name of the attribute in the reference class.
        """
        attr = self.attributes[name]
        if attr.form in ('DW_FORM_ref1', 'DW_FORM_ref2', 'DW_FORM_ref4',
                         'DW_FORM_ref8', 'DW_FORM_ref'):
            refaddr = self.cu.cu_offset + attr.raw_value
            return self.cu.get_DIE_from_refaddr(refaddr)
        elif attr.form in ('DW_FORM_ref_addr'):
            return self.cu.dwarfinfo.get_DIE_from_refaddr(attr.raw_value)
        elif attr.form in ('DW_FORM_ref_sig8'):
            # Implement search type units for matching signature
            raise NotImplementedError('%s (type unit by signature)' % attr.form)
        elif attr.form in ('DW_FORM_ref_sup4', 'DW_FORM_ref_sup8'):
            raise NotImplementedError('%s to dwo' % attr.form)
        else:
            raise DWARFError('%s is not a reference class form attribute' % attr)

    def get_parent(self):
        """ Return the parent DIE of this DIE, or None if the DIE has no
            parent (i.e. is a top-level DIE).
        """
        if self._parent is None:
            self._search_ancestor_offspring()
        return self._parent

    def get_full_path(self):
        """ Return the full path filename for the DIE.

            The filename is the join of 'DW_AT_comp_dir' and 'DW_AT_name',
            either of which may be missing in practice. Note that its value is
            usually a string taken from the .debug_string section and the
            returned value will be a string.
        """
        comp_dir_attr = self.attributes.get('DW_AT_comp_dir', None)
        comp_dir = bytes2str(comp_dir_attr.value) if comp_dir_attr else ''
        fname_attr = self.attributes.get('DW_AT_name', None)
        fname = bytes2str(fname_attr.value) if fname_attr else ''
        return os.path.join(comp_dir, fname)

    def iter_children(self):
        """ Iterates all children of this DIE
        """
        return self.cu.iter_DIE_children(self)

    def iter_siblings(self):
        """ Yield all siblings of this DIE
        """
        parent = self.get_parent()
        if parent:
            for sibling in parent.iter_children():
                if sibling is not self:
                    yield sibling
        else:
            raise StopIteration()

    # The following methods are used while creating the DIE and should not be
    # interesting to consumers
    #

    def set_parent(self, die):
        self._parent = die

    #------ PRIVATE ------#

    def _search_ancestor_offspring(self):
        """ Search our ancestors identifying their offspring to find our parent.

            DIEs are stored as a flattened tree.  The top DIE is the ancestor
            of all DIEs in the unit.  Each parent is guaranteed to be at
            an offset less than their children.  In each generation of children
            the sibling with the closest offset not greater than our offset is
            our ancestor.
        """
        # This code is called when get_parent notices that the _parent has
        # not been identified.  To avoid execution for each sibling record all
        # the children of any parent iterated.  Assuming get_parent will also be
        # called for siblings, it is more efficient if siblings references are
        # provided and no worse than a single walk if they are missing, while
        # stopping iteration early could result in O(n^2) walks.
        search = self.cu.get_top_DIE()
        while search.offset < self.offset:
            prev = search
            for child in search.iter_children():
                child.set_parent(search)
                if child.offset <= self.offset:
                    prev = child

            # We also need to check the offset of the terminator DIE
            if search.has_children and search._terminator.offset <= self.offset:
                    prev = search._terminator

            # If we didn't find a closer parent, give up, don't loop.
            # Either we mis-parsed an ancestor or someone created a DIE
            # by an offset that was not actually the start of a DIE.
            if prev is search:
                raise ValueError("offset %s not in CU %s DIE tree" %
                    (self.offset, self.cu.cu_offset))

            search = prev

    def __repr__(self):
        s = 'DIE %s, size=%s, has_children=%s\n' % (
            self.tag, self.size, self.has_children)
        for attrname, attrval in iteritems(self.attributes):
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
        self.abbrev_code = struct_parse(
            structs.Dwarf_uleb128(''), self.stream, self.offset)

        # This may be a null entry
        if self.abbrev_code == 0:
            self.size = self.stream.tell() - self.offset
            return

        abbrev_decl = self.cu.get_abbrev_table().get_abbrev(self.abbrev_code)
        self.tag = abbrev_decl['tag']
        self.has_children = abbrev_decl.has_children()

        # Guided by the attributes listed in the abbreviation declaration, parse
        # values from the stream.
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
        elif form == 'DW_FORM_flag_present':
            value = True
        elif form == 'DW_FORM_indirect':
            try:
                form = DW_FORM_raw2name[raw_value]
            except KeyError as err:
                raise DWARFError(
                        'Found DW_FORM_indirect with unknown raw_value=' +
                        str(raw_value))

            raw_value = struct_parse(
                self.cu.structs.Dwarf_dw_form[form], self.stream)
            # Let's hope this doesn't get too deep :-)
            return self._translate_attr_value(form, raw_value)
        else:
            value = raw_value
        return value
