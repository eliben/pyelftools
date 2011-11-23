#-------------------------------------------------------------------------------
# elftools: elf/relocation.py
#
# ELF relocations
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from collections import namedtuple

from ..common.exceptions import ELFRelocationError


class Relocation(object):
    """ Relocation object - representing a single relocation entry. Allows
        dictionary-like access to the entry's fields.

        Can be either a REL or RELA relocation.
    """
    def __init__(self, entry, elffile):
        self.entry = entry
        self.elffile = elffile
        
    def is_RELA(self):
        """ Is this a RELA relocation? If not, it's REL.
        """
        return 'r_addend' in self.entry
        
    def __getitem__(self, name):
        """ Dict-like access to entries
        """
        return self.entry[name]

    def __repr__(self):
        return '<Relocation (%s): %s>' % (
                'RELA' if self.is_RELA() else 'REL',
                self.entry)

    def __str__(self):
        return self.__repr__()


class RelocationSection(Section):
    def __init__(self, header, name, stream, elffile):
        super(RelocationSection, self).__init__(header, name, stream)
        self.elffile = elffile
        self.elfstructs = self.elffile.structs
        if self.header['sh_type'] == 'SHT_REL':
            expected_size = self.elfstructs.Elf_Rel.sizeof()
            self.entry_struct = self.elfstructs.Elf_Rel
        elif self.header['sh_type'] == 'SHT_RELA':
            expected_size = self.elfstructs.Elf_Rela.sizeof()
            self.entry_struct = self.elfstructs.Elf_Rela
        else:
            elf_assert(False, 'Unknown relocation type section')

        elf_assert(
            self.header['sh_entsize'] == expected_size,
            'Expected sh_entsize of SHT_REL section to be %s' % expected_size)

    def is_RELA(self):
        """ Is this a RELA relocation section? If not, it's REL.
        """
        return self.header['sh_type'] == 'SHT_RELA'

    def num_relocations(self):
        """ Number of relocations in the section
        """
        return self['sh_size'] // self['sh_entsize']

    def get_relocation(self, n):
        """ Get the relocation at index #n from the section (Relocation object)
        """
        entry_offset = self['sh_offset'] + n * self['sh_entsize']
        entry = struct_parse(
            self.entry_struct,
            self.stream,
            stream_pos=entry_offset)
        return Relocation(entry, self.elffile)

    def iter_relocations(self):
        """ Yield all the relocations in the section
        """
        for i in range(self.num_relocations()):
            yield self.get_relocation(i)


class RelocationHandler(object):
    """ Handles the logic of relocations in ELF files.
    """
    def __init__(self, elffile):
        self.elffile = elffile

    def find_relocations_for_section(self, section):
        """ Given a section, find the relocation section for it in the ELF
            file. Return a RelocationSection object, or None if none was
            found.
        """
        reloc_section_names = (
                '.rel' + section.name,
                '.rela' + section.name)
        # Find the relocation section aimed at this one. Currently assume
        # that either .rel or .rela section exists for this section, but
        # not both.
        for relsection in self.iter_sections():
            if (    isinstance(relsection, RelocationSection) and
                    relsection.name in reloc_section_names):
                return relsection
        return None
        
    def apply_section_relocations(self, stream, reloc_section):
        """ Apply all relocations in reloc_section (a RelocationSection object)
            to the given stream, that contains the data of the section that is
            being relocated. The stream is modified as a result.
        """
        # The symbol table associated with this relocation section
        symtab = self.elffile.get_section(reloc_section['sh_link'])
        for reloc in reloc_section.iter_relocations():
            self._do_apply_relocation(stream, reloc, symtab)

    def _do_apply_relocation(self, stream, reloc, symtab):
        # ZZZ: steps
        # 1. Read the value from the stream (with correct size and endianness)
        # 2. Apply the relocation to the value
        # 3. Write the relocated value back into the stream
        #
        # To make it generic, have a map of "relocation recipes" per
        # relocation.
        #


        # Some basic sanity checking
        if self.architecture_is_x86() and reloc.is_RELA():
            raise ELFRelocationError(
                'Unexpected RELA relocation for x86: %s' % reloc)
        elif self.architecture_is_x64() and not reloc.is_RELA():
            raise ELFRelocationError(
                'Unexpected REL relocation for x64: %s' % reloc)

        if reloc['r_info_sym'] >= symtab.num_symbols():
            raise ELFRelocationError(
                'Invalid symbol reference in relocation: index %s' % (
                    reloc['r_info_sym']))

        sym_value = symtab.get_symbol(reloc['r_info_sym'])['st_value']
        reloc_type = reloc['r_info_type']

        if self.architecture_is_x86():
            if reloc_type == ENUM_RELOC_TYPE_i386['R_386_NONE']:
                # No relocation
                return value
            elif reloc_type == ENUM_RELOC_TYPE_i386['R_386_32']:
                return sym_value + value
            elif reloc_type == ENUM_RELOC_TYPE_i386['R_386_PC32']:
                return sym_value + value - offset
            else:
                raise ELFRelocationError('Unsupported relocation type %s' % (
                    reloc_type))
        elif self.architecture_is_x64():
            if reloc_type == ENUM_RELOC_TYPE_x64['R_X86_64_NONE']:
                # No relocation
                return value
            elif reloc_type in (
                    ENUM_RELOC_TYPE_x64['R_X86_64_64'],
                    ENUM_RELOC_TYPE_x64['R_X86_64_32'],
                    ENUM_RELOC_TYPE_x64['R_X86_64_32S']):
                return sym_value + reloc['r_addend']
            else:
                raise ELFRelocationError('Unsupported relocation type %s' % (
                    reloc_type))
        else:
            raise ELFRelocationError(
                'Relocations not supported for architecture %s' % (
                    self['e_machine']))

        raise ELFRelocationError('unreachable relocation code')

    # Relocations are represented by "recipes". Each recipe specifies
    _RELOCATION_RECIPE_TYPE = namedtuple('_RELOCATION_RECIPE_TYPE',
        'bytesize has_addend calc_func')

    def _reloc_calc_identity(value, offset, addend=0):
        return value
        
    _RELOCATION_RECIPES = {
        'R_386_NONE':
    }

