#!/usr/bin/env python
#-------------------------------------------------------------------------------
# scripts/dwarfdump.py
#
# A clone of 'llvm-dwarfdump' in Python, based on the pyelftools library
# Roughly corresponding to v15
#
# Sources under https://github.com/llvm/llvm-project/tree/main/llvm/tools/llvm-dwarfdump
#
# Utterly incompatible with 64-bit DWARF or DWARFv2 targeting a 64-bit machine.
# Also incompatible with machines that have a selector/segment in the address.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import argparse
import os, sys, posixpath
import traceback

# For running from development directory. It should take precedence over the
# installed pyelftools.
sys.path.insert(0, '.')

from elftools import __version__
from elftools.common.exceptions import DWARFError, ELFError
from elftools.common.utils import bytes2str
from elftools.elf.elffile import ELFFile
from elftools.dwarf.locationlists import LocationParser, LocationEntry, LocationExpr, LocationViewPair, BaseAddressEntry as LocBaseAddressEntry
from elftools.dwarf.ranges import RangeEntry # ranges.BaseAddressEntry collides with the one above
import elftools.dwarf.ranges
from elftools.dwarf.enums import *
from elftools.dwarf.dwarf_expr import DWARFExprParser, DWARFExprOp
from elftools.dwarf.datatype_cpp import DIE_name, describe_cpp_datatype
from elftools.dwarf.descriptions import describe_reg_name

# ------------------------------
# ------------------------------

def _get_cu_base(cu):
    top_die = cu.get_top_DIE()
    attr = top_die.attributes
    if 'DW_AT_low_pc' in attr:
        return attr['DW_AT_low_pc'].value
    elif 'DW_AT_entry_pc' in attr:
        return attr['DW_AT_entry_pc'].value
    else:
        raise ValueError("Can't find the base IP (low_pc) for a CU")

def _addr_str_length(die):
    return die.cu.header.address_size*2

def _DIE_name(die):
    if 'DW_AT_name' in die.attributes:
        return bytes2str(die.attributes['DW_AT_name'].value)
    elif 'DW_AT_linkage_name' in die.attributes:
        return bytes2str(die.attributes['DW_AT_linkage_name'].value)
    else:
        raise DWARFError()

def _DIE_linkage_name(die):
    if 'DW_AT_linkage_name' in die.attributes:
        return bytes2str(die.attributes['DW_AT_linkage_name'].value)
    elif 'DW_AT_name' in die.attributes:
        return bytes2str(die.attributes['DW_AT_name'].value)
    else:
        raise DWARFError()        

def _safe_DIE_name(die, default=None):
    if 'DW_AT_name' in die.attributes:
        return bytes2str(die.attributes['DW_AT_name'].value)
    elif 'DW_AT_linkage_name' in die.attributes:
        return bytes2str(die.attributes['DW_AT_linkage_name'].value)
    else:
        return default

def _safe_DIE_linkage_name(die, default=None):
    if 'DW_AT_linkage_name' in die.attributes:
        return bytes2str(die.attributes['DW_AT_linkage_name'].value)
    elif 'DW_AT_name' in die.attributes:
        return bytes2str(die.attributes['DW_AT_name'].value)
    else:
        return default

def _desc_ref(attr, die, extra=''):
    if extra:
        extra = " \"%s\"" % extra
    return "cu + 0x%04x => {0x%08x}%s" % (
        attr.raw_value,
        die.cu.cu_offset + attr.raw_value,
        extra)

def _desc_data(attr, die):
    """ Hex with length driven by form
    """
    len = int(attr.form[12:]) * 2
    return "0x%0*x" % (len, attr.value,)

def _desc_strx(attr, die):
    return "indexed (%08x) string = \"%s\"" % (attr.raw_value, bytes2str(attr.value).replace("\\", "\\\\"))

