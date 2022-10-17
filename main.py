import os, struct, zlib
from sys import int_info

png = 'maze.png'
path = os.path.join(os.path.dirname(__file__), png)

class PNG:

    signature = b'\x89PNG\r\n\x1a\n'
    
    def __init__(self, path):

        with open(path, 'rb') as f:
            if f.read(len(PNG.signature)) != PNG.signature:
                raise Exception(f"Invalid signature. Expected {PNG.signature}, got {f.read(len(PNG.signature))}")

        cursor = 8
        chunks = []


        # image contains 3 chunks. Match for type == b'IEND' later
        for i in range(3):
            chunk = Chunk(cursor)
            chunks.append(chunk)
            cursor = chunks[-1].end



class Chunk:

    def __init__(self, start: int):

        self.start  : int
        self.end    : int

        self.length : int
        self.type   : bytes  # 4 chars
        self.data   : bytes  # any
        self.crc    : bytes  # unsigned int
        self.valid  : bool

        with open(path, 'rb') as f:

            f.seek(start)   # start of chunk
            self.length, self.type = struct.unpack('>I4s', f.read(8))

            f.seek(start + 8)  # start of data
            self.data = f.read(self.length)

            f.seek(start + 8 + self.length)  # start of crc
            self.crc = struct.unpack('>I', f.read(4))[0]

            # validate crc
            self.valid = self.crc == zlib.crc32(self.data, zlib.crc32(struct.pack('>4s', self.type)))

        self.start  = start
        self.end    = start + 12 + self.length


png = PNG(path)
