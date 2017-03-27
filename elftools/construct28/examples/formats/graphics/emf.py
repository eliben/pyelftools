"""
Enhanced Meta File
"""
from construct import *


record_type = "record_type" / Enum(Int32ul,
    ABORTPATH = 68,
    ANGLEARC = 41,
    ARC = 45,
    ARCTO = 55,
    BEGINPATH = 59,
    BITBLT = 76,
    CHORD = 46,
    CLOSEFIGURE = 61,
    CREATEBRUSHINDIRECT = 39,
    CREATEDIBPATTERNBRUSHPT = 94,
    CREATEMONOBRUSH = 93,
    CREATEPALETTE = 49,
    CREATEPEN = 38,
    DELETEOBJECT = 40,
    ELLIPSE = 42,
    ENDPATH = 60,
    EOF = 14,
    EXCLUDECLIPRECT = 29,
    EXTCREATEFONTINDIRECTW = 82,
    EXTCREATEPEN = 95,
    EXTFLOODFILL = 53,
    EXTSELECTCLIPRGN = 75,
    EXTTEXTOUTA = 83,
    EXTTEXTOUTW = 84,
    FILLPATH = 62,
    FILLRGN = 71,
    FLATTENPATH = 65,
    FRAMERGN = 72,
    GDICOMMENT = 70,
    HEADER = 1,
    INTERSECTCLIPRECT = 30,
    INVERTRGN = 73,
    LINETO = 54,
    MASKBLT = 78,
    MODIFYWORLDTRANSFORM = 36,
    MOVETOEX = 27,
    OFFSETCLIPRGN = 26,
    PAINTRGN = 74,
    PIE = 47,
    PLGBLT = 79,
    POLYBEZIER = 2,
    POLYBEZIER16 = 85,
    POLYBEZIERTO = 5,
    POLYBEZIERTO16 = 88,
    POLYDRAW = 56,
    POLYDRAW16 = 92,
    POLYGON = 3,
    POLYGON16 = 86,
    POLYLINE = 4,
    POLYLINE16 = 87,
    POLYLINETO = 6,
    POLYLINETO16 = 89,
    POLYPOLYGON = 8,
    POLYPOLYGON16 = 91,
    POLYPOLYLINE = 7,
    POLYPOLYLINE16 = 90,
    POLYTEXTOUTA = 96,
    POLYTEXTOUTW = 97,
    REALIZEPALETTE = 52,
    RECTANGLE = 43,
    RESIZEPALETTE = 51,
    RESTOREDC = 34,
    ROUNDRECT = 44,
    SAVEDC = 33,
    SCALEVIEWPORTEXTEX = 31,
    SCALEWINDOWEXTEX = 32,
    SELECTCLIPPATH = 67,
    SELECTOBJECT = 37,
    SELECTPALETTE = 48,
    SETARCDIRECTION = 57,
    SETBKCOLOR = 25,
    SETBKMODE = 18,
    SETBRUSHORGEX = 13,
    SETCOLORADJUSTMENT = 23,
    SETDIBITSTODEVICE = 80,
    SETMAPMODE = 17,
    SETMAPPERFLAGS = 16,
    SETMETARGN = 28,
    SETMITERLIMIT = 58,
    SETPALETTEENTRIES = 50,
    SETPIXELV = 15,
    SETPOLYFILLMODE = 19,
    SETROP2 = 20,
    SETSTRETCHBLTMODE = 21,
    SETTEXTALIGN = 22,
    SETTEXTCOLOR = 24,
    SETVIEWPORTEXTEX = 11,
    SETVIEWPORTORGEX = 12,
    SETWINDOWEXTEX = 9,
    SETWINDOWORGEX = 10,
    SETWORLDTRANSFORM = 35,
    STRETCHBLT = 77,
    STRETCHDIBITS = 81,
    STROKEANDFILLPATH = 63,
    STROKEPATH = 64,
    WIDENPATH = 66,
    default=Pass
)

generic_record = "records" / Struct(
    record_type,
    "record_size" / Int32ul,      # Size of the record in bytes 
    "params" / RawCopy(Array((this.record_size - 8) // 4, Int32ul)),
)

header_record = "header_record" / Struct(
    Const(record_type, "HEADER"),
    "record_size" / Int32ul,              # Size of the record in bytes 
    "bounds_left" / Int32sl,              # Left inclusive bounds 
    "bounds_right" / Int32sl,             # Right inclusive bounds 
    "bounds_top" / Int32sl,               # Top inclusive bounds 
    "bounds_bottom" / Int32sl,            # Bottom inclusive bounds 
    "frame_left" / Int32sl,               # Left side of inclusive picture frame 
    "frame_right" / Int32sl,              # Right side of inclusive picture frame 
    "frame_top" / Int32sl,                # Top side of inclusive picture frame 
    "frame_bottom" / Int32sl,             # Bottom side of inclusive picture frame 
    "signature" / Const(Int32ul, 0x464D4520),
    "version" / Int32ul,                  # Version of the metafile 
    "size" / Int32ul,                     # Size of the metafile in bytes 
    "num_of_records" / Int32ul,           # Number of records in the metafile 
    "num_of_handles" / Int16ul,           # Number of handles in the handle table 
    Padding(2),
    "description_size" / Int32ul,         # Size of description string in WORDs 
    "description_offset" / Int32ul,       # Offset of description string in metafile 
    "num_of_palette_entries" / Int32ul,   # Number of color palette entries 
    "device_width_pixels" / Int32sl,      # Width of reference device in pixels 
    "device_height_pixels" / Int32sl,     # Height of reference device in pixels 
    "device_width_mm" / Int32sl,          # Width of reference device in millimeters
    "device_height_mm" / Int32sl,         # Height of reference device in millimeters
    
    "description" / Pointer(this.description_offset,
        String(this.description_size * 2),
    ),
    
    # padding up to end of record
    Padding(this.record_size - 88),
)

emf_file = "emf_file" / Struct(
    header_record,
    Array(this.header_record.num_of_records - 1, generic_record),
)


