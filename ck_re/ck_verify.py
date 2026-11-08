"""ck_verify.py ORIG NOVO: confere que as voices de fabrica do CK resolvem identicas e lista as novas (waves validos e nao vazios)."""
import struct, sys, hashlib
WBASE=0x15E
class P:
    def __init__(s,p):
        s.f=open(p,'rb'); s.V=0x1100180; s.PV=0x1C00180; s.WB=0x2100200
        V=s.V; KT,MAP,MENU,OT=struct.unpack('<4I',s.rd(V+0x20,16)); s.MENU=MENU; s.map=s.rd(V+MAP,256)
        s.km=[s.u32(V+KT+4*i) for i in range((s.u32(V+KT)-KT)//4)]
        s.npv=int.from_bytes(s.rd(s.PV+12,4),'big'); s.pv=[s.rd(s.PV+16+16*i,16) for i in range(s.npv)]
        s.vo=[s.u32(V+OT+4*i) for i in range(s.npv)]
        s.wsize=s.u32(0x2100180+0x7c)
    def rd(s,o,n): s.f.seek(o); return s.f.read(n)
    def u32(s,o): return struct.unpack('<I',s.rd(o,4))[0]
    def u16(s,o): return struct.unpack('<H',s.rd(o,2))[0]
    def menu(s,cat,pc):
        row=s.map[cat]; return None if row==0xff else s.u16(s.V+s.MENU+256*row+2*pc)
    def resolve(s,cat,pc):
        V=s.V; vi=s.menu(cat,pc)
        if vi is None: return None,'organ',set()
        o=s.vo[vi]; t=s.rd(V+o,1)[0]; hl={0x61:0x2c,0x08:0x10}.get(t)
        if hl is None: return vi,hashlib.md5(s.rd(V+o,64)).hexdigest(),set()
        nel=s.u16(V+o+10); out=[s.rd(V+o,hl)]; waves=set()
        for e in range(nel):
            p=s.u32(V+o+hl+4*e); eb=bytearray(s.rd(V+p,200)); k=struct.unpack('<H',eb[12:14])[0]; eb[12:14]=b'..'
            ko=s.km[k]; n,ty=struct.unpack('<HH',s.rd(V+ko,4)); st=84 if ty==2 else 48
            zs=s.rd(V+ko,4+n*st); out+=[bytes(eb),zs]
            for z in range(n):
                waves.add(struct.unpack('<I',zs[4+st*z+12:4+st*z+16])[0])
                if ty==2: waves.add(struct.unpack('<I',zs[4+st*z+48:4+st*z+52])[0])
        return vi,hashlib.md5(b''.join(out)).hexdigest(),waves
A=P(sys.argv[1]); B=P(sys.argv[2]); bad=0
for i,e in enumerate(A.pv):
    assert B.pv[i]==e
    va,ha,_=A.resolve(e[1],e[2]); vb,hb,_=B.resolve(e[1],e[2])
    if ha!=hb or va!=vb: bad+=1; print('DIFERENTE',i,e[3:].rstrip(b'\0'))
print('fabrica:',len(A.pv),'voices,',bad,'diferentes; keymaps',len(A.km),'->',len(B.km),'; wave',hex(A.wsize),'->',hex(B.wsize))
for i in range(A.npv,B.npv):
    e=B.pv[i]; vi,h,w=B.resolve(e[1],e[2])
    pages=[(x+WBASE) for x in w]; ok=all(WBASE<=p and p*4096<B.wsize for p in pages)
    nz=sum(any(B.rd(B.WB+p*4096,4096)) for p in pages)
    print(f"PV {i} cat {e[1]:#04x} pc {e[2]:2d} {e[3:].rstrip(bytes(1)).decode():14s} VPRM {vi} waves {len(w):4d} dentro {ok} nao_vazios {nz}/{len(w)}")