FORM_DESCRIPTIONS = dict(
    DW_FORM_string=lambda attr, die: "\"%s\"" % (bytes2str(attr.value),),
    DW_FORM_strp=lambda attr, die: " .debug_str[0x%08x] = \"%s\"" % (attr.raw_value, bytes2str(attr.value).replace("\\", "\\\\")),
    DW_FORM_strx1=_desc_strx,
    DW_FORM_strx2=_desc_strx,
    DW_FORM_strx3=_desc_strx,
    DW_FORM_strx4=_desc_strx,
    DW_FORM_line_strp=lambda attr, die: ".debug_line_str[0x%08x] = \"%s\"" % (attr.raw_value, bytes2str(attr.value).replace("\\", "\\\\")),
    DW_FORM_flag_present=lambda attr, die: "true",
    DW_FORM_flag=lambda attr, die: "0x%02x" % int(attr.value),
    DW_FORM_addr=lambda attr, die: "0x%0*x" % (_addr_str_length(die), attr.value),
    DW_FORM_addrx=lambda attr, die: "indexed (%08x) address = 0x%0*x" % (attr.raw_value, _addr_str_length(die), attr.value),
    DW_FORM_data1=_desc_data,
    DW_FORM_data2=_desc_data,
    DW_FORM_data4=_desc_data,
    DW_FORM_data8=_desc_data,
    DW_FORM_block1=lambda attr, die: "<0x%02x> %s " % (len(attr.value), " ".join("%02x" %b for b in attr.value)),
    DW_FORM_block2=lambda attr, die: "<0x%04x> %s " % (len(attr.value), " ".join("%02x" %b for b in attr.value)),
    DW_FORM_block4=lambda attr, die: "<0x%08x> %s " % (len(attr.value), " ".join("%02x" %b for b in attr.value)),
    DW_FORM_ref=_desc_ref,
    DW_FORM_ref1=_desc_ref, DW_FORM_ref2=_desc_ref,
    DW_FORM_ref4=_desc_ref, DW_FORM_ref8=_desc_ref,
    DW_FORM_sec_offset=lambda attr,die:  "0x%08x" % (attr.value,),
    DW_FORM_exprloc=lambda attr, die: _desc_expression(attr.value, die)
)

def _desc_enum(attr, enum):
    """For attributes like DW_AT_language, physically
    int, logically an enum
    """
    return next((k for (k, v) in enum.items() if v == attr.value), str(attr.value))

def _cu_comp_dir(cu):
    return bytes2str(cu.get_top_DIE().attributes['DW_AT_comp_dir'].value)

def _desc_decl_file(attr, die):
    # Filename/dirname arrays are 0 based in DWARFv5
    cu = die.cu
    if not hasattr(cu, "_lineprogram"):
        cu._lineprogram = die.dwarfinfo.line_program_for_CU(cu)
    ver5 = cu._lineprogram.header.version >= 5
    file_index = attr.value if ver5 else attr.value-1
    if cu._lineprogram and file_index >= 0 and file_index < len(cu._lineprogram.header.file_entry):
        file_entry = cu._lineprogram.header.file_entry[file_index]
        dir_index = file_entry.dir_index if ver5 else file_entry.dir_index - 1
        includes = cu._lineprogram.header.include_directory
        if dir_index >= 0:
            dir = bytes2str(includes[dir_index])
            if dir.startswith('.'):
                dir = posixpath.join(_cu_comp_dir(cu), dir)
        else:
            dir = _cu_comp_dir(cu)
        file_name = bytes2str(file_entry.name)
    else:
        raise DWARFError("Invalid source filename entry index in a decl_file attribute")
    return "\"%s\"" % (posixpath.join(dir, file_name),)


def _desc_ranges(attr, die):
    di = die.cu.dwarfinfo
    if not hasattr(di, '_rnglists'):
        di._rangelists = di.range_lists()
    rangelist = di._rangelists.get_range_list_at_offset(attr.value, die.cu)
    base_ip = _get_cu_base(die.cu)
    lines = []
    addr_str_len = die.cu.header.address_size*2
    for entry in rangelist:
        if isinstance(entry, RangeEntry):
            lines.append("                 [0x%0*x, 0x%0*x)" % (
                addr_str_len,
                (0 if entry.is_absolute else base_ip) + entry.begin_offset,
                addr_str_len,
                (0 if entry.is_absolute else base_ip) + entry.end_offset))
        elif isinstance(entry, elftools.dwarf.ranges.BaseAddressEntry):
            base_ip = entry.base_address
        else:
            raise NotImplementedError("Unknown object in a range list")
    prefix = "indexed (0x%x) rangelist = " % attr.raw_value if attr.form == 'DW_FORM_rnglistx' else ''
    return ("%s0x%08x\n" % (prefix, attr.value)) + "\n".join(lines)

