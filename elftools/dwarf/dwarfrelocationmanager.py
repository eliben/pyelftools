#-------------------------------------------------------------------------------
# elftools: dwarf/dwarfrelocationmanager.py
#
# DWARFRelocationManager - handles relocations of DWARF data
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..elf.sections import RelocationSection


class DWARFRelocationManager(object):
    """ Manages relocations for some DWARF section
    """
    def __init__(self, elffile, section_name):
        """ 
        """
        self.elffile = elffile
        self.section_name = section_name
        self._section = self.elffile.get_section_by_name(section_name)

        # _relocs maps an offset in the section to an index in the relocation
        # table.
        # _reloc_section is the relocation section object
        # ... both are loaded by _load_relocations
        self._relocs = {}
        self._reloc_section = None
        self._load_relocations()

    def has_relocation(self, offset):
        """ Does the given offset have a relocation registered for it?
            The offset is relative to its section.
        """
        return offset in self._relocs
        
    def apply_relocation(self, offset, value):
        """ Apply the relocation registered for the given offset. value is
            the original value at that offset. Return the relocated value.
        """
        reloc_index = self._relocs[offset]
        return self.elffile.apply_relocation(
                    reloc_section=self._reloc_section,
                    reloc_index=reloc_index,
                    offset=offset,
                    value=value)

    def _load_relocations(self):
        # Currently assume that only a single relocation section will exist
        # for our section, and that it's either a .rel or a .rela
        reloc_section_names = (
                '.rel' + self.section_name,
                '.rela' + self.section_name)
        for section in self.elffile.iter_sections():
            if (    isinstance(section, RelocationSection) and
                    section.name in reloc_section_names):
                self._reloc_section = section
                for i, reloc in enumerate(
                        self._reloc_section.iter_relocations()):
                    self._relocs[reloc['r_offset']] = i
                break

