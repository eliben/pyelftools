# Regression tests for #581: CU address sizes can differ within one file.
# Build small DWARF sections directly, without a compiler or platform binary.

import unittest
from io import BytesIO
from itertools import product

from elftools.dwarf.dwarfinfo import DebugSectionDescriptor, DwarfConfig, DWARFInfo
from elftools.dwarf.locationlists import (
    BaseAddressEntry as LocationBaseAddressEntry,
)
from elftools.dwarf.locationlists import (
    LocationEntry,
    LocationListsPair,
    LocationParser,
    LocationViewPair,
)
from elftools.dwarf.ranges import BaseAddressEntry as RangeBaseAddressEntry
from elftools.dwarf.ranges import RangeEntry, RangeListsPair


def make_dwarf(units, little_endian, default_address_size, locviews=False, offset_table=False):
    """units contains (version, address_size, dwarf_format) tuples."""
    byteorder = 'little' if little_endian else 'big'

    def uint(value, size):
        return value.to_bytes(size, byteorder)

    def with_length(data, dwarf_format):
        length = uint(len(data), 4) if dwarf_format == 32 else b'\xff' * 4 + uint(len(data), 8)
        return length + data

    # CU: DW_AT_ranges/sec_offset and DW_AT_low_pc/addr, with a child variable:
    # DW_AT_location/sec_offset.
    abbrev = bytes.fromhex('01 11 01 55 17 11 01 00 00 02 34 00 02 17')
    if locviews:
        abbrev += bytes.fromhex('b7 42 17')  # DW_AT_GNU_locviews/sec_offset
    abbrev += b'\0\0\0'
    sections = {'debug_info': b'', 'debug_abbrev': abbrev}
    for version, address_size, dwarf_format in units:
        offset_size = dwarf_format // 8
        base = 0x12340000 if address_size == 4 else 0x123456780000
        views = b'\x01\x02' if locviews else b''
        if version < 5:
            loc_name, rng_name = 'debug_loc', 'debug_ranges'
            # Base address selection, one range/location, then the terminator.
            base_entry = b'\xff' * address_size + uint(base, address_size)
            entry = uint(0x10, address_size) + uint(0x20, address_size)
            terminator = b'\0' * (2 * address_size)
            loc = views + base_entry + entry + uint(1, 2) + b'\x50' + terminator
            rng = base_entry + entry + terminator
            loc_offset, rng_offset, views_offset = len(views), 0, 0
            header = uint(version, 2) + uint(0, offset_size) + uint(address_size, 1)
        else:
            loc_name, rng_name = 'debug_loclists', 'debug_rnglists'
            # DW_LLE/RLE_base_address followed by DW_LLE/RLE_start_end.
            addresses = uint(base + 0x10, address_size) + uint(base + 0x20, address_size)
            loc_entries = views + b'\x06' + uint(base, address_size) + b'\x07' + addresses + b'\x01\x50\0'
            rng_entries = b'\x05' + uint(base, address_size) + b'\x06' + addresses + b'\0'
            list_header = uint(5, 2) + uint(address_size, 1) + b'\0' + uint(int(offset_table), 4)
            loc_table = uint(offset_size + len(views), offset_size) if offset_table else b''
            rng_table = uint(offset_size, offset_size) if offset_table else b''
            loc = with_length(list_header + loc_table + loc_entries, dwarf_format)
            rng = with_length(list_header + rng_table + rng_entries, dwarf_format)
            loc_offset = len(loc) - len(loc_entries) + len(views)
            rng_offset = len(rng) - len(rng_entries)
            views_offset = loc_offset - len(views)
            header = uint(5, 2) + b'\x01' + uint(address_size, 1) + uint(0, offset_size)

        loc_offset += len(sections.get(loc_name, b''))
        views_offset += len(sections.get(loc_name, b''))
        rng_offset += len(sections.get(rng_name, b''))
        dies = b'\x01' + uint(rng_offset, offset_size) + uint(base, address_size)
        dies += b'\x02' + uint(loc_offset, offset_size)
        if locviews:
            dies += uint(views_offset, offset_size)
        sections['debug_info'] += with_length(header + dies + b'\0', dwarf_format)
        sections[loc_name] = sections.get(loc_name, b'') + loc
        sections[rng_name] = sections.get(rng_name, b'') + rng

    def section(name):
        data = sections.get(name)
        return DebugSectionDescriptor(BytesIO(data), '.' + name, None, len(data), 0) if data else None

    return DWARFInfo(
        config=DwarfConfig(little_endian=little_endian, machine_arch='64-bit PowerPC',
                           default_address_size=default_address_size),
        debug_info_sec=section('debug_info'),
        debug_abbrev_sec=section('debug_abbrev'),
        debug_loc_sec=section('debug_loc'),
        debug_ranges_sec=section('debug_ranges'),
        debug_loclists_sec=section('debug_loclists'),
        debug_rnglists_sec=section('debug_rnglists'),
        debug_aranges_sec=None, debug_frame_sec=None, eh_frame_sec=None,
        debug_str_sec=None, debug_line_sec=None, debug_pubtypes_sec=None,
        debug_pubnames_sec=None, debug_addr_sec=None, debug_str_offsets_sec=None,
        debug_line_str_sec=None, debug_sup_sec=None, gnu_debugaltlink_sec=None,
        debug_types_sec=None)