def _desc_locations(attr, die):
    cu = die.cu
    di = cu.dwarfinfo
    if not hasattr(di, '_loclists'):
        di._loclists = di.location_lists()
    if not hasattr(di, '_locparser'):
        di._locparser = LocationParser(di._loclists)
    loclist = di._locparser.parse_from_attribute(attr, cu.header.version, die)
    if isinstance(loclist, LocationExpr):
        return _desc_expression(loclist.loc_expr, die)
    else:
        base_ip = _get_cu_base(cu)
        lines = []
        addr_str_len = die.cu.header.address_size*2
        for entry in loclist:
            if isinstance(entry, LocationEntry):
                lines.append("                 [0x%0*x, 0x%0*x): %s" % (
                    addr_str_len,
                    (0 if entry.is_absolute else base_ip) + entry.begin_offset,
                    addr_str_len,
                    (0 if entry.is_absolute else base_ip) + entry.end_offset,
                    _desc_expression(entry.loc_expr, die)))
            elif isinstance(entry, LocBaseAddressEntry):
                base_ip = entry.base_address
            else:
                raise NotImplementedError("Unknown object in a location list")
        prefix = "indexed (0x%x) loclist = " % attr.raw_value if attr.form == 'DW_FORM_loclistx' else ''
        return ("%s0x%08x:\n" % (prefix, attr.value)) + "\n".join(lines)

# By default, numeric arguments are spelled in hex with a leading 0x
def _desc_operationarg(s, cu):
    if isinstance(s, str):
        return s
    elif isinstance(s, int):
        return hex(s)
    elif isinstance(s, list): # Could be a blob (list of ints), could be a subexpression
        if len(s) > 0 and isinstance(s[0], DWARFExprOp): # Subexpression
            return '(' + '; '.join(_desc_operation(op.op, op.op_name, op.args, cu) for op in s) + ')'
        else:
            return " ".join((hex(len(s)),) + tuple("0x%02x" % b for b in s))

def _arch(cu):
    return cu.dwarfinfo.config.machine_arch

def _desc_reg(reg_no, cu):
    return describe_reg_name(reg_no, _arch(cu), True).upper()

def _desc_operation(op, op_name, args, cu):
    # Not sure about regx(regno) and bregx(regno, offset)
    if 0x50 <= op <= 0x6f: # reg0...reg31 - decode reg name
        return op_name + " " + _desc_reg(op - 0x50, cu)
    elif 0x70 <= op <= 0x8f: # breg0...breg31(offset) - also decode reg name
        return '%s %s%+d' % (
            op_name,
            _desc_reg(op - 0x70, cu),
            args[0])
    elif op_name in ('DW_OP_fbreg', 'DW_OP_bra', 'DW_OP_skip', 'DW_OP_consts', ): # Argument is decimal with a leading sign
        return op_name + ' ' + "%+d" % (args[0])
    elif op_name in ('DW_OP_const1s', 'DW_OP_const2s'): # Argument is decimal without a leading sign
        return op_name + ' ' + "%d" % (args[0])
    elif op_name in ('DW_OP_entry_value', 'DW_OP_GNU_entry_value'): # No space between opcode and args
        return op_name + _desc_operationarg(args[0], cu)
    elif op_name == 'DW_OP_regval_type': # Arg is a DIE pointer
        return "%s %s (0x%08x -> 0x%08x) \"%s\"" % (
            op_name,
            _desc_reg(args[0], cu),
            args[1],
            args[1] + cu.cu_offset,
            _DIE_name(cu._get_cached_DIE(args[1] + cu.cu_offset)))
    elif op_name == 'DW_OP_convert': # Arg is a DIE pointer
        return "%s (0x%08x -> 0x%08x) \"%s\"" % (
            op_name,
            args[0],
            args[0] + cu.cu_offset,
            _DIE_name(cu._get_cached_DIE(args[0] + cu.cu_offset)))
    elif args:
        return op_name + ' ' + ', '.join(_desc_operationarg(s, cu) for s in args)
    else:
        return op_name

