#!/opt/csw/bin/python
#-------------------------------------------------------------------------------
# scripts/elfdump.py
#
# A clone of 'elfdump' in Python, based on the pyelftools library
#
# Eli Bendersky (eliben@gmail.com)
# Yann Rouillard (yann@pleiades.fr.eu.org)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
from optparse import OptionParser
import string

# For running from development directory. It should take precedence over the
# installed pyelftools.
sys.path.insert(0, '.')


from elftools import __version__
from elftools.common.exceptions import ELFError
from elftools.common.py3compat import (
        ifilter, byte2int, bytes2str, itervalues, str2bytes)
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection, DynamicSegment
from elftools.elf.enums import ENUM_D_TAG
from elftools.elf.constants import SYMINF0_FLAGS
from elftools.elf.segments import InterpSegment
from elftools.elf.sections import SUNWSyminfoTableSection
from elftools.elf.relocation import RelocationSection
from elftools.elf.descriptions import (
    describe_ei_class, describe_ei_data, describe_ei_version,
    describe_ei_osabi, describe_e_type, describe_e_machine,
    describe_e_version_numeric, describe_p_type, describe_p_flags,
    describe_sh_type, describe_sh_flags,
    describe_symbol_type, describe_symbol_bind, describe_symbol_visibility,
    describe_symbol_shndx, describe_reloc_type, describe_dyn_tag,
    describe_syminfo_flags,
    )
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.dwarf.descriptions import (
    describe_reg_name, describe_attr_value, set_global_machine_arch,
    describe_CFI_instructions, describe_CFI_register_rule,
    describe_CFI_CFA_rule,
    )
from elftools.dwarf.constants import (
    DW_LNS_copy, DW_LNS_set_file, DW_LNE_define_file)
from elftools.dwarf.callframe import CIE, FDE


class Elfdump(object):
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

    def display_syminfo_table(self):
        """ Display the SUNW syminfo tables contained in the file
        """
        # The symbol table section pointed to in sh_link
        dyntable = self.elffile.get_section_by_name('.dynamic')

        for section in self.elffile.iter_sections():
            if not isinstance(section, SUNWSyminfoTableSection):
                continue

            if section['sh_entsize'] == 0:
                self._emitline("\nSymbol table '%s' has a sh_entsize of zero!" % (
                    bytes2str(section.name)))
                continue

            # The symbol table section pointed to in sh_link
            symtable = self.elffile.get_section(section['sh_link'])

            self._emitline("\nSyminfo Section:  %s" % bytes2str(section.name))
            self._emitline('     index  flags            bound to                 symbol')

            for nsym, syminfo in enumerate(section.iter_symbols(), start=1):

                # elfdump doesn't display anything for this kind of symbols
                symbol = symtable.get_symbol(nsym)
                if (symbol['st_info']['type'] == 'STT_NOTYPE' and
                        symbol['st_shndx'] == 'SHN_UNDEF'):
                    continue

                index = ''
                if syminfo['si_flags'] & SYMINF0_FLAGS.SYMINFO_FLG_CAP:
                    boundto = '<symbol capabilities>'
                elif syminfo['si_boundto'] == 0xffff:
                    boundto = '<self>'
                elif syminfo['si_boundto'] == 0xfffe:
                    boundto = '<parent>'
                elif syminfo['si_boundto'] == 0xfffd:
                    boundto = ''
                else:
                    boundto = bytes2str(dyntable.get_tag(syminfo['si_boundto']).needed)
                    index = '[%d]' % syminfo['si_boundto']

                # syminfo names are truncated to 25 chars, similarly to readelf
                self._emitline('%10s  %-5s %10s %-24s %s' % (
                    '[%d]' % (int(nsym)),
                    describe_syminfo_flags(syminfo['si_flags']),
                    index,
                    boundto,
                    bytes2str(syminfo.name)))

    def _emit(self, s=''):
        """ Emit an object to output
        """
        self.output.write(str(s))

    def _emitline(self, s=''):
        """ Emit an object to output, followed by a newline
        """
        self.output.write(str(s) + '\n')


SCRIPT_DESCRIPTION = 'Dumps selected parts of an object file'
VERSION_STRING = '%%prog: based on pyelftools %s' % __version__


def main(stream=None):
    # parse the command-line arguments and invoke ReadElf
    optparser = OptionParser(
            usage='usage: %prog [options] <elf-file>',
            description=SCRIPT_DESCRIPTION,
            add_help_option=False,  # -h is a real option of readelf
            prog='elfdump.py',
            version=VERSION_STRING)
    optparser.add_option('--help',
            action='store_true', dest='help',
            help='Display this information')
    optparser.add_option('-y',
            action='store_true', dest='show_syminfo',
            help='dump the contents of the .SUNW_syminfo section')

    options, args = optparser.parse_args()

    if options.help or len(args) == 0:
        optparser.print_help()
        sys.exit(0)

    with open(args[0], 'rb') as file:
        try:
            readelf = Elfdump(file, stream or sys.stdout)
            if options.show_syminfo:
                readelf.display_syminfo_table()
        except ELFError as ex:
            sys.stderr.write('ELF error: %s\n' % ex)
            sys.exit(1)


def profile_main():
    # Run 'main' redirecting its output to readelfout.txt
    # Saves profiling information in readelf.profile
    PROFFILE = 'elfdump.profile'
    import cProfile
    cProfile.run('main(open("elfdumpout.txt", "w"))', PROFFILE)

    # Dig in some profiling stats
    import pstats
    p = pstats.Stats(PROFFILE)
    p.sort_stats('cumulative').print_stats(25)


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
    #profile_main()
