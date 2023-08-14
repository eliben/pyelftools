from elftools.common.utils import save_dwarf_section
from elftools.dwarf.dwarf_expr import DWARFExprParser
from elftools.dwarf.locationlists import LocationEntry, LocationExpr, LocationParser
from elftools.elf.elffile import ELFFile
from pathlib import WindowsPath, PosixPath
import os
import posixpath

ops_to_find = set((
    #'DW_OP_entry_value',
    'DW_OP_const_type',
    'DW_OP_deref_type',
    'DW_OP_regval_type',
    #'DW_OP_implicit_pointer',
    'DW_OP_convert'))

def is_block(form):
    return form in ('DW_FORM_block', 'DW_FORM_block1', 'DW_FORM_block2', 'DW_FORM_block4')

def expr_has_ops(expr, ep):
    expr = ep.parse_expr(expr)
    ops = set(op.op_name for op in expr if op.op_name in ops_to_find)
    for evop in expr:
        if evop.op_name == 'DW_OP_entry_value':
            ops = ops.union(set(op.op_name for op in evop.args[0] if op.op_name in ops_to_find))
    return ops

def loc_list_has_ops(ll, ep):
    ops = set()
    for le in ll:
        if isinstance(le, LocationEntry):
            ops = ops.union(expr_has_ops(le.loc_expr, ep))
    return ops

def die_has_ops(die, ep, lp):
    all_ops = set()
    for key in die.attributes:
        attr = die.attributes[key]
        if lp.attribute_has_location(attr, die.cu.header['version']):
            loc = lp.parse_from_attribute(attr, die.cu.header.version, die)
            ops = expr_has_ops(loc.loc_expr, ep) if isinstance(loc, LocationExpr) else loc_list_has_ops(loc, ep)
            all_ops = all_ops.union(ops)
        elif key in ('DW_AT_upper_bound', 'DW_AT_lower_bound') and is_block(attr.form):
            all_ops = all_ops.union(expr_has_ops(attr.value, ep))
    return all_ops

with open('test\\testfiles_for_readelf\\dwarf_v5ops.so.elf', 'rb') as file:
    efile = ELFFile(file)
    di = efile.get_dwarf_info() #eh_frame at 0x2048/8264, 0xb6/182 bytes

    #save_dwarf_section(di.debug_rnglists_sec, "rnglists")
    
    ll = di.location_lists()
    lp = LocationParser(ll)
    funcs = dict()
    for cu in di.iter_CUs():
        ep = DWARFExprParser(cu.structs)
        top_die = cu.get_top_DIE()
        def get_func(die):
            while die.get_parent() != top_die:
                die = die.get_parent()
            return die

        for die in cu.iter_DIEs():
            ops = die_has_ops(die, ep, lp)
            if len(ops):
                func_die = get_func(die)
                func_name = func_die.attributes['DW_AT_name'].value.decode('ASCII') if 'DW_AT_name' in func_die.attributes else "0x%x" % func_die.offset
                if func_name in funcs:
                    funcs[func_name] = funcs[func_name].union(ops)
                else:
                    funcs[func_name] = ops

    for (f, ops) in funcs.items():
        print("%s: %s" % (f, ",".join(ops)))