# TODO: remove this once dwarfdump catches up
UNSUPPORTED_OPS = (
    'DW_OP_implicit_pointer',
    'DW_OP_deref_type',
    'DW_OP_GNU_parameter_ref',
    'DW_OP_GNU_deref_type',
    'DW_OP_GNU_implicit_pointer',
    'DW_OP_GNU_convert',
    'DW_OP_GNU_regval_type')

def _desc_expression(expr, die):
    cu = die.cu
    if not hasattr(cu, '_exprparser'):
        cu._exprparser = DWARFExprParser(cu.structs)

    parsed = cu._exprparser.parse_expr(expr)
    # TODO: remove this once dwarfdump catches up
    first_unsupported = next((i for (i, op) in enumerate(parsed) if op.op_name in UNSUPPORTED_OPS), None)
    if first_unsupported is None:
        lines = [_desc_operation(op.op, op.op_name, op.args, cu) for op in parsed]
    else:
        lines = [_desc_operation(op.op, op.op_name, op.args, cu) for op in parsed[0:first_unsupported]]
        start_of_unparsed = parsed[first_unsupported].offset
        lines.append("<decoding error> " + " ".join("%02x" % b for b in expr[start_of_unparsed:]))
    return ", ".join(lines)

def _desc_datatype(attr, die):
    """Oy vey
    """
    return _desc_ref(attr, die, describe_cpp_datatype(die))

def _get_origin_name(die):
    func_die = die.get_DIE_from_attribute('DW_AT_abstract_origin')
    name = _safe_DIE_linkage_name(func_die, '')
    if not name:
        if 'DW_AT_specification' in func_die.attributes:
            name = _DIE_linkage_name(func_die.get_DIE_from_attribute('DW_AT_specification'))
        elif 'DW_AT_abstract_origin' in func_die.attributes:
            return _get_origin_name(func_die)    
    return name

def _desc_origin(attr, die):
    return _desc_ref(attr, die, _get_origin_name(die))

def _desc_spec(attr, die):
    return _desc_ref(attr, die,
        _DIE_linkage_name(die.get_DIE_from_attribute('DW_AT_specification')))

def _desc_value(attr, die):
    return str(attr.value)

ATTR_DESCRIPTIONS = dict(
    DW_AT_language=lambda attr, die: _desc_enum(attr, ENUM_DW_LANG),
    DW_AT_encoding=lambda attr, die: _desc_enum(attr, ENUM_DW_ATE),
    DW_AT_accessibility=lambda attr, die: _desc_enum(attr, ENUM_DW_ACCESS),
    DW_AT_inline=lambda attr, die: _desc_enum(attr, ENUM_DW_INL),
    DW_AT_calling_convention=lambda attr, die: _desc_enum(attr, ENUM_DW_CC),
    DW_AT_decl_file=_desc_decl_file,
    DW_AT_decl_line=_desc_value,
    DW_AT_ranges=_desc_ranges,
    DW_AT_location=_desc_locations,
    DW_AT_data_member_location=lambda attr, die: _desc_data(attr, die) if attr.form.startswith('DW_FORM_data') else _desc_locations(attr, die),
    DW_AT_frame_base=_desc_locations,
    DW_AT_type=_desc_datatype,
    DW_AT_call_line=_desc_value,
    DW_AT_call_file=_desc_decl_file,
    DW_AT_abstract_origin=_desc_origin,
    DW_AT_specification=_desc_spec
)

