import json
import re
import unittest
from pathlib import Path

from elftools.dwarf.descriptions import describe_DWARF_expr
from elftools.dwarf.locationlists import (
    BaseAddressEntry as LocationBaseAddressEntry,
)
from elftools.dwarf.locationlists import (
    LocationEntry,
)
from elftools.dwarf.ranges import BaseAddressEntry as RangeBaseAddressEntry
from elftools.elf.elffile import ELFFile

FIXTURES = Path('test/testfiles_for_unittests/mixed_bitness')


def expression_without_register_names(expression):
    # The register numbers are encoded in DWARF. Their display names depend
    # on global machine-architecture state and are irrelevant to this test.
    return re.sub(r'(DW_OP_b?reg\d+) \([^)]*\)', r'\1', expression)


def absolute_locations(entries, cu):
    base = cu.get_top_DIE().attributes['DW_AT_low_pc'].value
    result = []
    for entry in entries:
        if isinstance(entry, LocationBaseAddressEntry):
            base = entry.base_address
        else:
            assert isinstance(entry, LocationEntry)
            adjustment = 0 if entry.is_absolute else base
            result.append([
                entry.begin_offset + adjustment,
                entry.end_offset + adjustment,
                expression_without_register_names(
                    describe_DWARF_expr(entry.loc_expr, cu.structs)),
            ])
    return result


def absolute_ranges(entries, cu):
    base = cu.get_top_DIE().attributes['DW_AT_low_pc'].value
    result = []
    for entry in entries:
        if isinstance(entry, RangeBaseAddressEntry):
            base = entry.base_address
        else:
            adjustment = 0 if entry.is_absolute else base
            result.append([entry.begin_offset + adjustment,
                           entry.end_offset + adjustment])
    return result


class TestExecutableMixedBitness(unittest.TestCase):
    """Parse runnable ELF64 files containing GCC i386 and x86-64 CUs.

    Fixture regeneration runs the executable on Linux x86-64. These tests
    only parse it, so other operating systems and architectures can run them.
    Expected intervals and expressions come from GNU readelf, not pyelftools.
    """

    def assert_fixture(self, version, iteration):
        expectations = json.loads((FIXTURES / 'expected.json').read_text())
        for first in (32, 64):
            name = f'dwarf{version}-{first}-first.elf'
            with self.subTest(fixture=name), (FIXTURES / name).open('rb') as stream:
                dwarf = ELFFile(stream).get_dwarf_info()
                cus = list(dwarf.iter_CUs())
                expected_cus = expectations[name]
                expected_sizes = [4, 8] if first == 32 else [8, 4]
                self.assertEqual([cu['address_size'] for cu in cus], expected_sizes)
                self.assertEqual([cu['version'] for cu in cus], [version, version])
                locations = dwarf.location_lists()
                ranges = dwarf.range_lists()
                location_references = []
                range_references = []
                for cu, expected in zip(cus, expected_cus):
                    self.assertEqual(cu['address_size'], expected['address_size'])
                    location_dies = {
                        die.attributes['DW_AT_location'].value: die
                        for die in cu.iter_DIEs()
                        if 'DW_AT_location' in die.attributes
                        and die.attributes['DW_AT_location'].form == 'DW_FORM_sec_offset'
                    }
                    self.assertEqual(sorted(location_dies),
                                     sorted(item['offset'] for item in expected['locations']))
                    for item in expected['locations']:
                        expected_entries = [entry[:2] + [
                            expression_without_register_names(entry[2])]
                            for entry in item['entries']]
                        location_references.append((item['offset'], cu, expected_entries))
                        if not iteration:
                            entries = locations.get_location_list_at_offset(
                                item['offset'], location_dies[item['offset']])
                            self.assertEqual(absolute_locations(entries, cu), expected_entries)
                    for item in expected['ranges']:
                        self.assertEqual(cu.get_top_DIE().attributes['DW_AT_ranges'].value,
                                         item['offset'])
                        range_references.append((item['offset'], cu, item['entries']))
                        if not iteration:
                            entries = ranges.get_range_list_at_offset(item['offset'], cu)
                            self.assertEqual(absolute_ranges(entries, cu), item['entries'])
                if iteration:
                    parsed = list(locations.iter_location_lists())
                    self.assertEqual(len(parsed), len(location_references))
                    for entries, (offset, cu, expected) in zip(
                            parsed, sorted(location_references, key=lambda ref: ref[0])):
                        self.assertEqual(entries[0].entry_offset, offset)
                        self.assertEqual(absolute_locations(entries, cu), expected)
                    parsed = list(ranges.iter_range_lists())
                    self.assertEqual(len(parsed), len(range_references))
                    for entries, (offset, cu, expected) in zip(
                            parsed, sorted(range_references, key=lambda ref: ref[0])):
                        self.assertEqual(entries[0].entry_offset, offset)
                        self.assertEqual(absolute_ranges(entries, cu), expected)

    def test_dwarf4_references(self):
        self.assert_fixture(4, iteration=False)

    def test_dwarf5_references(self):
        self.assert_fixture(5, iteration=False)

    def test_dwarf4_iteration(self):
        self.assert_fixture(4, iteration=True)

    def test_dwarf5_iteration(self):
        self.assert_fixture(5, iteration=True)


if __name__ == '__main__':
    unittest.main()
