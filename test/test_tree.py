#------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#
# Making sure the two ways of iterating through DIEs (linear and by tree)
# return an identically built tree (parents, children, terminators).
# 
# TODO: find a siblingless file. None in the corpus so far.
#------------------------------------------------------------------------------

import unittest
import os
from elftools.elf.elffile import ELFFile

class TestTree(unittest.TestCase):
    def test_tree(self):
        self.run_test_on('dwarf_llpair.elf')

    def run_test_on(self, file_name):
        def die_summary(die):
            return (die.offset, die.tag, die._terminator.offset if die._terminator else None, die.get_parent().offset if die.get_parent() else None)
        
        with ELFFile.load_from_path(os.path.join('test', 'testfiles_for_unittests', file_name)) as elf:
            di = elf.get_dwarf_info()
            cu = next(di.iter_CUs())
            #_terminator is only set on a DIE *after* that DIE is yielded during enumeration
            DIEs = [d for d in cu.iter_DIEs() if not d.is_null()]
            seq_DIEs = [die_summary(d) for d in DIEs]

            sample_offset = DIEs[len(DIEs) // 2].offset
            # Offset of a random DIE from the middle for later

            # Deliberately erase the CU/DIE cache to force a repeat parse - this time using an explicit tree traversal
            di = elf.get_dwarf_info()
            cu = next(di.iter_CUs())
            DIEs = []
            def add_subtree(die):
                DIEs.append(die)
                if die.has_children:
                    for child in die.iter_children():
                        add_subtree(child)
            add_subtree(cu.get_top_DIE())
            tree_DIEs = [die_summary(d) for d in DIEs]
            self.assertSequenceEqual(seq_DIEs, tree_DIEs)

            # Another repeat parse, with a nonblank cache
            di = elf.get_dwarf_info()
            cu = next(di.iter_CUs())
            cu.get_DIE_from_refaddr(sample_offset) # Cache this random DIE in the middle
            DIEs = [d for d in cu.iter_DIEs() if not d.is_null()]
            seq_DIEs_x = [die_summary(d) for d in DIEs]
            self.assertSequenceEqual(seq_DIEs, seq_DIEs_x)

if __name__ == '__main__':
    unittest.main()