class ReadElf(object):
    """ dump_xxx is used to dump the respective section.
    Mimics the output of dwarfdump with --verbose
    """
    def __init__(self, filename, file, output):
        """ file:
                stream object with the ELF file to read

            output:
                output stream to write to
        """
        self.elffile = ELFFile(file)
        self.output = output
        self._dwarfinfo = self.elffile.get_dwarf_info()
        arches = {"EM_386": "i386", "EM_X86_64": "x86-64", "EM_ARM": "littlearm", "EM_AARCH64": "littleaarch64"}
        arch = arches[self.elffile['e_machine']]
        bits = self.elffile.elfclass
        self._emitline("%s:	file format elf%d-%s" % (filename, bits, arch))

    def _emit(self, s=''):
        """ Emit an object to output
        """
        self.output.write(str(s))

    def _emitline(self, s=''):
        """ Emit an object to output, followed by a newline
        """
        self.output.write(str(s).rstrip() + '\n')

    def dump_info(self):
        # TODO: DWARF64 will cause discrepancies in hex offset sizes
        self._emitline(".debug_info contents:")
        for cu in self._dwarfinfo.iter_CUs():
            if cu.header.version >= 5:
                unit_type_str = " unit_type = %s," % cu.header.unit_type
            else:
                unit_type_str = ''

            self._emitline("0x%08x: Compile Unit: length = 0x%08x, format = DWARF%d, version = 0x%04x,%s abbr_offset = 0x%04x, addr_size = 0x%02x (next unit at 0x%08x)" %(
                cu.cu_offset,
                cu.header.unit_length,
                cu.structs.dwarf_format,
                cu.header.version,
                unit_type_str,
                cu.header.debug_abbrev_offset,
                cu.header.address_size,
                cu.cu_offset + (4 if cu.structs.dwarf_format == 32 else 12) + cu.header.unit_length))
            self._emitline()
            parent = cu.get_top_DIE()
            for die in cu.iter_DIEs():
                if die.get_parent() == parent:
                    parent = die
                if not die.is_null(): 
                    self._emitline("0x%08x: %s [%d] %s %s" % (
                        die.offset,
                        die.tag,
                        die.abbrev_code,
                        '*' if die.has_children else '',
                        '(0x%08x)' % die.get_parent().offset if die.get_parent() is not None else ''))
                    for attr_name in die.attributes:
                        attr = die.attributes[attr_name]
                        self._emitline("              %s [%s]	(%s)" % (attr_name, attr.form, self.describe_attr_value(die, attr)))
                else:
                    self._emitline("0x%08x: NULL" % (die.offset,))
                    parent = die.get_parent()
                self._emitline()

    def describe_attr_value(self, die, attr):
        """This describes the attribute value in the way that's compatible 
        with llvm_dwarfdump. Somewhat duplicates the work of describe_attr_value() in descriptions
        """
        if attr.name in ATTR_DESCRIPTIONS:
            return ATTR_DESCRIPTIONS[attr.name](attr, die)
        elif attr.form in FORM_DESCRIPTIONS:
            return FORM_DESCRIPTIONS[attr.form](attr, die)
        else:
            return str(attr.value)

    def dump_loc(self):
        pass

    def dump_loclists(self):
        pass

    def dump_ranges(self):
        pass

    def dump_v4_rangelist(self, rangelist, cu_map):
        cu = cu_map[rangelist[0].entry_offset]
        addr_str_len = cu.header.address_size*2
        base_ip = _get_cu_base(cu)
        for entry in rangelist:
            if isinstance(entry, RangeEntry):
                self._emitline("[0x%0*x, 0x%0*x)" % (
                    addr_str_len,
                    (0 if entry.is_absolute else base_ip) + entry.begin_offset,
                    addr_str_len,
                    (0 if entry.is_absolute else base_ip) + entry.end_offset))
            elif isinstance(entry, elftools.dwarf.ranges.BaseAddressEntry):
                base_ip = entry.base_address
            else:
                raise NotImplementedError("Unknown object in a range list")    

    def dump_rnglists(self):
        self._emitline(".debug_rnglists contents:")
        ranges_sec = self._dwarfinfo.range_lists()
        if ranges_sec.version < 5:
            return

        cu_map = {die.attributes['DW_AT_ranges'].value : cu # Dict from range offset to home CU
            for cu in self._dwarfinfo.iter_CUs()
            for die in cu.iter_DIEs()
            if 'DW_AT_ranges' in die.attributes}

        for cu in ranges_sec.iter_CUs():
            self._emitline("0x%08x: range list header: length = 0x%08x, format = DWARF%d, version = 0x%04x, addr_size = 0x%02x, seg_size = 0x%02x, offset_entry_count = 0x%08x" % (
                cu.cu_offset,
                cu.unit_length,
                64 if cu.is64 else 32,
                cu.version,
                cu.address_size,
                cu.segment_selector_size,
                cu.offset_count))
            self._emitline("ranges:")
            if cu.offset_count > 0:
                rangelists = [ranges_sec.get_range_list_at_offset_ex(offset) for offset in cu.offsets]
            else:
                rangelists = list(ranges_sec.iter_CU_range_lists_ex(cu))
            # We have to parse it completely before dumping, because dwarfdump aligns columns,
            # no way to do that without some lookahead
            max_type_len = max(len(entry.entry_type) for rangelist in rangelists for entry in rangelist)
            for rangelist in rangelists:
                self.dump_v5_rangelist(rangelist, cu_map, max_type_len)

    def dump_v5_rangelist(self, rangelist, cu_map, max_type_len):
        cu = cu_map[rangelist[0].entry_offset]
        addr_str_len = cu.header.address_size*2
        base_ip = _get_cu_base(cu)        
        for entry in rangelist:
            type = entry.entry_type
            self._emit("0x%08x: [%s]:  " % (entry.entry_offset, type.ljust(max_type_len)))
            if type == 'DW_RLE_base_address':
                base_ip = entry.address
                self._emitline("0x%0*x" % (addr_str_len, base_ip))
            elif type == 'DW_RLE_offset_pair':
                self._emitline("0x%0*x, 0x%0*x => [0x%0*x, 0x%0*x)" % (
                    addr_str_len, entry.start_offset,
                    addr_str_len, entry.end_offset,
                    addr_str_len, entry.start_offset + base_ip,
                    addr_str_len, entry.end_offset + base_ip))
            elif type == 'DW_RLE_start_length':
                self._emitline("0x%0*x, 0x%0*x => [0x%0*x, 0x%0*x)" % (
                    addr_str_len, entry.start_address,
                    addr_str_len, entry.length,
                    addr_str_len, entry.start_address,
                    addr_str_len, entry.start_address + entry.length))
            elif type == 'DW_RLE_start_end':
                self._emitline("0x%0*x, 0x%0*x => [0x%0*x, 0x%0*x)" % (
                    addr_str_len, entry.start_address,
                    addr_str_len, entry.end_address,
                    addr_str_len, entry.start_address,
                    addr_str_len, entry.end_address))
            else:
                raise NotImplementedError()
        last = rangelist[-1]
        self._emitline("0x%08x: [DW_RLE_end_of_list ]" % (last.entry_offset + last.entry_length,))

