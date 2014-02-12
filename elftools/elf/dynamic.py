#-------------------------------------------------------------------------------
# elftools: elf/dynamic.py
#
# ELF Dynamic Tags
#
# Mike Frysinger (vapier@gentoo.org)
# This code is in the public domain
#-------------------------------------------------------------------------------
import itertools

from .sections import Section
from .segments import Segment
from ..common.utils import struct_parse

from .enums import ENUM_D_TAG


class DynamicTag(object):
    """ Dynamic Tag object - representing a single dynamic tag entry from a
        dynamic section.

        Allows dictionary-like access to the dynamic structure. For special
        tags (those listed in the _HANDLED_TAGS set below), creates additional
        attributes for convenience. For example, .soname will contain the actual
        value of DT_SONAME (fetched from the dynamic symbol table).
    """
    _HANDLED_TAGS = frozenset(
        ['DT_NEEDED', 'DT_RPATH', 'DT_RUNPATH', 'DT_SONAME',
         'DT_SUNW_FILTER'])

    def __init__(self, entry, stringtable):
        self.entry = entry
        if entry.d_tag in self._HANDLED_TAGS:
            setattr(self, entry.d_tag[3:].lower(),
                    stringtable.get_string(self.entry.d_val))

    def __getitem__(self, name):
        """ Implement dict-like access to entries
        """
        return self.entry[name]

    def __repr__(self):
        return '<DynamicTag (%s): %r>' % (self.entry.d_tag, self.entry)

    def __str__(self):
        if self.entry.d_tag in self._HANDLED_TAGS:
            s = '"%s"' % getattr(self, self.entry.d_tag[3:].lower())
        else:
            s = '%#x' % self.entry.d_ptr
        return '<DynamicTag (%s) %s>' % (self.entry.d_tag, s)


class Dynamic(object):
    """ Shared functionality between dynamic sections and segments.
    """
    def __init__(self, stream, elffile, stringtable, position):
        self._stream = stream
        self._elffile = elffile
        self._elfstructs = elffile.structs
        self._num_tags = -1
        self._offset = position
        self._tagsize = self._elfstructs.Elf_Dyn.sizeof()
        self._stringtable = stringtable

    def iter_tags(self, type=None):
        """ Yield all tags (limit to |type| if specified)
        """
        for n in itertools.count():
            tag = self.get_tag(n)
            if type is None or tag.entry.d_tag == type:
                yield tag
            if tag.entry.d_tag == 'DT_NULL':
                break

    def get_tag(self, n):
        """ Get the tag at index #n from the file (DynamicTag object)
        """
        offset = self._offset + n * self._tagsize
        entry = struct_parse(
            self._elfstructs.Elf_Dyn,
            self._stream,
            stream_pos=offset)
        return DynamicTag(entry, self._stringtable)

    def num_tags(self):
        """ Number of dynamic tags in the file
        """
        if self._num_tags != -1:
            return self._num_tags

        for n in itertools.count():
            tag = self.get_tag(n)
            if tag.entry.d_tag == 'DT_NULL':
                self._num_tags = n + 1
                return self._num_tags


class DynamicSection(Section, Dynamic):
    """ ELF dynamic table section.  Knows how to process the list of tags.
    """
    def __init__(self, header, name, stream, elffile):
        Section.__init__(self, header, name, stream)
        stringtable = elffile.get_section(header['sh_link'])
        Dynamic.__init__(self, stream, elffile, stringtable, self['sh_offset'])


class DynamicSegment(Segment, Dynamic):
    """ ELF dynamic table segment.  Knows how to process the list of tags.
    """
    def __init__(self, header, stream, elffile):
        # The string table section to be used to resolve string names in
        # the dynamic tag array is the one pointed at by the sh_link field
        # of the dynamic section header.
        # So we must look for the dynamic section contained in the dynamic
        # segment, we do so by searching for the dynamic section whose content
        # is located at the same offset as the dynamic segment
        for section in elffile.iter_sections():
            if (isinstance(section, DynamicSection) and
                    section['sh_offset'] == header['p_offset']):
                stringtable = elffile.get_section(section['sh_link'])
                break
        Segment.__init__(self, header, stream)
        Dynamic.__init__(self, stream, elffile, stringtable, self['p_offset'])
