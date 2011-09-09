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
from elftools.elf.descriptions import (
    describe_ei_class, describe_ei_data, describe_ei_version,
    describe_ei_osabi, describe_e_type,
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

    def _emit(self, s):
        """ Emit an object to output
        """
        self.output.write(str(s))
        
    def _emitline(self, s):
        """ Emit an object to output, followed by a newline
        """
        self.output.write(str(s) + '\n')


def main():
    optparser = OptionParser()
    options, args = optparser.parse_args()

    with open(args[0], 'rb') as file:
        try:
            readelf = ReadElf(file, sys.stdout)
            readelf.display_file_header()
        except ELFError as ex:
            sys.stderr.write('ELF read error: %s\n' % ex)
            sys.exit(1)


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()

