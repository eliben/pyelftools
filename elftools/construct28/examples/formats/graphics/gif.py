# Contributed by
# Dany Zatuchna (danzat at gmail)
""" Implementation of the following grammar for the GIF89a file format
<GIF Data Stream> ::=     Header <Logical Screen> <Data>* Trailer

<Logical Screen> ::=      Logical Screen Descriptor [Global Color Table]

<Data> ::=                <Graphic Block>  |
                          <Special-Purpose Block>

<Graphic Block> ::=       [Graphic Control Extension] <Graphic-Rendering Block>

<Graphic-Rendering Block> ::=  <Table-Based Image>  |
                               Plain Text Extension

<Table-Based Image> ::=   Image Descriptor [Local Color Table] Image Data

<Special-Purpose Block> ::=    Application Extension  |
                               Comment Extension
"""
from construct import *


data_sub_block = Struct("data_sub_block",
    ULInt8("size"),
    String("data", lambda ctx: ctx["size"])
)

gif_logical_screen = Struct("logical_screen",
    ULInt16("width"),
    ULInt16("height"),
    BitStruct("flags",
        Bit("global_color_table"),
        BitField("color_resolution", 3),
        Bit("sort_flag"),
        BitField("global_color_table_bpp", 3)
    ),
    ULInt8("bgcolor_index"),
    ULInt8("pixel_aspect_ratio"),
    If(lambda ctx: ctx["flags"]["global_color_table"],
        Array(lambda ctx: 2**(ctx["flags"]["global_color_table_bpp"] + 1),
            Struct("palette",
                ULInt8("R"),
                ULInt8("G"),
                ULInt8("B")
            )
        )
    )
)

gif_header = Struct("gif_header",
    Const("signature", b"GIF"),
    Const("version", b"89a"),
)

application_extension = Struct("application_extension",
    Const(ULInt8("block_size"), 11),
    String("application_identifier", 8),
    String("application_auth_code", 3),
    data_sub_block,
    ULInt8("block_terminator")
)

comment_extension = Struct("comment_extension",
    data_sub_block,
    ULInt8("block_terminator")
)

graphic_control_extension = Struct("graphic_control_extension",
    Const(ULInt8("block_size"), 4),
    BitStruct("flags",
        BitField("reserved", 3),
        BitField("disposal_method", 3),
        Bit("user_input_flag"),
        Bit("transparent_color_flag"),
    ),
    ULInt16("delay"),
    ULInt8("transparent_color_index"),
    ULInt8("block_terminator")
)

plain_text_extension = Struct("plain_text_extension",
    Const(ULInt8("block_size"), 12),
    ULInt16("text_left"),
    ULInt16("text_top"),
    ULInt16("text_width"),
    ULInt16("text_height"),
    ULInt8("cell_width"),
    ULInt8("cell_height"),
    ULInt8("foreground_index"),
    ULInt8("background_index"),
    data_sub_block,
    ULInt8("block_terminator")
)

extension = Struct("extension",
    ULInt8("label"),
    Switch("ext", lambda ctx: ctx["label"], {
        0xFF: application_extension,
        0xFE: comment_extension,
        0xF9: graphic_control_extension,
        0x01: plain_text_extension
    })
)

image_descriptor = Struct("image_descriptor",
    ULInt16("left"),
    ULInt16("top"),
    ULInt16("width"),
    ULInt16("height"),
    BitStruct("flags",
        Bit("local_color_table"),
        Bit("interlace"),
        Bit("sort"),
        BitField("reserved", 2),
        BitField("local_color_table_bpp", 3)
    ),
    If(lambda ctx: ctx["flags"]["local_color_table"],
        Array(lambda ctx: 2**(ctx["flags"]["local_color_table_bpp"] + 1),
            Struct("palette",
                ULInt8("R"),
                ULInt8("G"),
                ULInt8("B")
            )
        )
    ),
    ULInt8("LZW_minimum_code_size"),
    RepeatUntil(lambda obj, ctx: obj.size == 0, data_sub_block)
)

gif_data = Struct("gif_data",
    ULInt8("introducer"),
    Switch("dat", lambda ctx: ctx["introducer"], {
        0x21: extension,
        0x2C: image_descriptor
    })
)

gif_file = Struct("gif_file",
    gif_header,
    gif_logical_screen,
    OptionalGreedyRange(gif_data),
    #Const(ULInt8("trailer"), 0x3B)
)

if __name__ == "__main__":
    f = open("../../../tests/sample.gif", "rb")
    s = f.read()
    f.close()
    print(gif_file.parse(s))
