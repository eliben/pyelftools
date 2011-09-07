def int_to_bin(number, width = 32):
    if number < 0:
        number += 1 << width
    i = width - 1
    bits = ["\x00"] * width
    while number and i >= 0:
        bits[i] = "\x00\x01"[number & 1]
        number >>= 1
        i -= 1
    return "".join(bits)

_bit_values = {"\x00" : 0, "\x01" : 1, "0" : 0, "1" : 1}
def bin_to_int(bits, signed = False):
    number = 0
    bias = 0
    if signed and _bit_values[bits[0]] == 1:
        bits = bits[1:]
        bias = 1 << len(bits)
    for b in bits:
        number <<= 1
        number |= _bit_values[b]
    return number - bias

def swap_bytes(bits, bytesize = 8):
    i = 0
    l = len(bits)
    output = [""] * ((l // bytesize) + 1)
    j = len(output) - 1
    while i < l:
        output[j] = bits[i : i + bytesize]
        i += bytesize
        j -= 1
    return "".join(output)

_char_to_bin = {}
_bin_to_char = {}
for i in range(256):
    ch = chr(i)
    bin = int_to_bin(i, 8)
    _char_to_bin[ch] = bin
    _bin_to_char[bin] = ch
    _bin_to_char[bin] = ch

def encode_bin(data):
    return "".join(_char_to_bin[ch] for ch in data)

def decode_bin(data):
    assert len(data) & 7 == 0, "data length must be a multiple of 8"
    i = 0
    j = 0
    l = len(data) // 8
    chars = [""] * l
    while j < l:
        chars[j] = _bin_to_char[data[i:i+8]]
        i += 8
        j += 1
    return "".join(chars)




