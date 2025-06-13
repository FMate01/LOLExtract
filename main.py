from struct import unpack
from io import BytesIO
from enum import Enum
import zstandard as zstd
import gzip
from wpkDecoder import WPKDecoder
from bnkDecoder import BnkDecoder
from rstDecoder import RSTDecoder
from decoder import Decoder
from os import mkdir, listdir

class CompressionType(Enum):
    UNCOMPRESSED = 0
    GZIP = 1
    FILE_REDIRECT = 2
    ZSTD = 3
    ZSTD_WITH_SUBCHUNKS = 4

    @classmethod
    def from_byte(cls, byte: int):
        try:
            return cls(byte)
        except ValueError:
            raise ValueError(f"Invalid compression type byte: {byte}")
    
    def __str__(self):
        return self.name

class WadEntry:
    def __init__(self, stream: BytesIO, wadVersion: int, hashes: dict[str, str] = None):
        self.pathHash = stream.read(8)[::-1].hex()
        self.pathHash = self.pathHash.rjust(16, '0')  # Ensure it's 16 characters long
        if hashes:
            self.pathHash = hashes.get(self.pathHash, "UnknownHash_" + self.pathHash)
        else:
            raise ValueError("Hashes dictionary is required to resolve path hashes.")
        self.dataOffset  = unpack('I', stream.read(4))[0]
        self.compressedSize = unpack('I', stream.read(4))[0]
        self.decompressedSize = unpack('I', stream.read(4))[0]
        dataTypeAndSubchunkCount = unpack('B', stream.read(1))[0]
        self.dataType = CompressionType(dataTypeAndSubchunkCount & 0x0F)
        self.subchunkCount = dataTypeAndSubchunkCount >> 4
        if wadVersion == 1:
            stream.read(3)  # Skip the padding bytes
            return
        self.containsDuplicates = unpack('B', stream.read(1))[0] != 0
        self.firstSubchunkOffset = unpack('H', stream.read(2))[0]
        self.entryChecksum = unpack('Q', stream.read(8))[0]
        endPos = stream.tell()
        stream.seek(self.dataOffset)
        if self.dataType == CompressionType.UNCOMPRESSED:
            self.decompressedData = stream.read(self.compressedSize)
        elif self.dataType == CompressionType.ZSTD:
            compressed_data = stream.read(self.compressedSize)
            self.decompressedData = zstd.decompress(compressed_data)
        elif self.dataType == CompressionType.GZIP:
            compressed_data = stream.read(self.compressedSize)
            self.decompressedData = gzip.decompress(compressed_data)
        stream.seek(endPos)  # Restore the stream position after reading data

    def __repr__(self):
        return (f"WadEntry(pathHash={self.pathHash}, dataOffset={self.dataOffset}, "
                f"compressedSize={self.compressedSize}, decompressedSize={self.decompressedSize}, "
                f"dataType={self.dataType}, data={self.decompressedData[:20]}..., ")

class WadExtractor:
    def __init__(self, wad_file_path: str, hashes_file_path: str = "hashes.game.txt"):
        self.wad_file = open(wad_file_path, "rb")
        self.hashes = self.load_hashes(hashes_file_path)

    def load_hashes(self, hashes_file_path: str):
        hashes = {}
        with open(hashes_file_path, "r") as f:
            for line in f:
                parts = line.split(" ")
                if len(parts) >= 2:
                    hash_value = parts[0]
                    path = " ".join(parts[1:]).strip()
                    hashes[hash_value] = path
        return hashes
    
    def decodeFile(self):
        magic = self.wad_file.read(2)
        if magic != b'RW':
            raise ValueError("Invalid WAD file format")
        self.majorVersion, self.minorVersion = unpack('BB', self.wad_file.read(2))
        if self.majorVersion == 1:
            self.entryHeaderOffset, self.entryHeaderSize, self.entryCount = unpack("HHI", self.wad_file.read(8))
            self.wad_file.seek(self.entryHeaderOffset)
        elif self.majorVersion == 2:
            self.ECDSASignatureLength = unpack('B', self.wad_file.read(1))[0]
            self.ECDSASignature = self.wad_file.read(83)
            self.XXH64Sum, self.entryHeaderOffset, self.entryHeaderSize, self.entryCount = unpack("QHHI", self.wad_file.read(16))
            self.wad_file.seek(self.entryHeaderOffset)
        elif self.majorVersion == 3:
            self.ECDSASignature = self.wad_file.read(256)
            self.XXH64Sum = self.wad_file.read(8)
            self.entryCount = unpack("I", self.wad_file.read(4))[0]
        self.entries:list[WadEntry] = []
        if "extracted" not in listdir("."):
            mkdir("extracted")
        for _ in range(self.entryCount):
            entry = WadEntry(self.wad_file, self.majorVersion, self.hashes)
            decoder = self.selectDecoder(entry.decompressedData, entry.pathHash)
            if decoder:
                decoder.decompress()
                self.entries.append(decoder)
            else:
                if "unknowns" not in listdir("."):
                    mkdir("unknowns")
                filePath = entry.pathHash.split("/")[-1]
                with open(f"unknowns/{filePath}", "wb") as f:
                    f.write(entry.decompressedData)
        print(f"Decoded {len(self.entries)} entries from WAD file {self.wad_file.name}")
        self.wad_file.close()
        if "unknowns" in listdir("."):
            for file in listdir("unknowns"):
                print(f"No decoder found for {file}, saved to unknowns/{file}")
    
    def selectDecoder(self, raw_data: bytes, file_path:str) -> Decoder | None:
        if raw_data.startswith(b'r3d2'):
            return WPKDecoder(raw_data, file_path)
        elif raw_data.startswith(b'BKHD'):
            return BnkDecoder(raw_data, file_path)
        elif raw_data.startswith(b'RST'):
            return RSTDecoder(raw_data, file_path)
        else:
            return None
        

if __name__ == "__main__":
    wad_file_name = "insert wad file name here"
    wad_extractor = WadExtractor(wad_file_name)
    wad_extractor.decodeFile()