SCRIPT_DESCRIPTION = 'Display information about the contents of ELF format files'
VERSION_STRING = '%%(prog)s: based on pyelftools %s' % __version__

def main(stream=None):
    # parse the command-line arguments and invoke ReadElf
    argparser = argparse.ArgumentParser(
            usage='usage: %(prog)s [options] <elf-file>',
            description=SCRIPT_DESCRIPTION,
            add_help=False,
            prog='readelf.py')
    argparser.add_argument('file',
            nargs='?', default=None,
            help='ELF file to parse')
    argparser.add_argument('-H', '--help',
            action='store_true', dest='help',
            help='Display this information')
    argparser.add_argument('--verbose',
            action='store_true', dest='verbose',
            help=('For compatibility with dwarfdump. Non-verbose mode is not implemented.'))

    # Section dumpers
    sections = ('info', 'loclists', 'rnglists') # 'loc', 'ranges' not implemented yet
    for section in sections:
        argparser.add_argument('--debug-%s' % section,
            action='store_true', dest=section,
            help=('Display the contents of DWARF debug_%s section.' % section))

    args = argparser.parse_args()

    if args.help or not args.file:
        argparser.print_help()
        sys.exit(0)

    # A compatibility hack on top of a compatibility hack :(
    del ENUM_DW_TAG["DW_TAG_template_type_param"]
    del ENUM_DW_TAG["DW_TAG_template_value_param"]
    ENUM_DW_TAG['DW_TAG_template_type_parameter'] = 0x2f
    ENUM_DW_TAG['DW_TAG_template_value_parameter'] = 0x30

    with open(args.file, 'rb') as file:
        try:
            readelf = ReadElf(args.file, file, stream or sys.stdout)
            if args.info:
                readelf.dump_info()
            if args.loclists:
                readelf.dump_loclists()
            if args.rnglists:
                readelf.dump_rnglists()
            #if args.loc:
            #    readelf.dump_loc()
            #if args.ranges:
            #    readelf.dump_ranges()
        except ELFError as ex:
            sys.stdout.flush()
            sys.stderr.write('ELF error: %s\n' % ex)
            if args.show_traceback:
                traceback.print_exc()
            sys.exit(1)

#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
    #profile_main()
