#!/usr/bin/env python
#-------------------------------------------------------------------------------
# readelf.py
#
# A clone of 'readelf' in Python, based on the pyelftools library
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys
from optparse import OptionParser

# If elftools is not installed, maybe we're running from the root or scripts
# dir of the source distribution
#
try:
    import elftools
except ImportError:
    sys.path.extend(['.', '..'])

from elftools.common.exceptions import ELFError
from elftools.elf.elffile import ELFFile
from elftools.elf.segments import InterpSegment
from elftools.elf.sections import SymbolTableSection
from elftools.elf.descriptions import (
    describe_ei_class, describe_ei_data, describe_ei_version,
    describe_ei_osabi, describe_e_type, describe_e_machine,
    describe_e_version_numeric, describe_p_type, describe_p_flags,
    describe_sh_type, describe_sh_flags,
    describe_symbol_type, describe_symbol_bind, describe_symbol_visibility,
    describe_symbol_shndx,
    )


class ReadElf(object):
    """ display_* methods are used to emit output into the output stream
    """
    def __init__(self, file, output):
        """ file: 
                stream object with the ELF file to read
            
            output:
                output stream to write to
        """
        self.elffile = ELFFile(file)
        self.output = output

    def display_file_header(self):
        """ Display the ELF file header
        """
        self._emitline('ELF Header:')
        self._emit('  Magic:   ')
        self._emitline(' '.join('%2.2x' % ord(b) 
                                    for b in self.elffile.e_ident_raw))
        header = self.elffile.header
        e_ident = header['e_ident']
        self._emitline('  Class:                             %s' % 
                describe_ei_class(e_ident['EI_CLASS']))
        self._emitline('  Data:                              %s' % 
                describe_ei_data(e_ident['EI_DATA']))
        self._emitline('  Version:                           %s' % 
                describe_ei_version(e_ident['EI_VERSION']))
        self._emitline('  OS/ABI:                            %s' %
                describe_ei_osabi(e_ident['EI_OSABI']))
        self._emitline('  ABI Version:                       %d' % 
                e_ident['EI_ABIVERSION'])
        self._emitline('  Type:                              %s' %
                describe_e_type(header['e_type']))
        self._emitline('  Machine:                           %s' % 
                describe_e_machine(header['e_machine']))
        self._emitline('  Version:                           %s' %
                describe_e_version_numeric(header['e_version']))
        self._emitline('  Entry point address:               %s' % 
                self._format_hex(header['e_entry']))
        self._emit('  Start of program headers           %s' % 
                header['e_phoff'])
        self._emitline(' (bytes into file)')
        self._emit('  Start of section headers           %s' % 
                header['e_shoff'])
        self._emitline(' (bytes into file)')
        self._emitline('  Flags:                             %s' % 
                self._format_hex(header['e_flags']))
        self._emitline('  Size of this header:               %s (bytes)' %
                header['e_ehsize'])
        self._emitline('  Size of program headers:           %s (bytes)' %
                header['e_phentsize'])
        self._emitline('  Number of program headers:         %s' %
                header['e_phnum'])
        self._emitline('  Size of section headers:           %s (bytes)' %
                header['e_shentsize'])
        self._emitline('  Number of section headers:         %s' %
                header['e_shnum'])
        self._emitline('  Section header string table index: %s' %
                header['e_shstrndx'])

    def display_program_headers(self):
        """ Display the ELF program headers
        """
        self._emitline()
        elfheader = self.elffile.header
        self._emitline('Elf file type is %s' %
            describe_e_type(elfheader['e_type']))
        self._emitline('Entry point is %s' %
            self._format_hex(elfheader['e_entry']))
        # readelf weirness - why isn't e_phoff printed as hex? (for section
        # headers, it is...)
        self._emitline('There are %s program headers, starting at offset %s' % (
            elfheader['e_phnum'], elfheader['e_phoff']))

        self._emitline('\nProgram headers:')

        # Now comes the table of program headers with their attributes. Note
        # that due to different formatting constraints of 32-bit and 64-bit
        # addresses, there are some conditions on elfclass here.
        #
        # First comes the table heading
        #
        if self.elffile.elfclass == 32:
            self._emitline('  Type           Offset   VirtAddr   PhysAddr   FileSiz MemSiz  Flg Align')
        else:
            self._emitline('  Type           Offset             VirtAddr           PhysAddr')
            self._emitline('                 FileSiz            MemSiz              Flags  Align')

        # Now the entries
        #
        for segment in self.elffile.iter_segments():
            self._emit('  %-14s ' % describe_p_type(segment['p_type']))

            if self.elffile.elfclass == 32:
                self._emitline('%s %s %s %s %s %-3s %s' % (
                    self._format_hex(segment['p_offset'], fieldsize=6),
                    self._format_hex(segment['p_vaddr'], fullhex=True),
                    self._format_hex(segment['p_paddr'], fullhex=True),
                    self._format_hex(segment['p_filesz'], fieldsize=5),
                    self._format_hex(segment['p_memsz'], fieldsize=5),
                    describe_p_flags(segment['p_flags']),
                    self._format_hex(segment['p_align'])))
            else: # 64
                self._emitline('%s %s %s' % (
                    self._format_hex(segment['p_offset'], fullhex=True),
                    self._format_hex(segment['p_vaddr'], fullhex=True),
                    self._format_hex(segment['p_paddr'], fullhex=True)))
                self._emitline('                 %s %s  %-3s    %s' % (
                    self._format_hex(segment['p_filesz'], fullhex=True),
                    self._format_hex(segment['p_memsz'], fullhex=True),
                    describe_p_flags(segment['p_flags']),
                    # lead0x set to False for p_align, to mimic readelf.
                    # No idea why the difference from 32-bit mode :-|
                    self._format_hex(segment['p_align'], lead0x=False)))

            if isinstance(segment, InterpSegment):
                self._emitline('      [Requesting program interpreter: %s]' % 
                    segment.get_interp_name())

        # Sections to segments mapping
        #
        if self.elffile.num_sections() == 0:
            # No sections? We're done
            return 

        self._emitline('\n Section to Segment mapping:')
        self._emitline('  Segment Sections...\n')

        for nseg, segment in enumerate(self.elffile.iter_segments()):
            self._emit('   %2.2d    ' % nseg)

            for section in self.elffile.iter_sections():
                if (    not section.is_null() and 
                        segment.section_in_segment(section)):
                    self._emit('%s ' % section.name)

            self._emitline('')

    def display_section_headers(self):
        """ Display the ELF section headers
        """
        elfheader = self.elffile.header
        self._emitline('There are %s section headers, starting at offset %s' % (
            elfheader['e_shnum'], self._format_hex(elfheader['e_shoff'])))

        self._emitline('\nSection header%s:' % (
            's' if elfheader['e_shnum'] > 1 else ''))

        # Different formatting constraints of 32-bit and 64-bit addresses
        #
        if self.elffile.elfclass == 32:
            self._emitline('  [Nr] Name              Type            Addr     Off    Size   ES Flg Lk Inf Al')
        else:
            self._emitline('  [Nr] Name              Type             Address           Offset')
            self._emitline('       Size              EntSize          Flags  Link  Info  Align')

        # Now the entries
        #
        for nsec, section in enumerate(self.elffile.iter_sections()):
            self._emit('  [%2u] %-17.17s %-15.15s ' % (
                nsec, section.name, describe_sh_type(section['sh_type'])))

            if self.elffile.elfclass == 32:
                self._emitline('%s %s %s %s %3s %2s %3s %2s' % (
                    self._format_hex(section['sh_addr'], fieldsize=8, lead0x=False),
                    self._format_hex(section['sh_offset'], fieldsize=6, lead0x=False),
                    self._format_hex(section['sh_size'], fieldsize=6, lead0x=False),
                    self._format_hex(section['sh_entsize'], fieldsize=2, lead0x=False),
                    describe_sh_flags(section['sh_flags']),
                    section['sh_link'], section['sh_info'],
                    section['sh_addralign']))
            else: # 64
                self._emitline(' %s  %s' % (
                    self._format_hex(section['sh_addr'], fullhex=True, lead0x=False),
                    self._format_hex(section['sh_offset'],
                        fieldsize=16 if section['sh_offset'] > 0xffffffff else 8,
                        lead0x=False)))
                self._emitline('       %s  %s %3s      %2s   %3s     %s' % (
                    self._format_hex(section['sh_size'], fullhex=True, lead0x=False),
                    self._format_hex(section['sh_entsize'], fullhex=True, lead0x=False),
                    describe_sh_flags(section['sh_flags']),
                    section['sh_link'], section['sh_info'],
                    section['sh_addralign']))

        self._emitline('Key to Flags:')
        self._emitline('  W (write), A (alloc), X (execute), M (merge), S (strings)')
        self._emitline('  I (info), L (link order), G (group), x (unknown)')
        self._emitline('  O (extra OS processing required) o (OS specific), p (processor specific)')

    def display_symbol_tables(self):
        """ Display the symbol tables contained in the file
        """
        for section in self.elffile.iter_sections():
            if not isinstance(section, SymbolTableSection):
                continue

            if section['sh_entsize'] == 0:
                self._emitline("\nSymbol table '%s' has a sh_entsize of zero!" % (
                    section.name))
                continue

            self._emitline("\nSymbol table '%s' contains %s entries:" % (
                section.name, section.num_symbols()))

            if self.elffile.elfclass == 32:
                self._emitline('   Num:    Value  Size Type    Bind   Vis      Ndx Name')
            else: # 64
                self._emitline('   Num:    Value          Size Type    Bind   Vis      Ndx Name')

            for nsym, symbol in enumerate(section.iter_symbols()):
                # symbol names are truncated to 25 chars, similarly to readelf
                self._emitline('%6d: %s %5d %-7s %-6s %-7s %4s %.25s' % (
                    nsym,
                    self._format_hex(symbol['st_value'], fullhex=True, lead0x=False),
                    symbol['st_size'],
                    describe_symbol_type(symbol['st_info']['type']),
                    describe_symbol_bind(symbol['st_info']['bind']),
                    describe_symbol_visibility(symbol['st_other']['visibility']),
                    describe_symbol_shndx(symbol['st_shndx']),
                    symbol.name))
        
    def _format_hex(self, addr, fieldsize=None, fullhex=False, lead0x=True):
        """ Format an address into a hexadecimal string.

            fieldsize:
                Size of the hexadecimal field (with leading zeros to fit the
                address into. For example with fieldsize=8, the format will
                be %08x
                If None, the minimal required field size will be used.

            fullhex:
                If True, override fieldsize to set it to the maximal size 
                needed for the elfclass

            lead0x:
                If True, leading 0x is added
        """
        s = '0x' if lead0x else ''
        if fullhex:
            fieldsize = 8 if self.elffile.elfclass == 32 else 16
        if fieldsize is None:
            field = '%x'
        else:
            field = '%' + '0%sx' % fieldsize
        return s + field % addr
        
    def _emit(self, s=''):
        """ Emit an object to output
        """
        self.output.write(str(s))

    def _emitline(self, s=''):
        """ Emit an object to output, followed by a newline
        """
        self.output.write(str(s) + '\n')


