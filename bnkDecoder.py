from struct import unpack, calcsize, error
from io import BytesIO
from decoder import Decoder
from os import remove, system

class Entry:
    def __init__(self, stream: BytesIO):
        self.id = unpack('<I', stream.read(4))[0]
        self.offset = unpack('<I', stream.read(4))[0]
        self.size = unpack('<I', stream.read(4))[0]

    def __repr__(self):
        return f"Entry(id={self.id}, offset={self.offset}, size={self.size})"

class STIDEntry:
    def __init__(self, stream: BytesIO):
        self.id = unpack('<I', stream.read(4))[0]
        self.nameLength = unpack('<B', stream.read(1))[0]
        self.name = stream.read(self.nameLength)

    def __repr__(self):
        return f"STIDEntry(id={self.id}, name={self.name})"

class HIRCEntry:
    def __init__(self, stream: BytesIO):
        start = stream.tell()
        self.type = unpack('<B', stream.read(1))[0]
        self.length = unpack('<I', stream.read(4))[0]
        if self.type == 1:
            self.data = stream.read(self.length-4)
        elif self.type == 2:
            self.id = unpack('<I', stream.read(4))[0]
            stream.read(4)  # Skip padding
            self.storageType = unpack('<I', stream.read(4))[0]
            self.audioId = unpack('<I', stream.read(4))[0]
            self.sourceId = unpack('<I', stream.read(4))[0]
            self.soundType = unpack('<B', stream.read(1))[0]
            self.data = stream.read(self.length - 21)  # 21 bytes for the fields read above
        elif self.type == 3:
            self.scope = unpack('<B', stream.read(1))[0]
            self.type = unpack('<B', stream.read(1))[0]
            self.gameObjectID = unpack('<I', stream.read(4))[0]
            stream.read(1)  # Skip padding
            self.parameterCount = unpack('<B', stream.read(1))[0]
            self.parameterTypes = []
            self.parameters = []
            for _ in range(self.parameterCount):
                paramType = unpack('<B', stream.read(1))[0]
                self.parameterTypes.append(paramType)
            for _ in range(self.parameterCount):
                paramValue = unpack('<B', stream.read(1))[0]
                self.parameters.append(paramValue)
            stream.read(self.length-start)
        else:
            stream.seek(self.length, 1)  # Skip unknown type

class BnkDecoder(Decoder):
    def __init__(self, raw_data: bytes, file_path: str = None):
        self.stream = BytesIO(raw_data)
        self.file_path = file_path
        self.magic = self.stream.read(4)
        self.endianness = '<'
        if self.magic != b'BKHD':
            raise ValueError(f"{self.file_path}: Invalid BNK file format. MAGIC: {self.magic}")
    
    def read(self, fmt):
        size = calcsize(fmt)
        data = self.stream.read(size)
        if len(data) < size:
            raise EOFError("Unexpected end of file while reading BNK data.")
        return unpack(f"{self.endianness}{fmt}", data)[0]

    def decompress(self):
        self.stream.seek(0)
        while True:
            try:
                magic = self.stream.read(4)
                sectionLength = self.read('I')
            except EOFError:
                break
            if magic == b'BKHD':
                self.bankVersion = self.read('I')
                self.id = self.read('I')
                padding = self.stream.read(sectionLength - 8)
            elif magic == b'DIDX':
                entryCount = sectionLength // 12
                self.didxEntries:list[Entry] = []
                for _ in range(entryCount):
                    self.didxEntries.append(Entry(self.stream))
            elif magic == b'DATA':
                self.dataEntries:list[bytes] = []
                offPos = self.stream.tell()
                for i in range(len(self.didxEntries)):
                    self.stream.seek(self.didxEntries[i].offset + offPos)
                    data = self.stream.read(self.didxEntries[i].size)
                    self.dataEntries.append(data)
                    filename = f"extracted/{self.file_path.split('/')[-1].replace('.bnk', f'_{i}.wem')}"
                    with open(filename, "wb") as f:
                        f.write(data)
                    
                    system(f".\\vgmstream\\vgmstream-cli.exe -i {filename} -o {filename.replace('wem', 'wav')} > NUL")
                    remove(filename)
            elif magic == b'HIRC':
                count = self.read('I')
                self.hircEntries:list[HIRCEntry] = []
                for _ in range(count):
                    try:
                        self.hircEntries.append(HIRCEntry(self.stream))
                    except error as e:
                        break # EOF
            elif magic == b'STID':
                one = self.read('I')
                count = self.read('I')
                self.stidEntries:list[STIDEntry] = []
                for _ in range(count):
                    self.stidEntries.append(STIDEntry(self.stream))
    
    def __repr__(self):
        return (f"BnkDecoder(file_path={self.file_path}, bankVersion={self.bankVersion}, id={self.id}, entryCount={len(self.didxEntries)})",
        f"dataEntriesCount={len(self.dataEntries)}, stidEntriesCount={len(self.stidEntries)})")