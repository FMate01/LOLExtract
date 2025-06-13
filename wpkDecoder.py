from struct import unpack
from io import BytesIO
from decoder import Decoder
from os import remove, system

class WPKFileEntry:
    def __init__(self, stream: BytesIO):
        self.offset = unpack('I', stream.read(4))[0]
        self.size = unpack('I', stream.read(4))[0]
        name_length = unpack('I', stream.read(4))[0] * 2
        self.name = stream.read(name_length).decode("utf-16-le")
        stream.seek(self.offset)
        self.data = BytesIO(stream.read(self.size))
    
    def __repr__(self):
        self.data.seek(0) 
        magic = self.data.read(4)
        self.data.seek(0)
        return f"WPKFileEntry(name='{self.name}', size={self.size}, type={magic})"

class WPKDecoder(Decoder):
    def __init__(self, raw_data: bytes, file_path: str = None):
        self.stream = BytesIO(raw_data)
        self.file_path = file_path
        self.magic = self.stream.read(4)
        if self.magic != b'r3d2':
            raise ValueError(f"{self.file_path}: Invalid WPK file format. MAGIC: {self.magic}")
    
    def decompress(self):
        self.version = unpack('I', self.stream.read(4))[0]
        self.fileCount = unpack('I', self.stream.read(4))[0]
        self.offsets = [unpack('I', self.stream.read(4))[0] for _ in range(self.fileCount)]
        self.entries:list[WPKFileEntry] = []
        for offset in self.offsets:
            if offset != 0:
                self.stream.seek(offset)
                entry = WPKFileEntry(self.stream)
                self.entries.append(entry)
        print(f"Decompressed {len(self.entries)} entries from WPK file: {self.file_path}")

        for entry in self.entries:
            filename = f"extracted/{'_'.join(self.file_path.split('.')[0].split('/'))}_{entry.name}"
            with open(filename, "wb") as f:
                f.write(entry.data.read())
        
            system(f".\\vgmstream\\vgmstream-cli.exe -i {filename} -o {filename.replace('wem', 'wav')} > NUL")
            remove(filename)
    
    def __repr__(self):
        return (f"WPKDecoder(version={self.version}, fileCount={self.fileCount}")