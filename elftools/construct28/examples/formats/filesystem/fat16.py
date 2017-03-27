"""
fat.py; ad-hoc fat16 reader
   by Bram Westerbaan <bram@westerbaan.name> 

references:
  http://en.wikipedia.org/wiki/File_Allocation_Table
  http://www.ecma-international.org/publications/standards/Ecma-107.htm

example:
   with open("/dev/sdc1", "rb") as file:
       fs = FatFs(file)
       for rootdir in fs:
           print rootdir
"""
import numbers
from io import BytesIO, BufferedReader

from construct import Struct, Byte, Bytes, ULInt16, ULInt32, Enum, Array, Padding, Embed, Pass, BitStruct, Flag, Const


def Fat16Header(name):
    return Struct(name,
            Bytes("jumpInstruction", 3),
            Bytes("creatingSystemId", 8),
            ULInt16("sectorSize"),
            Byte("sectorsPerCluster"),
            ULInt16("reservedSectorCount"),
            Byte("fatCount"),
            ULInt16("rootdirEntryCount"),
            ULInt16("sectorCount_small"),
            Byte("mediaId"), 
            ULInt16("sectorsPerFat"),
            ULInt16("sectorsPerTrack"),
            ULInt16("sideCount"),
            ULInt32("hiddenSectorCount"),
            ULInt32("sectorCount_large"),
            Byte("physicalDriveNumber"),
            Byte("currentHead"),
            Byte("extendedBootSignature"),
            Bytes("volumeId", 4),
            Bytes("volumeLabel", 11),
            Const(Bytes("fsType", 8), "FAT16   "),
            Bytes("bootCode", 448),
            Const(Bytes("bootSectorSignature", 2), "\x55\xaa"))

def BootSector(name):
    header = Fat16Header("header")
    return  Struct(name,
            Embed(header),
            Padding(lambda ctx: ctx.sectorSize - header.sizeof()))

def FatEntry(name):
    return Enum(ULInt16(name),
            free_cluster = 0x0000,
            bad_cluster = 0xfff7,
            last_cluster = 0xffff,
            _default_ = Pass)

def DirEntry(name):
    return Struct(name,
            Bytes("name", 8),
            Bytes("extension", 3),
            BitStruct("attributes",
                Flag("unused"),
                Flag("device"),
                Flag("archive"),
                Flag("subDirectory"),
                Flag("volumeLabel"),
                Flag("system"),
                Flag("hidden"),
                Flag("readonly")),
            # reserved
            Padding(10),
            ULInt16("timeRecorded"),
            ULInt16("dateRecorded"),
            ULInt16("firstCluster"),
            ULInt32("fileSize"))

def PreDataRegion(name):
    rde = DirEntry("rootdirs")
    fe = FatEntry("fats")
    return Struct(name,
            Embed(BootSector("bootSector")),
            # the remaining reserved sectors
            Padding(lambda ctx: (ctx.reservedSectorCount - 1)
                * ctx.sectorSize),
            # file allocation tables
            Array(lambda ctx: (ctx.fatCount), 
                Array(lambda ctx: ctx.sectorsPerFat * 
                    ctx.sectorSize / fe.sizeof(), fe)),
            # root directories
            Array(lambda ctx: (ctx.rootdirEntryCount*rde.sizeof()) 
                / ctx.sectorSize, rde))


class File(object):
    def __init__(self, dirEntry, fs):
        self.fs = fs
        self.dirEntry = dirEntry

    @classmethod
    def fromDirEntry(cls, dirEntry, fs):
        if dirEntry.name[0] in "\x00\xe5\x2e":
            return None
        a = dirEntry.attributes
        #Long file name directory entry
        if a.volumeLabel and a.system and a.hidden and a.readonly:
            return None
        if a.subDirectory:
            return Directory(dirEntry, fs)
        return File(dirEntry, fs)

    @classmethod
    def fromDirEntries(cls, dirEntries, fs):
        return filter(None, [cls.fromDirEntry(de, fs) 
            for de in dirEntries])

    def toStream(self, stream):
        self.fs.fileToStream(self.dirEntry.firstCluster, stream)
    
    @property
    def name(self):
        return "%s.%s" %  (self.dirEntry.name.rstrip(),
                self.dirEntry.extension)
    
    def __str__(self):
        return "&%s %s" % (self.dirEntry.firstCluster, self.name)


class Directory(File):
    def __init__(self, dirEntry, fs, children=None):
        super(Directory, self).__init__(dirEntry, fs)
        self.children = children
        if not self.children:
            self.children = File.fromDirEntries(\
                    self.fs.getDirEntries(\
                    self.dirEntry.firstCluster), fs)
    
    @property
    def name(self):
        return self.dirEntry.name.rstrip()

    def __str__(self):
        return "&%s %s/" % (self.dirEntry.firstCluster, self.name)

    def __getitem__(self, name):
        for file in self.children:
            if file.name == name:
                return file
    
    def __iter__(self):
        return iter(self.children)


class FatFs(Directory):
    def __init__(self, stream):
        self.stream = stream
        self.pdr = PreDataRegion("pdr").parse_stream(stream)
        super(FatFs, self).__init__(dirEntry = None, 
                fs = self, children = File.fromDirEntries(
                        self.pdr.rootdirs, self))

    def fileToStream(self, clidx, stream):
        for clidx in self.getLinkedClusters(clidx):
            self.clusterToStream(clidx, stream)

    def clusterToStream(self, clidx, stream):
        start, todo = self.getClusterSlice(clidx)
        self.stream.seek(start)
        while todo > 0:
            read = self.stream.read(todo)
            if not len(read):
                print("failed to read %s bytes at %s" % (todo, self.stream.tell()))
                raise EOFError()
            todo -= len(read)
            stream.write(read)

    def getClusterSlice(self, clidx):
        startSector = self.pdr.reservedSectorCount \
                + self.pdr.fatCount * self.pdr.sectorsPerFat \
                + (self.pdr.rootdirEntryCount * 32) \
                    / self.pdr.sectorSize \
                + (clidx-2) * self.pdr.sectorsPerCluster
        start = startSector * self.pdr.sectorSize
        length = self.pdr.sectorSize * self.pdr.sectorsPerCluster
        return (start, length)

    def getLinkedClusters(self, clidx):
        res = []
        while clidx != "last_cluster":
            if not isinstance(clidx, numbers.Real):
                print(clidx)
                assert False
            assert 2 <= clidx <= 0xffef
            res.append(clidx)
            clidx = self.getNextCluster(clidx)
            assert clidx not in res
        return res

    def getNextCluster(self, clidx):
        ress = set([fat[clidx] for fat in self.pdr.fats])
        if len(ress)==1:
            return ress.pop()
        print("inconsistencie between FATs:  %s points to" % clidx)
        for i,fat in enumerate(self.pdr.fats):
            print("\t%s according to fat #%s" % (fat[clidx], i))
        res = ress.pop()
        print ("assuming %s" % res)
        return res
    
    def getDirEntries(self, clidx):
        try:
            for de in self._getDirEntries(clidx):
                yield de
        except IOError:
            print("failed to read directory entries at %s" % clidx)

    def _getDirEntries(self, clidx):
        de = DirEntry("dirEntry")
        with BytesIO() as mem:
            self.fileToStream(clidx, mem)
            mem.seek(0)
            with BufferedReader(mem) as reader:
                while reader.peek(1):
                    yield de.parse_stream(reader)
    def __str__(self):
        return "/"

    @property
    def name(self):
        return ""

