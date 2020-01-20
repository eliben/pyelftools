#-------------------------------------------------------------------------------
# elftools: dwarf/macro.py
#
# DWARF Macro Info
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.py3compat import bytes2str, BytesIO
from ..common.utils import struct_parse, dwarf_assert
from collections import namedtuple

MacinfoDefinition = namedtuple('Definition', 'type lineno macro')
MacinfoUndefinition = namedtuple('Undef', 'type lineno macro')
MacinfoStartFile = namedtuple('StartFile', 'type lineno filenum')
MacinfoEndFile = namedtuple('EndFile', 'type')
MacinfoVendorExt = namedtuple('VendorExt', 'type constant string')

class UnitMacInfos(object):
    """ A container for a the Macro Information for a single
        compile unit.
    """
    def __init__(self, entry_list):
        self._entries = entry_list

    def get_entries(self):
        """ Return a list of macro information entries for a
            single compile unit
        """
        return self._entries

    def iter_entries(self):
        for e in self.entries:
            return e

class MacInfo(object):
    """ A DWARF .debug_macinfo section

        The .debug_macinfo section provies information on macro definitions,
        undefinitions, and the source file and line upon which they occur.
        See DWARF v2, v3, or v4 section 6.3.

            Macro definitions entries consist of the line number and the
            macro string.  The first space seperates the definiton from the
            macro name and formal parameters.

            Entries before parsing the file are define outside the sorce file.

            File start entries have teh source line of the including file and
            the fileno in the location table for the compile unit.  Each file
            start has a matching file end entry.
    """
    def __init__(self, section, structs):
        """ create a MacInfo context

            section;
                The .debug_macinfo section containing the stream parse and size

            structs:
                dwarf structs inistance that includes the entry struct.
        """
        self.section = section
        self.structs = structs

    def get_UnitMacInfos_at_offset(self, offset):
        """ Return a compile units contrbution to .debug_macinfo
        """
        return UnitMacInfos([e for e in self._parse_entries_at_offset(offset)])

    def iter_MacInfo_units(self):
        """ Return a list of MacInfo entires for each unit in the
            .debug_macinfo section
        """
        offset = 0
        while offset < self.section.size:
            unit = self.get_UnitMacInfos_at_offset(offset)
            offset = self.section.stream.tell()
            yield unit

    #------ PRIVATE ------#

    _type2tuple = dict(
         DW_MACINFO_define = MacinfoDefinition,
         DW_MACINFO_undef = MacinfoUndefinition,
         DW_MACINFO_start_file = MacinfoStartFile,
         DW_MACINFO_end_file = MacinfoEndFile,
         DW_MACINFO_vendor_ext = MacinfoVendorExt )

    def _parse_entries_at_offset(self, offset):
        while offset < self.section.size:
            mac = struct_parse(self.structs.Dwarf_MacInfo_Entry,
                self.section.stream, offset)
            if mac.type == 0:
                return
            offset = self.section.stream.tell()
            dwarf_assert(isinstance(mac.type, type('')),
                "Unknown MacInfo entry type %s offset %s." % (mac.type, offset))
            obj = self._type2tuple[mac.type](**mac)
            # should CString return string not bytes?
            if 'macro' in obj._fields and isinstance(obj.macro, bytes):
                obj = obj._replace(macro = bytes2str(obj.macro))
            if 'string' in obj._fields and isinstance(obj.string, bytes):
                obj = obj._replace(string = bytes2str(obj.string))
            yield obj

        dwarf_assert(True, "Unterminated MacInfo section")
