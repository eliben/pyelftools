#------------------------------------------------------------------------------
# elftools tests
#
# Gabriele Digregorio - Io_no
# This code is in the public domain
#------------------------------------------------------------------------------

from elftools.elf.elffile import ELFFile
import unittest


class TestDebuglink(unittest.TestCase):
    """ This test verifies that the .gnu_debuglink section is followed and parsed correctly.
        The test file contains a .gnu_debuglink section that points to a debug file
        containing DWARF info.
        We verify that the subprograms are correctly retrieved from the debug file.
    """

    def stream_loader(self, external_filename: str) -> 'IO[bytes]':
        """
        This function takes an external filename to load a supplementary object file,
        and returns a stream suitable for creating a new ELFFile.
        Args:
            external_filename (str): The relative file path to load.

        Returns:
            stream (IO[bytes]): A stream suitable for creating a new ELFFile.
        """
        self.assertEqual(external_filename, b'debuglink.debug')
        stream = open(b'test/testfiles_for_unittests/' + external_filename, 'rb')
        return stream

    def subprograms_from_debuglink(self, elf: ELFFile) -> dict[str, (int, int)]:
        """Returns a dictionary containing the subprograms of the specified ELF file from the linked
        debug file.
        Args:
            elf (ELFFile): The ELF file.

        Returns:
            dict: A dictionary containing the subprograms of the specified ELF file.
        """
        subprograms = {}

        # Retrieve the subprograms from the DWARF info
        dwarf_info = elf.get_dwarf_info(follow_links=True, relocate_dwarf_sections=True)

        if dwarf_info:
            for CU in dwarf_info.iter_CUs():
                for DIE in CU.iter_DIEs():
                    if DIE.tag == 'DW_TAG_subprogram':
                        attributes = DIE.attributes
                        lowpc_attr = attributes.get('DW_AT_low_pc')
                        highpc_attr = attributes.get('DW_AT_high_pc')
                        name_attr = attributes.get('DW_AT_name')
                        if not lowpc_attr or not highpc_attr or not name_attr:
                            continue
                        lowpc = lowpc_attr.value
                        if highpc_attr.form == 'DW_FORM_addr':
                            # highpc is an absolute address
                            size = highpc_attr.value - lowpc
                        elif highpc_attr.form in {'DW_FORM_data2','DW_FORM_data4',
                                                    'DW_FORM_data8', 'DW_FORM_data1',
                                                    'DW_FORM_udata'}:
                            # highpc is an offset from lowpc
                            size = highpc_attr.value
                        name = name_attr.value
                        subprograms[name] = (lowpc, size)
        return subprograms

    def test_debuglink(self):
        with open('test/testfiles_for_unittests/debuglink', "rb") as elf_file:
            elf = ELFFile(elf_file, stream_loader=self.stream_loader)
            # Contains eh_frame and gnu_debuglink, but no DWARF
            self.assertTrue(elf.has_dwarf_info(False))
            self.assertFalse(elf.has_dwarf_info(True))
            self.assertTrue(elf.has_dwarf_link())

            link = elf.get_dwarf_link()
            self.assertIsNotNone(link)
            self.assertEqual(link.filename, b'debuglink.debug')
            self.assertEqual(link.checksum, 0x29b7c5f1)

            subprograms = self.subprograms_from_debuglink(elf)
            self.assertEqual(subprograms, {b'main': (0x1161, 0x52), b'addNumbers': (0x1149, 0x18)})

        # Test the filesystem aware ELFFile loading
        elf = ELFFile.load_from_path('test/testfiles_for_unittests/debuglink')
        subprograms = self.subprograms_from_debuglink(elf)
        self.assertEqual(subprograms, {b'main': (0x1161, 0x52), b'addNumbers': (0x1149, 0x18)})

if __name__ == '__main__':
    unittest.main()