def main():
    optparser = OptionParser(
            usage='usage: %prog [options] <elf-file>',
            description='Display information about the contents of ELF format files',
            add_help_option=False, # -h is a real option of readelf
            prog='readelf.py')
    optparser.add_option('-H', '--help',
            action='store_true', dest='help',
            help='Display this information')
    optparser.add_option('-h', '--file-header',
            action='store_true', dest='show_file_header',
            help='Display the ELF file header')
    optparser.add_option('-l', '--program-headers', '--segments',
            action='store_true', dest='show_program_headers',
            help='Display the program headers')
    optparser.add_option('-S', '--section-headers', '--sections',
            action='store_true', dest='show_section_headers',
            help="Display the sections' headers")
    optparser.add_option('-e', '--headers',
            action='store_true', dest='show_all_headers',
            help='Equivalent to: -h -l -S')
    optparser.add_option('-s', '--symbols', '--syms',
            action='store_true', dest='show_symbols',
            help='Display the symbol table')
    options, args = optparser.parse_args()

    if options.help or len(args) == 0:
        optparser.print_help()
        sys.exit(0)

    with open(args[0], 'rb') as file:
        try:
            readelf = ReadElf(file, sys.stdout)
            #readelf.display_file_header()
            #readelf.display_program_headers()
            #readelf.display_section_headers()
            readelf.display_symbol_tables()
        except ELFError as ex:
            sys.stderr.write('ELF read error: %s\n' % ex)
            sys.exit(1)


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()

