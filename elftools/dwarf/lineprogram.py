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
                The header of this line program

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

        offset = self.program_start_offset
        while offset < self.program_end_offset:
            opcode = struct_parse(
                self.structs.Dwarf_uint8, 
                self.stream,
                offset)

            # As an exercise in avoiding premature optimization, if...elif
            # chains are used here for standard and extended opcodes instead
            # of dispatch tables. This keeps the code much cleaner. Besides,
            # the majority of instructions are special opcodes anyway.
            if opcode == 0:
                # Extended opcode: start with a zero byte, followed by
                # instruction size and the instruction itself.
                pass
            elif opcode < self.header['opcode_base']:
                # Standard opcode
                if opcode == DW_LNS_copy:
                    linetable.append(state)
                    state.basic_block = False
                    state.prologue_end = False
                    state.epilogue_begin = False
                elif opcode == DW_LNS_advance_pc:
                    operand = struct_parse(self.Dwarf_uleb128, self.stream)
                    state.address += (
                        operand * self.header['minimum_instruction_length'])
                elif opcode = DW_LNS_advance_line:
                    operand = struct_parse(self.Dwarf_sleb128, self.stream)
                    state.line += operand
                # ZZZ! go on now...
            else:
                # Special opcode
                pass

    def _handle_LNS_copy(self, opcode, state, linetable):
        pass

