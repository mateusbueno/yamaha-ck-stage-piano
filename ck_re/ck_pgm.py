"""ck_pgm.py - container 8W61OS_.PGM (Yamaha CK88/CK76/CK61), mesmo formato do 8T25OS_.PGM do YC.
4 imagens (Installer, Boot, Program, Wave), cabecalho 0x80: +0x00 nome, +0x18 versao[8], +0x40 soma de bytes do corpo, +0x7C tamanho.
Strings de Version Info nos corpos: 0x1400E0 (Boot) e 0x2000160 (Program).
uso: ck_pgm.py info PGM | cp_pgm.py setver PGM_IN PGM_OUT 2.01.0"""
import struct, sys, shutil, numpy as np
HDRS=(0x0,0x100080,0x140100,0x2100180)
VSTR=((0x100080,0x1400E0),(0x140100,0x2000160))
def bsum(f,off,size):
    f.seek(off); s=0; left=size
    while left:
        b=f.read(min(left,1<<26)); left-=len(b); s+=int(np.frombuffer(b,np.uint8).sum(dtype=np.uint64))
    return s&0xffffffff
def info(p):
    f=open(p,'rb'); ok=True
    for h in HDRS:
        f.seek(h); hd=f.read(0x80); ck,=struct.unpack('<I',hd[0x40:0x44]); sz,=struct.unpack('<I',hd[0x7c:0x80])
        s=bsum(f,h+0x80,sz); ok&=s==ck
        print(f"{hd[:24].rstrip(bytes(1)).decode():10s} ver={hd[0x18:0x20].rstrip(bytes(1)).decode():8s} size={sz:#x} sum={ck:#010x} {'OK' if s==ck else 'ERRO calc=%#x'%s}")
    for _,o in VSTR: f.seek(o); print(f"string {o:#x}: {f.read(8)}")
    return ok
def patch(f,hdr,off,new):
    f.seek(hdr+0x40); s=struct.unpack("<I",f.read(4))[0]; f.seek(off); old=f.read(len(new))
    s=(s-sum(old)+sum(new))&0xffffffff; f.seek(off); f.write(new); f.seek(hdr+0x40); f.write(struct.pack("<I",s))
def setver(src,dst,ver):
    shutil.copyfile(src,dst); f=open(dst,'r+b'); v=ver.encode().ljust(8,b"\0"); assert len(v)==8
    for h in HDRS: f.seek(h+0x18); f.write(v)
    for h,o in VSTR:
        f.seek(o); assert f.read(6)==b"2.00.0", "string de versao nao encontrada"; patch(f,h,o,v)
    f.close()
if __name__=="__main__":
    c=sys.argv[1]
    if c=="info": sys.exit(0 if info(sys.argv[2]) else 1)
    if c=="setver": setver(*sys.argv[2:5]); info(sys.argv[3])
