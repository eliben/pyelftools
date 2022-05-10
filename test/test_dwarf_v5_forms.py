# The dwarf_v5_forms.debug file was generated as follows, using gcc 11.2.0 on
# an x86_64 machine.
# $ cat dwarf_v5_forms.c
# int main();
# {
#         char ** val;
#         return 0;
# }
# $ gcc -O0 -gdwarf-5 dwarf_v5_forms.c -o dwarf_v5_forms.debug
# $ strip --only-keep-debug dwarf_v5_forms.debug
import unittest
import os


from elftools.elf.elffile import ELFFile

class TestDWARFV5_forms(unittest.TestCase):

    def test_DW_FORM_implicit_const(self):
        path = os.path.join('test', 'testfiles_for_unittests',
                            'dwarf_v5_forms.debug')
        with open(path, 'rb') as f:
            elffile = ELFFile(f)
            dwarfinfo = elffile.get_dwarf_info()
            # File is very small, so load all DIEs.
            dies = []
            for cu in dwarfinfo.iter_CUs():
                dies.extend(cu.iter_DIEs())
            # Locate the "var" DIE.
            for die in dies:
                # There should be only one
                if (die.tag == "DW_TAG_variable" and
                    die.attributes["DW_AT_name"].value == b'val'):
                        # In the dwarfinfo, it's type is sized using a
                        # DW_FORM_implicit_const: check it is parsed correctly
                        break
            dietype = cu.get_DIE_from_refaddr(die.attributes["DW_AT_type"].value)
            byte_size_attr = dietype.attributes["DW_AT_byte_size"]
            self.assertEqual(byte_size_attr.form, "DW_FORM_implicit_const")
            self.assertEqual(byte_size_attr.value, 8)

    def test_DW_FORM_linestrp(self):
        path = os.path.join('test', 'testfiles_for_unittests',
                            'dwarf_v5_forms.debug')
        with open(path, 'rb') as f:
            elffile = ELFFile(f)
            dwarfinfo = elffile.get_dwarf_info()
            cu = next(dwarfinfo.iter_CUs())
            top_die = cu.get_top_DIE()
            name_attr = top_die.attributes["DW_AT_name"]
            self.assertEqual(name_attr.form, "DW_FORM_line_strp")
            self.assertEqual(name_attr.value, b"dwarf_v5_forms.c")
