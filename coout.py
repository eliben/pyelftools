from difflib import SequenceMatcher
import platform

with open('R:\\pyelftools\\re_n_2.txt') as f:
    s1 = f.read() 
with open('R:\\pyelftools\\re_p_2.txt') as f:
    s2 = f.read()

def prepare_lines(s):
    return [line for line in s.lower().splitlines() if line.strip() != '']

lines1 = prepare_lines(s1)
lines2 = prepare_lines(s2)

flag_after_symtable = False

for i in range(len(lines1)):
    if 'symbol table' in lines1[i]:
        flag_after_symtable = True

    # Compare ignoring whitespace
    lines1_parts = lines1[i].split()
    lines2_parts = lines2[i].split()

    if ''.join(lines1_parts) != ''.join(lines2_parts):
        ok = False

        try:
            # Ignore difference in precision of hex representation in the
            # last part (i.e. 008f3b vs 8f3b)
            if (''.join(lines1_parts[:-1]) == ''.join(lines2_parts[:-1]) and
                int(lines1_parts[-1], 16) == int(lines2_parts[-1], 16)):
                ok = True
        except ValueError:
            pass

        sm = SequenceMatcher()
        sm.set_seqs(lines1[i], lines2[i])
        changes = sm.get_opcodes()
        if flag_after_symtable:
            # Detect readelf's adding @ with lib and version after
            # symbol name.
            if (    len(changes) == 2 and changes[1][0] == 'delete' and
                    lines1[i][changes[1][1]] == '@'):
                ok = True
        elif 'at_const_value' in lines1[i]:
            # On 32-bit machines, readelf doesn't correctly represent
            # some boundary LEB128 numbers
            val = lines2_parts[-1]
            num2 = int(val, 16 if val.startswith('0x') else 10)
            if num2 <= -2**31 and '32' in platform.architecture()[0]:
                ok = True
        elif 'os/abi' in lines1[i]:
            if 'unix - gnu' in lines1[i] and 'unix - linux' in lines2[i]:
                ok = True
        elif (  'unknown at value' in lines1[i] and
                'dw_at_apple' in lines2[i]):
            ok = True
        else:
            for s in ('t (tls)', 'l (large)'):
                if s in lines1[i] or s in lines2[i]:
                    ok = True
                    break
        if not ok:
            errmsg = 'Mismatch on line #%s:\n>>%s<<\n>>%s<<\n (%r)' % (
                i, lines1[i], lines2[i], changes)
            exit(1)

