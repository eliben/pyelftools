'''
read function information from symbol information
'''

def readFuncsFromSyms(binary):

    result = set()
    global BLACKLIST_ADDRS

    with open(binary, 'rb') as open_file:
        elffile = ELFFile(open_file)
        symsec = elffile.get_section_by_name('.symtab')
        if not symsec:
            print("binary file %s does not contains .symtab section!" % (binary))
            return result 
        for sym in symsec.iter_symbols():
            if 'STT_FUNC' == sym['st_info']['type'] and sym['st_value'] != 0x0 and \
                isInTextSection(sym['st_value']):
                #logging.debug("[Find Func Start From .symtab]: address 0x%x" % (sym['st_value']))
                result.add(sym['st_value'])
                # if sym.name in LINKER_ADDED_FUNCS:
                #     BLACKLIST_ADDRS.add(sym['st_value'])
    return result

if __name__ == "__name__":
    print(readFuncsFromSyms("~/linux-master/lib/earlycpio.o"))