class TestMixedAddressSizes(unittest.TestCase):
    def check_lists(self, cu, locations, ranges):
        size = cu['address_size']
        base = 0x12340000 if size == 4 else 0x123456780000
        absolute = cu['version'] >= 5
        begin, end = (base + 0x10, base + 0x20) if absolute else (0x10, 0x20)
        self.assertEqual(len(locations), 2)
        self.assertEqual(len(ranges), 2)
        self.assertIsInstance(locations[0], LocationBaseAddressEntry)
        self.assertIsInstance(ranges[0], RangeBaseAddressEntry)
        self.assertEqual(locations[0].base_address, base)
        self.assertEqual(ranges[0].base_address, base)
        self.assertIsInstance(locations[1], LocationEntry)
        self.assertIsInstance(ranges[1], RangeEntry)
        for entry in (locations[1], ranges[1]):
            self.assertEqual((entry.begin_offset, entry.end_offset), (begin, end))
            self.assertEqual(entry.is_absolute, absolute)
        self.assertEqual(locations[1].loc_expr, [0x50])

    def read_lists(self, cu, locations, ranges):
        die = next(cu.get_top_DIE().iter_children())
        loc = LocationParser(locations).parse_from_attribute(
            die.attributes['DW_AT_location'], cu['version'], die)
        rng = ranges.get_range_list_at_offset(cu.get_top_DIE().attributes['DW_AT_ranges'].value, cu)
        self.check_lists(cu, loc, rng)
        return loc, rng

    def test_lookup(self):
        for version, little_endian, default_size, formats in product(
                (4, 5), (True, False), (4, 8), ((32, 64), (64, 32))):
            with self.subTest(version=version, little_endian=little_endian,
                              default_size=default_size, formats=formats):
                dwarf = make_dwarf(((version, 4, formats[0]), (version, 8, formats[1])),
                                   little_endian, default_size)
                cus = list(dwarf.iter_CUs())
                self.assertEqual([cu['address_size'] for cu in cus], [4, 8])
                self.assertEqual([cu.structs.dwarf_format for cu in cus], list(formats))
                locations, ranges = dwarf.location_lists(), dwarf.range_lists()
                # Revisit both CUs after parsing the other address size.
                for cu in (cus[0], cus[1], cus[0], cus[1]):
                    self.read_lists(cu, locations, ranges)
                self.assertIs(locations.structs, dwarf.structs)
                self.assertIs(ranges.structs, dwarf.structs)

    def test_iteration(self):
        for version, little_endian, locviews in product((4, 5), (True, False), (False, True)):
            with self.subTest(version=version, little_endian=little_endian, locviews=locviews):
                dwarf = make_dwarf(((version, 4, 64), (version, 8, 32)),
                                   little_endian, 8, locviews=locviews, offset_table=True)
                locations = list(dwarf.location_lists().iter_location_lists())
                ranges = list(dwarf.range_lists().iter_range_lists())
                self.assertEqual(len(locations), 2)
                self.assertEqual(len(ranges), 2)
                for cu, loc, rng in zip(dwarf.iter_CUs(), locations, ranges):
                    if locviews:
                        self.assertIsInstance(loc[0], LocationViewPair)
                        self.assertEqual((loc[0].begin, loc[0].end), (1, 2))
                        loc = loc[1:]
                    self.check_lists(cu, loc, rng)

    def test_mixed_versions(self):
        for little_endian in (True, False):
            with self.subTest(little_endian=little_endian):
                dwarf = make_dwarf(((4, 4, 32), (5, 8, 64), (4, 8, 64), (5, 4, 32)),
                                   little_endian, 8)
                locations, ranges = dwarf.location_lists(), dwarf.range_lists()
                self.assertIsInstance(locations, LocationListsPair)
                self.assertIsInstance(ranges, RangeListsPair)
                for cu in dwarf.iter_CUs():
                    self.read_lists(cu, locations, ranges)
                    if cu['version'] == 5:
                        raw = ranges.get_range_list_at_offset_ex(
                            cu.get_top_DIE().attributes['DW_AT_ranges'].value, cu)
                        self.check_raw(cu, raw)

    def check_raw(self, cu, entries):
        base = 0x12340000 if cu['address_size'] == 4 else 0x123456780000
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].entry_type, 'DW_RLE_base_address')
        self.assertEqual(entries[0].address, base)
        self.assertEqual(entries[1].entry_type, 'DW_RLE_start_end')
        self.assertEqual((entries[1].start_address, entries[1].end_address), (base + 0x10, base + 0x20))

    def test_raw_ranges(self):
        for little_endian, offset_table, formats in product(
                (True, False), (False, True), ((32, 64), (64, 32))):
            with self.subTest(little_endian=little_endian, offset_table=offset_table, formats=formats):
                dwarf = make_dwarf(((5, 4, formats[0]), (5, 8, formats[1])),
                                   little_endian, 8, offset_table=offset_table)
                ranges = dwarf.range_lists()
                cus = list(dwarf.iter_CUs())
                headers = list(ranges.iter_CUs())
                self.assertEqual([header.address_size for header in headers], [4, 8])
                for cu, header in zip(cus, headers):
                    offset = cu.get_top_DIE().attributes['DW_AT_ranges'].value
                    raw = ranges.get_range_list_at_offset_ex(offset, cu)
                    self.check_raw(cu, raw)
                    # Enumeration must use the table header, including its offset width.
                    self.assertEqual(list(ranges.iter_CU_range_lists_ex(header)), [raw])
                    if offset_table:
                        self.assertEqual(header.offset_table_offset + header.offsets[0], offset)

    def test_default_structs_without_cu(self):
        for version, default_size in product((4, 5), (4, 8)):
            with self.subTest(version=version, default_size=default_size):
                other_size = 8 if default_size == 4 else 4
                dwarf = make_dwarf(((version, default_size, 32), (version, other_size, 32)),
                                   True, default_size)
                locations, ranges = dwarf.location_lists(), dwarf.range_lists()
                first, other = list(dwarf.iter_CUs())
                self.read_lists(other, locations, ranges)
                offset = first.get_top_DIE().attributes['DW_AT_ranges'].value
                if version == 4:
                    die = next(first.get_top_DIE().iter_children())
                    loc = locations.get_location_list_at_offset(die.attributes['DW_AT_location'].value)
                    rng = ranges.get_range_list_at_offset(offset)
                    self.check_lists(first, loc, rng)
                else:
                    self.check_raw(first, ranges.get_range_list_at_offset_ex(offset))


if __name__ == '__main__':
    unittest.main()
