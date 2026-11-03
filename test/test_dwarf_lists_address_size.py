import struct
import unittest
from io import BytesIO

from elftools.dwarf.dwarfinfo import (
    DebugSectionDescriptor,
    DwarfConfig,
    DWARFInfo,
)


def make_dwarf(versions, address_sizes, little_endian, default_address_size):
    """Encode small DWARF units with location and range list references.

    The section bytes are independent of DWARFStructs, so the fixture does
    not inherit the address-size choice being tested.
    """
    endian = '<' if little_endian else '>'
    sections = {name: bytearray() for name in (
        'info', 'abbrev', 'loc', 'ranges', 'loclists', 'rnglists')}
    # Compile unit with DW_AT_ranges/DW_FORM_sec_offset, then a variable
    # with DW_AT_location/DW_FORM_sec_offset.
    sections['abbrev'].extend(bytes([
        1, 0x11, 1, 0x55, 0x17, 0, 0,
        2, 0x34, 0, 2, 0x17, 0, 0, 0,
    ]))
    for version, address_size in zip(versions, address_sizes):
        def addr(value, address_size=address_size):
            return value.to_bytes(
                address_size, 'little' if little_endian else 'big')
        base = 0x12340000 if address_size == 4 else 0x1234567800000000
        if version < 5:
            loc_offset = len(sections['loc'])
            range_offset = len(sections['ranges'])
            base_entry = addr((1 << (8 * address_size)) - 1) + addr(base)
            interval = addr(0x10) + addr(0x20)
            terminator = addr(0) + addr(0)
            sections['loc'].extend(
                base_entry + interval + struct.pack(endian + 'H', 1) +
                b'\x50' + terminator)
            sections['ranges'].extend(base_entry + interval + terminator)
            header = struct.pack(endian + 'HIB', version, 0, address_size)
        else:
            # DWARF5 list contributions have an initial length, version,
            # address size, segment selector size, and offset entry count.
            loc_body = (b'\x06' + addr(base) + b'\x07' +
                        addr(base + 0x10) + addr(base + 0x20) + b'\x01\x50\x00')
            range_body = (b'\x05' + addr(base) + b'\x06' +
                          addr(base + 0x10) + addr(base + 0x20) + b'\x00')
            loc_offset = len(sections['loclists']) + 12
            range_offset = len(sections['rnglists']) + 12
            for name, body in (('loclists', loc_body), ('rnglists', range_body)):
                sections[name].extend(struct.pack(
                    endian + 'IHBBI', len(body) + 8, 5, address_size, 0, 0) + body)
            header = struct.pack(endian + 'HBBI', version, 1, address_size, 0)
        dies = (b'\x01' + struct.pack(endian + 'I', range_offset) +
                b'\x02' + struct.pack(endian + 'I', loc_offset) + b'\x00')
        sections['info'].extend(
            struct.pack(endian + 'I', len(header) + len(dies)) + header + dies)

    def section(name):
        data = sections.get(name)
        if not data:
            return None
        return DebugSectionDescriptor(BytesIO(data), '.debug_' + name, 0, len(data), 0)

    names = ('info', 'aranges', 'abbrev', 'frame', 'str', 'loc', 'ranges',
             'line', 'pubtypes', 'pubnames', 'addr', 'str_offsets', 'line_str',
             'loclists', 'rnglists', 'sup', 'types')
    return DWARFInfo(
        config=DwarfConfig(little_endian, 'x64', default_address_size),
        eh_frame_sec=None, gnu_debugaltlink_sec=None,
        **{'debug_' + name + '_sec': section(name) for name in names})


class TestListsAddressSize(unittest.TestCase):
    def assert_lists(self, locations, ranges, cu, address_size):
        die = next(die for die in cu.iter_DIEs() if die.tag == 'DW_TAG_variable')
        location_list = locations.get_location_list_at_offset(
            die.attributes['DW_AT_location'].value, die)
        range_list = ranges.get_range_list_at_offset(
            cu.get_top_DIE().attributes['DW_AT_ranges'].value, cu)
        base = 0x12340000 if address_size == 4 else 0x1234567800000000
        self.assertEqual(len(location_list), 2)
        self.assertEqual(len(range_list), 2)
        self.assertEqual(location_list[0].base_address, base)
        self.assertEqual(range_list[0].base_address, base)
        start = base + 0x10 if cu['version'] >= 5 else 0x10
        end = base + 0x20 if cu['version'] >= 5 else 0x20
        for entry in (location_list[1], range_list[1]):
            self.assertEqual((entry.begin_offset, entry.end_offset), (start, end))
            self.assertEqual(entry.is_absolute, cu['version'] >= 5)
        self.assertEqual(location_list[1].loc_expr, [0x50])
        return location_list, range_list

    def test_cu_address_sizes(self):
        for version in (4, 5):
            for little_endian in (False, True):
                for default_address_size in (4, 8):
                    with self.subTest(version=version, little_endian=little_endian,
                                      default_address_size=default_address_size):
                        dwarf = make_dwarf([version] * 3, [4, 8, 4],
                                           little_endian, default_address_size)
                        cus = list(dwarf.iter_CUs())
                        locations, ranges = dwarf.location_lists(), dwarf.range_lists()
                        expected = [self.assert_lists(locations, ranges, cu, size)
                                    for cu, size in zip(cus, [4, 8, 4])]
                        self.assertEqual(list(locations.iter_location_lists()),
                                         [item[0] for item in expected])
                        self.assertEqual(list(ranges.iter_range_lists()),
                                         [item[1] for item in expected])
                        # Parsing a CU must not change the shared default parser.
                        self.assertIs(locations.structs, dwarf.structs)
                        self.assertIs(ranges.structs, dwarf.structs)
                        self.assert_lists(locations, ranges, cus[0], 4)

    def test_mixed_versions(self):
        for little_endian in (False, True):
            with self.subTest(little_endian=little_endian):
                dwarf = make_dwarf([4, 5, 4, 5], [4, 8, 8, 4], little_endian, 8)
                locations, ranges = dwarf.location_lists(), dwarf.range_lists()
                cus = list(dwarf.iter_CUs())
                for index in (0, 1, 2, 3, 0):
                    self.assert_lists(locations, ranges, cus[index], [4, 8, 8, 4][index])

    def test_legacy_calls_without_cu(self):
        for address_size in (4, 8):
            with self.subTest(address_size=address_size):
                dwarf = make_dwarf([4], [address_size], True, address_size)
                cu = next(dwarf.iter_CUs())
                locations, ranges = dwarf.location_lists(), dwarf.range_lists()
                expected = self.assert_lists(locations, ranges, cu, address_size)
                self.assertEqual(locations.get_location_list_at_offset(0), expected[0])
                self.assertEqual(ranges.get_range_list_at_offset(0), expected[1])


if __name__ == '__main__':
    unittest.main()
