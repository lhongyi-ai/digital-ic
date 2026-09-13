import hashlib,struct,unittest,zlib
import numpy as np
from vibfpga.known_board import build_image,parse_log,COMMIT

class KnownBoardContract(unittest.TestCase):
    model=b'{"test_fixture":true}'
    def log(self):
        w=[0]*64;w[:10]=[0x314c534b,1,16,4,4,750,64,64,0,0]
        w[10:20]=[(-12)&0xffffffff,(-13)&0xffffffff,1,0,0,192,368,956,326,1842]
        w[20:26]=[100,100+63*750,100+63*750+300,1234,1234,64]
        w[32:40]=struct.unpack('<8I',hashlib.sha256(self.model).digest())
        w[62]=zlib.crc32(struct.pack('<62I',*w[:62]));w[63]=COMMIT
        return struct.pack('<64I',*w)+b'\xff'*(4096-256)
    def parse(self,data,**kw):return parse_log(data,self.model,n=16,windows=4,**kw)
    def test_raw_image_and_limits(self):
        raw=np.arange(-32,32,dtype=np.int16);b=build_image(raw,self.model,n=16,windows=4)
        self.assertEqual(b[64:],raw.astype('<i2').tobytes())
        self.assertEqual(struct.unpack('<I',b[24:28])[0],zlib.crc32(b[64:]))
        for values,period in [(raw[:-1],750),(raw.astype(float),750),(raw,12001),(raw,3)]:
            with self.assertRaises(ValueError):build_image(values,self.model,period,n=16,windows=4)
    def test_valid_log(self):
        r=self.parse(self.log());self.assertEqual(r['score'],-12);self.assertEqual(r['generated'],64)
    def test_shifted_corrupt_or_uncommitted_read(self):
        b=self.log()
        for invalid in [b'\xff'+b[:-1],b[:43]+bytes([b[43]^1])+b[44:],b[:252]+b'\xff'*4+b[256:]]:
            with self.assertRaises(ValueError):self.parse(invalid)
    def test_wrong_model_even_with_valid_crc(self):
        b=bytearray(self.log());b[130]^=1;struct.pack_into('<I',b,248,zlib.crc32(b[:248]))
        with self.assertRaises(ValueError):self.parse(b)
    def test_counter_mismatch_even_with_valid_crc(self):
        b=bytearray(self.log());struct.pack_into('<I',b,28,63);struct.pack_into('<I',b,248,zlib.crc32(b[:248]))
        with self.assertRaises(ValueError):self.parse(b)
    def test_explicit_error_requires_opt_in(self):
        b=bytearray(self.log());struct.pack_into('<I',b,32,16);struct.pack_into('<I',b,248,zlib.crc32(b[:248]))
        with self.assertRaises(ValueError):self.parse(b)
        self.assertEqual(self.parse(b,allow_error=True)['errors'],16)

if __name__=='__main__':unittest.main()
