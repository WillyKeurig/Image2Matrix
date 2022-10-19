import os, struct, zlib
from typing import Iterable, List, Tuple

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

        # calculated meta data
        self.px_size    : int   = self.get_px_size()
 
        # get data bytes from all data chunks
        self.IDAT = b''.join(chunk.data for chunk in self.chunks if chunk.type == b'IDAT')
        self.IDAT = zlib.decompress(self.IDAT)

        self.scanlines      = self.get_scanlines()
        self.channel_matrix = self.reconstruct()  # remove filters from scanlines



    def get_px_size(self):
        
        # if color type
        match(self.color_type):
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

        px  = self.px_size
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


    def reconstruct(self):
        
        # method to defilter/reconstruct png image data
        # reconstructing a pixel requires reconstruction of bytes in said pixel
        # bytes that require reconstruction are named as followed:
        # 
        # BYTE STRUCTURE RELATIVE TO X:
        #  C|B  ==  X-px-row | X-row 
        #  A|X  ==  X-px     | X
        #
        # these reconstructed bytes are then used to calculate the absolute pixel data
        # calculations are based on specified filter method


        ### INIT

        recon = []
        f   = lambda r : self.scanlines[r][0]
        pxs = lambda r : self.scanlines[r][1] 

        def get_x(row, px, B):
            return pxs(row)[px][B]

        
        # FILTER reconstruction methods as specified by ISO standard
        def none(pos: Iterable[int]):   # filter method 0
            return get_x(*pos)

        def sub(pos: Iterable[int]):    # filter method 1
            return (get_x(*pos) + recon_a(*pos)) % 256
        
        # not tested
        def up(pos: Iterable[int]):     # filter method 2
            return get_x(*pos) + recon_b(pos)

        # not tested
        def avg(pos: Iterable[int]):    # filter method 3
            return get_x + (recon_a(*pos)) + recon_b(*pos) >> 1

        # not tested
        def paeth(pos: Iterable[int]):  # filter method 4

            def predictor(a,b,c):

                p = a + b - c
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)

                if pa <= pb and pa <= pc:
                    Pr = a
                elif pb <= pc:
                    Pr = b
                else:
                    Pr = c
                return Pr

            return get_x(*pos) + predictor(recon_a(*pos), recon_b(*pos), recon_c(*pos))


        # RECONSTRUCTION / DEFILTERING
        def recon_a(row, px, B):
            return recon[row][px-1][B] if px else 0

        def recon_b(row, px, B):
            return recon[row-1][px][B] if row else 0

        def recon_c(row, px, B):
            return recon[row-1][px-1][B] if row and px else 0

        def recon_pixel(row, px) -> Tuple['int']:

            filters = [none, sub, up, avg, paeth]
            px_new  = []

            for B in range(self.px_size):
                x_pos   = (row, px, B)
                recon_x = filters[f(row)](x_pos)
                px_new.append(recon_x)

            return tuple(px_new)


        ### MAIN
        recon  = []

        for row in range(self.height):
            recon.append([])  # empty row

            for px in range(self.width):
                # append reconstructed pixel directly to row
                # because new matrix datastructure doesn't include a filter field at row[0]
                recon[row].append(recon_pixel(row, px))

        return recon

    ### STATIC

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


    ### DATA STRUCTURES

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


def maze_print(matrix, ch='H', sep=' '):
    for row in matrix:
        for px in row:
            s = ch+sep if px else ' '+sep
            print(s, end='')
        print()


def maze_matrix_walls(png, inverted=False):
    matrix = []
    
    for row in range(png.height):
        matrix.append([])  # new row

        for px in range(png.width):
            matrix[row].append([])  # new cell
            filled = png.channel_matrix[row][px] == (0,0,0,255)
            matrix[row][px] = filled ^ inverted
    
    return matrix


maze = maze_matrix_walls(PNG(path), inverted=False)
maze_print(maze)