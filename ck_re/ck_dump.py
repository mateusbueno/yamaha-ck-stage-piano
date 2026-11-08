"""ck_dump.py PGM [PV...]: estrutura das voices (PV -> VPRM -> elementos -> keymaps) no 8W61OS_.PGM do CK."""
import struct,sys,collections
f=open(sys.argv[1],'rb')
def rd(o,n): f.seek(o); return f.read(n)
def u32(o): return struct.unpack('<I',rd(o,4))[0]
def u16(o): return struct.unpack('<H',rd(o,2))[0]
PB=0x140180; V=PB+0xFC0000; PV=PB+0x1AC0000
KT,MAP,MENU,OT=struct.unpack('<4I',rd(V+0x20,16))
km=[u32(V+KT+4*i) for i in range((u32(V+KT)-KT)//4)]
npv=int.from_bytes(rd(PV+12,4),'big'); pv=[rd(PV+16+16*i,16) for i in range(npv)]
mp=rd(V+MAP,256)
def vidx(e):
    row=mp[e[1]]
    return None if row==0xff else u16(V+MENU+256*row+2*e[2])
NV=(u32(V+OT)-OT)//4
vo=[u32(V+OT+4*i) for i in range(NV)]
print('NV',NV,'NKM',len(km))
sel=[int(x) for x in sys.argv[2:]] or range(npv)
for i in sel:
    e=pv[i]; vi=vidx(e); name=e[3:].rstrip(b'\0').decode('latin1')
    if vi is None or vi>=NV: print(i,name,'sem VPRM',vi); continue
    o=vo[vi]; t=rd(V+o,1)[0]
    hl={0x61:0x2c,0x08:0x10}.get(t)
    if hl is None: print(i,name,'VPRM',vi,'tipo',hex(t)); continue
    nel=u16(V+o+10)
    els=[]
    for k in range(nel):
        p=u32(V+o+hl+4*k); eb=rd(V+p,200); kk=u16(V+p+12)
        n,ty=struct.unpack('<HH',rd(V+km[kk],4)) if kk<len(km) else (0,0)
        st=84 if ty==2 else 48
        fm=collections.Counter(u16(V+km[kk]+4+st*z+0x1c) for z in range(n)) if kk<len(km) else {}
        els.append(f"[v{eb[7]}-{eb[6]} k{eb[5]}-{eb[4]} km{kk} t{ty} n{n} f{dict(fm)} b0={eb[0]} b97={eb[97]}]")
    print(i,name,'VPRM',vi,'tipo',hex(t),'nel',nel,' '.join(els))
