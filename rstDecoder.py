from struct import unpack, calcsize
from io import BytesIO
from decoder import Decoder
from base64 import b64encode

class RSTDecoder(Decoder):
    def __init__(self, raw_data: bytes, file_path: str = None):
        self.stream = BytesIO(raw_data)
        self.file_path = file_path
        self.magic = self.stream.read(3)
        self.endianness = '<'
        if self.magic != b'RST':
            raise ValueError(f"{self.file_path}: Invalid RST file format. MAGIC: {self.magic}")
    
    def read(self, fmt):
        size = calcsize(fmt)
        data = self.stream.read(size)
        if len(data) < size:
            raise EOFError("Unexpected end of file while reading RST data.")
        return unpack(f"{self.endianness}{fmt}", data)[0]

    def decompress(self):
        self.version = unpack('B', self.stream.read(1))[0]
        if self.version == 2:
            if self.read("B"):
                n = self.read("L")
                self.font_config = self.stream.read(n)
            else:
                self.font_config = None
        elif self.version == 3:
            pass
        elif self.version == 4 or self.version == 5:
            self.hash_bits = 38
        hash_mask = (1 << self.hash_bits) - 1
        count = self.read("L")
        entries = []
        self.entries = {}
        for _ in range(count):
            v = self.read("Q")
            entries.append((v >> self.hash_bits, v & hash_mask))
        has_trenc = False
        if self.version < 5:
            has_trenc = self.read("B")
        data = self.stream.read()
        for i, h in entries:
            if has_trenc and data[i] == 0xFF:
                size = int.from_bytes(data[i+1:][:2], 'little')
                d = b64encode(data[i+3:][:size])
                self.entries[h] = d.decode('utf-8', 'replace')
            else:
                end = data.find(b"\0", i)
                d = data[i:end]
                self.entries[h] = d.decode('utf-8', 'replace')
        print(f"Decoded {len(self.entries)} entries from RST file {self.file_path}")
        with open(f"extracted/{self.file_path.replace('/', '_')}", "w", encoding="utf-8") as f:
            for key, value in self.entries.items():
                f.write(f"{hex(key)}: {value}\n")

    def __repr__(self):
        return (f"RSTDecoder(version={self.version}, entries_count={len(self.entries)}, "
                f"file_path={self.file_path})")