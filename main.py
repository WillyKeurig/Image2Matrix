import os, struct, zlib
from typing import List

png = 'maze.png'
path = os.path.join(os.path.dirname(__file__), png)

class PNG:

    signature = b'\x89PNG\r\n\x1a\n'
    
    def __init__(self, path):

        # exception if file signature not valid
        PNG.validate_signature(path)

        self.path       = path
        self.chunks     = self.get_chunks()

        # meta data from IHDR
        self.IHDR = struct.unpack('>2I5B', self.chunks[0].data)
        PNG.validate_IHDR(self.IHDR)

        self.width      : int   = self.IHDR[0]  # 4B
        self.height     : int   = self.IHDR[1]  # 4B
        self.bit_depth  : bytes = self.IHDR[2]  # 1B 
        self.color_type : bytes = self.IHDR[3]  # 1B
        self.comp_meth  : bytes = self.IHDR[4]  # 1B - Compression Method
        self.filt_meth  : bytes = self.IHDR[5]  # 1B - Filter Method
        self.itrl_meth  : bytes = self.IHDR[6]  # 1B - Interlace Method
 
        # get data bytes from all data chunks
        self.IDAT = b''.join(chunk.data for chunk in self.chunks if chunk.type == b'IDAT')
        self.IDAT = zlib.decompress(self.IDAT)

        self.scanlines = self.get_scanlines()


    def get_chunks(self) -> List['PNG.Chunk']:

        # set cursor to end of signature
        cursor = 8
        chunks = []

        while 1:
            # add chunk to PNG instance
            chunk   = PNG.Chunk(cursor)
            chunks.append(chunk)

            # set cursor to end of current/start of next
            cursor  = chunks[-1].end

            # exit on closing chunk
            if chunk.type == b'IEND':
                break

        return chunks


    def get_scanlines(self):

        scanlines = []

        px  = PNG.px_size(self.color_type)
        w   = self.width
        h   = self.height
        
        bs  = (1+(w*px))*h  # total bytes in data
        row = 1+(w*px)      # total bytes in row

        # iter Row Start index for each line
        for row_start in range(0, bs, row):

            filter  = self.IDAT[row_start]                  # first byte is filter
            data    = self.IDAT[row_start+1:row_start+row]  # remaining is data
            pixels  = []

            # seperate data in pixel sized chunks
            for b in range(0, row-px, px):
                pixels.append(data[b:b+px])
            
            # append filter and Tuple[bytes]
            scanlines.append((filter, tuple(pixels)))

        return scanlines


    # STATIC

    @staticmethod
    def px_size(color_type: int):
            
            # if color type
            match(color_type):
                case 0:  # greyscale
                    return 1
                case 2:  # truecolor
                    return 3
                case 3:  # indexed-color
                    return 1
                case 4:  # greyscale with alpha
                    return 2
                case 6:  # truecolor w/ alpha
                    return 4


    # VALIDATION

    @staticmethod
    def validate_signature(path):
        with open(path, 'rb') as f:
            if f.read(len(PNG.signature)) != PNG.signature:
                raise Exception(
                    f"Invalid signature.\
                    Expected {PNG.signature},\
                    got {f.read(len(PNG.signature))}"
                )

    @staticmethod
    def validate_IHDR(IHDR):
        # Compression Method (4) and Filter Method (5) can only be 0
        if IHDR[4]:
            raise Exception(
                f"Invalid Compression Method in IHDR.\
                Expected 0,\
                got {IHDR[4]}"
            )
        if IHDR[5]:
            raise Exception(
                f"Invalid Filter Method in IHDR.\
                Expected 0,\
                got {IHDR[5]}"
            )


    # DATA STRUCTURES

    class Chunk:

        def __init__(self, start: int):

            self.start  : int
            self.end    : int    # actual last index == end-1

            self.length : int
            self.type   : bytes  # 4 chars
            self.data   : bytes  # any
            self.crc    : bytes  # unsigned int
            self.valid  : bool

            with open(path, 'rb') as f:

                f.seek(start)  # start of chunk
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

print('_______________')
for scanline in png.scanlines:
    print(png.scanlines.index(scanline), '\t', scanline)
print('_______________\n')











# w = h = 13
# pixel = w*4
# for i in range(0, (h*pixel)+h, pixel+1):
#     print(png.IDAT[i:i+pixel+1])
