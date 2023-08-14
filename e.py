import io
from elftools.elf.elffile import ELFFile
from elftools.dwarf.dwarf_expr import DWARFExprParser, DWARFExprOp, DW_OP_opcode2name
from elftools.dwarf.dwarfinfo import DWARFInfo, DebugSectionDescriptor, DwarfConfig

filename ='/Users/valekseyev/Documents/An-3.30.35-y-ARM64-libyarxi.so'
filename = '\\\\sandbox\\seva\\webdata\\clarify\\derived\\An-3.30.35-y-ARM64\\libyarxi.so'
filename = 'samples\\main.elf'
filename = 'E:\\Seva\\Projects\\dwex\\samples\\JiPadLib.dll'
filename = 'fft'
filename = 'temp\\corrupt_sh.elf'


with open(filename, 'rb') as f:
    ef = ELFFile(f)
    pass
    #di = ef.get_dwarf_info()
    #CUs = tuple(di.iter_CUs())
    ##cu = CUs[0] 
    #for cu in CUs:
    #    lp = di.line_program_for_CU(cu)
    #    lp.get_entries()

print("Done")
