#-------------------------------------------------------------------------------
# elftools: dwarf/lineprogram.py
#
# DWARF line number program
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from ..common.utils import struct_parse
from .constants import *


class LineState(object):
    """ Represents a line program state (or a "row" in the matrix
        describing debug location information for addresses).
        The instance variables of this class are the "state machine registers"
        described in section 6.2.2 of DWARFv3
    """
    def __init__(self, default_is_stmt):
        self.address = 0
        self.file = 1
        self.line = 1
        self.column = 0
        self.is_stmt = default_is_stmt
        self.basic_block = False
        self.end_sequence = False
        self.prologue_end = False
        self.epilogue_begin = False
        self.isa = 0


class LineProgram(object):
    """ Builds a "line table", which is essentially the matrix described
        in section 6.2 of DWARFv3. It's a list of LineState objects,
        sorted by increasing address, so it can be used to obtain the
        state information for each address.
    """
    def __init__(self, header, dwarfinfo, structs,
                 program_start_offset, program_end_offset):
        """ 
            header:
                The header of this line program. Note: LineProgram may modify
                its header by appending file entries if DW_LNE_define_file
                instructions are encountered.

            dwarfinfo:
                The DWARFInfo context object which created this one

            structs:
                A DWARFStructs instance suitable for this line program

            program_{start|end}_offset:
                Offset in the debug_line section stream where this program
                starts, and where it ends. The actual range includes start
                but not end: [start, end - 1]
        """
        self.dwarfinfo = dwarfinfo
        self.stream = self.dwarfinfo.debug_line_sec.stream
        self.header = header
        self.structs = structs
        self.program_start_offset = program_start_offset
        self.program_end_offset = program_end_offset

        self._line_table = None

    def get_line_table(self):
        """ Get the decoded line table for this line program
        """
        if self._line_table is None:
            self._line_table = self._decode_line_program()
        return self._line_table

    #------ PRIVATE ------#
    
    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def _decode_line_program(self):
        linetable = []
        state = LineState(self.header['default_is_stmt'])

        def add_state_to_table():
            # Used by instructions that have to add the current state to the
            # line table. After adding, some state registers have to be
            # cleared.
            linetable.append(state)
            state.basic_block = False
            state.prologue_end = False
            state.epilogue_begin = False

        offset = self.program_start_offset
        while offset < self.program_end_offset:
            opcode = struct_parse(
                self.structs.Dwarf_uint8, 
                self.stream,
                offset)

            # As an exercise in avoiding premature optimization, if...elif
            # chains are used here for standard and extended opcodes instead
            # of dispatch tables. This keeps the code much cleaner. Besides,
            # the majority of instructions in a typical program are special
            # opcodes anyway.
            if opcode >= self.header['opcode_base']:
                # Special opcode (follow the recipe in 6.2.5.1)
                adjusted_opcode = opcode - self['opcode_base']
                state.address += ((adjusted_opcode / self['line_range']) *
                                  self['minimum_instruction_length'])
                self.line += (self['line_base'] + 
                              adjusted_opcode % self['line_range'])
                add_state_to_table()
            elif opcode == 0:
                # Extended opcode: start with a zero byte, followed by
                # instruction size and the instruction itself.
                inst_len = struct_parse(self.Dwarf_uleb128, self.stream)
                ex_opcode = struct_parse(self.Dwarf_uint8, self.stream)

                if ex_opcode == DW_LNE_end_sequence:
                    state.end_sequence = True
                    add_state_to_table(state)
                    state = LineState() # reset state
                elif ex_opcode == DW_LNE_set_address:
                    operand = struct_parse(self.Dwarf_target_addr, self.stream)
                    state.address = operand
                elif ex_opcode == DW_LNE_define_file:
                    operand = struct_parse(self.Dwarf_lineprog_file_entry,
                                           self.stream)
                    self['file_entry'].append(operand)
            else: # 0 < opcode < opcode_base
                # Standard opcode
                if opcode == DW_LNS_copy:
                    add_state_to_table()
                elif opcode == DW_LNS_advance_pc:
                    operand = struct_parse(self.Dwarf_uleb128, self.stream)
                    state.address += (
                        operand * self.header['minimum_instruction_length'])
                elif opcode == DW_LNS_advance_line:
                    operand = struct_parse(self.Dwarf_sleb128, self.stream)
                    state.line += operand
                elif opcode == DW_LNS_set_file:
                    operand = struct_parse(self.Dwarf_sleb128, self.stream)
                    state.file = operand
                elif opcode == DW_LNS_set_column:
                    operand = struct_parse(self.Dwarf_uleb128, self.stream)
                    state.column = operand
                elif opcode == DW_LNS_negate_stmt:
                    state.is_stmt = not state.is_stmt
                elif opcode == DW_LNS_set_basic_block:
                    state.basic_block = True
                elif opcode == DW_LNS_const_add_pc:
                    adjusted_opcode = 255 - self['opcode_base']
                    state.address += ((adjusted_opcode / self['line_range']) *
                                      self['minimum_instruction_length'])
                elif opcode == DW_LNS_fixed_advance_pc:
                    operand = struct_parse(self.Dwarf_uint16, self.stream)
                    state.address += operand
                elif opcode == DW_LNS_set_prologue_end:
                    state.prologue_end = True
                elif opcode == DW_LNS_set_epilogue_begin:
                    state.epilogue_begin = True
                elif opcode == DW_LNS_set_isa:
                    operand = struct_parse(self.Dwarf_uleb128, self.stream)
                    state.isa = operand
                else:
                    dwarf_assert(False, 'Invalid standard line program opcode: %s' % (
                        opcode,))

