"""
Windows/OS2 Bitmap (BMP) this could have been a perfect show-case file format, but they had to make it ugly (all sorts of alignments)
"""
from construct import *


#===============================================================================
# pixels: uncompressed
#===============================================================================
def UncompressedRows(subcon, align_to_byte = False):
    """argh! lines must be aligned to a 4-byte boundary, and bit-pixel
    lines must be aligned to full bytes..."""
    if align_to_byte:
        line_pixels = Bitwise(Aligned(8, Array(this.width, subcon)))
    else:
        line_pixels = Array(this.width, subcon)
    return Array(this.height, Aligned(4, line_pixels))

uncompressed_pixels = "uncompressed" / Switch(this.bpp,
    {
        1 : UncompressedRows(Bit, align_to_byte = True), # index
        4 : UncompressedRows(Nibble, align_to_byte = True), # index
        8 : UncompressedRows(Byte),  # index
        24 : UncompressedRows(Byte[3]),  # rgb
    }
)

#===============================================================================
# pixels: Run Length Encoding (RLE) 8 bit
#===============================================================================
class RunLengthAdapter(Adapter):
    def _encode(self, obj):
        return len(obj), obj[0]
    def _decode(self, obj):
        length, value = obj
        return [value] * length

rle8pixel = "rle8pixel" / RunLengthAdapter(Byte >> Byte)

#===============================================================================
# file structure
#===============================================================================
bitmap_file = "bitmap_file" / Struct(
    # header
    "signature" / Const(b"BM"),
    "file_size" / Int32ul,
    Padding(4),
    "data_offset" / Int32ul,
    "header_size" / Int32ul,
    # Enum(Alias("version", "header_size"),
    "version" / Enum(Computed(this.header_size),
        v2 = 12,
        v3 = 40,
        v4 = 108,
        default=Pass
    ),
    "width" / Int32ul,
    "height" / Int32ul,
    "number_of_pixels" / Computed(this.width * this.height),
    "planes" / Int16ul,
    "bpp" / Int16ul, # bits per pixel
    "compression" / Enum(Int32ul,
        Uncompressed = 0,
        RLE8 = 1,
        RLE4 = 2,
        Bitfields = 3,
        JPEG = 4,
        PNG = 5,
    ),
    "image_data_size" / Int32ul, # in bytes
    "horizontal_dpi" / Int32ul,
    "vertical_dpi" / Int32ul,
    "colors_used" / Int32ul,
    "important_colors" / Int32ul,

    # palette (24 bit has no palette)
    "palette" / Array(lambda ctx: 2**ctx.bpp if ctx.bpp <= 8 else 0,
        Struct(
            "rgb" / Byte[3],
            Padding(1),
        )
    ),

    # pixels
    "pixels" / Pointer(this.data_offset,
        Switch(this.compression,
            {
                "Uncompressed" : uncompressed_pixels,
            },
        ),
    ),
)

