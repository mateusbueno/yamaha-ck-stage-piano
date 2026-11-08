"""v2.05.0: zonas custom usam loop sustentado do index (wave["loop"]=[a,b] em quadros) quando existir.
v2.03.2: acrescenta voices NOVAS (sem substituir nenhuma de fabrica).
- waves acrescentados no FIM da imagem Wave (regiao PRST ampliada + copia de cauda realocada);
- VPRM: tabela de keymaps e tabela de offsets de voice realocadas para a area livre (cabecalho +0x20 / +0x2C),
  voice nova = copia do blob da voice de origem, elementos copiados com keymap novo (copias dos keymaps de origem);
- menu VPRM (linha da categoria, pc livre) e Preset Voice (entrada nova, contagem BE).
usage: ck_build_new.py VERSION OUTDIR BASEPGM plan.json  (porta do cp_build_new para o CK88/76/61: 8W61OS_.PGM)
plan.json: lista de {kind: cfx|eps, src: idx VPRM, cat, name, data: pasta (index.json+waves.bin), tag (eps), km: {km_orig: vel_central}}"""
import struct, json, os, shutil, sys
ver,outdir,base,planf=sys.argv[1:5]
PLAN=json.load(open(planf))
os.makedirs(outdir,exist_ok=True); out=os.path.join(outdir,"8W61OS_.PGM")
shutil.copyfile(base,out)
f=open(out,"r+b")
PH=0x140100; PB=0x140180; WH=0x2100180; WB=0x2100200
V=PB+0xFC0000; PV=PB+0x1AC0000; VSIZE=0x800000; VREG=0xB00000; WBASE=0x15E   # CK: VPRM regiao 11 MB (copia em RAM 0x130 = 8 MB -> alocar so ate 8 MB), Preset Voice 0x21B00000, waves (id+0x15E)*4096
def rd(o,n): f.seek(o); return f.read(n)
u32=lambda o: struct.unpack("<I",rd(o,4))[0]; u16=lambda o: struct.unpack("<H",rd(o,2))[0]
def patch(hdr,off,new):
    f.seek(hdr+0x40); s=struct.unpack("<I",f.read(4))[0]
    f.seek(off); old=f.read(len(new)); s=(s-sum(old)+sum(new))&0xffffffff
    f.seek(off); f.write(new); f.seek(hdr+0x40); f.write(struct.pack("<I",s))
# ---------- VPRM: estado de fabrica ----------
KT=u32(V+0x20); OT=u32(V+0x2c); MENU=u32(V+0x28); MAP=u32(V+0x24)
assert rd(V,8)==b"UTG VPRM" and KT==0x1AD878 and OT==0x6340 and MENU==0x4040 and MAP==0x40
NKM=(u32(V+KT)-KT)//4; assert NKM==884
km=[u32(V+KT+4*i) for i in range(NKM)]
NV=367; vo=[u32(V+OT+4*i) for i in range(NV)]
HL={0x61:0x2c,0x08:0x10}   # tamanho do cabecalho do blob de voice por tipo (ponteiros de elemento logo depois)
els=set(); com=set()
for o in vo:
    t_=rd(V+o,1)[0]
    if t_ not in HL: continue
    nel=u16(V+o+0x0a); els.update(u32(V+o+HL[t_]+4*k) for k in range(nel))
    if t_==0x61: com.add(u32(V+o+0x28))
used_end=0x2a4998
allp=sorted(set(vo)|els|com|set(km)|{OT,KT,MAP,MENU,used_end})
nxt=lambda p: allp[allp.index(p)+1]
free=(used_end+0xfff)&~0xfff
blank=rd(V+free,VREG-free); assert set(blank)=={0xff}, "area livre do VPRM nao esta vazia"
def alloc(n,al=16):
    global free
    free=(free+al-1)&~(al-1); o=free; free+=n; assert free<=VSIZE; return o
def kmsize(off):
    n,t=struct.unpack("<HH",rd(V+off,4)); return 4+n*(84 if t==2 else 48), n, t
# ---------- PV ----------
pvn=int.from_bytes(rd(PV+12,4),"big"); assert pvn==NV
pv=[rd(PV+16+16*i,16) for i in range(pvn)]
# ---------- Wave: regiao PRST ----------
wsize=u32(WH+0x7c); assert wsize==0x2FBC0000
prst=bytearray(rd(WB,4096)); assert prst[:4]==b"PRST"
regs=struct.unpack(">10I",prst[4:44]); assert regs[4]==WBASE and regs[5]==0x2FA31
assert rd(WB+wsize-4096,0x2c)==bytes(prst[:0x2c]), "copia de cauda nao encontrada"
page=wsize//4096            # primeira pagina livre (apos a cauda antiga)
placed={}
def place(data):
    global page
    if data not in placed:
        Ii=json.load(open(os.path.join(data,"index.json"))); bl=open(os.path.join(data,"waves.bin"),"rb").read(); assert len(bl)==Ii['total_pages']*4096
        placed[data]=page; waveblobs.append((page,bl)); page+=Ii['total_pages']
    return placed[data]
SKIP=set()|{int(x) for x in os.environ.get('YC_SKIP','').split(',') if x}   # PV que derrubam (202-204) ou deixam mudo (214, 217, 218: v2.04.3/4/6)
newel=[]; newkm=[]; newvo=[]; newpv=[]; menu_set=[]; zone_patches=[]; waveblobs=[]; log=[]
for vp in PLAN:
    I=json.load(open(os.path.join(vp['data'],"index.json"))); blob=open(os.path.join(vp['data'],"waves.bin"),"rb").read()
    assert len(blob)==I['total_pages']*4096
    first_id=place(vp['data'])-WBASE
    src=vp['src']; so=vo[src]; hl=HL[rd(V+so,1)[0]]
    nel=u16(V+so+0x0a); hdr=bytearray(rd(V+so,hl+4*nel))
    kmmap={}; elmap={}
    if vp.get('inplace'):
        for k in sorted(int(x) for x in vp['km']): kmmap[k]=(k,km[k])
        pi=vp['pv_src']; patch(PH,PV+16+16*pi+3,vp['name'].encode()[:13].ljust(13,b"\0"))
        vidx=src; row=None; pc=pv[pi][2]; cat=pv[pi][1]
    elif vp['kind']=="custom":   # keymaps novos gerados: uma zona por grupo do SF2, bytes da 1a zona do keymap de origem como molde
        Z=I['sets'].get(vp.get('tag'),[]); sil=I['silence']
        for e,spec in enumerate(vp['els']):
            p=u32(V+so+hl+4*e); k=u16(V+p+12)
            n0,t=struct.unpack("<HH",rd(V+km[k],4)); st=84 if t==2 else 48; tz=rd(V+km[k]+4,st)
            tail=struct.pack("<H",13 if t==2 else 6)+bytes(2)+struct.pack("<6h",0,0,0,0,0,0)+bytes(4)
            if spec=="silence": zl=[(0,127,60,sil,sil)]
            else:
                c=sorted([q for q in Z if q['vel'][0]<=spec['vc']<=q['vel'][1]],key=lambda q:q['key'][0]); zl=[]
                out_sil=vp.get('outside')=="silence"
                if out_sil and c[0]['key'][0]>0: zl.append((0,c[0]['key'][0]-1,60,sil,sil))
                for i,q in enumerate(c):
                    lo=(q['key'][0] if out_sil else 0) if i==0 else c[i-1]['key'][1]+1; hi=(q['key'][1] if out_sil else 127) if i==len(c)-1 else q['key'][1]
                    ch=spec['ch']; wl=q['L'] if 'L' in q else q; wr=q['R'] if 'R' in q else q
                    if ch=="R": wl=wr
                    if ch=="L": wr=wl
                    zl.append((lo,hi,q['root']+q['shift'],wl,wr))
                if out_sil and c[-1]['key'][1]<127: zl.append((c[-1]['key'][1]+1,127,60,sil,sil))
            zb=b""
            for lo,hi,root,wl,wr in zl:
                assert 0<=root<=127
                z=bytearray(tz); z[0]=hi; z[1]=lo; z[4]=root; z[5]=0; z[6]=0
                struct.pack_into("<IIII",z,12,first_id+wl['page_off'],0,*wl.get('loop',(wl['b'],wl['b']))); z[28:48]=tail
                if t==2: struct.pack_into("<IIII",z,48,first_id+wr['page_off'],0,*wr.get('loop',(wr['b'],wr['b']))); z[64:84]=tail
                zb+=bytes(z)
            kb=struct.pack("<HH",len(zl),t)+zb; no=alloc(len(kb)); patch(PH,V+no,kb)
            elmap[e]=(NKM+len(newkm),no); kmmap[k]=elmap[e]; newkm.append(no)   # por elemento (elementos podem dividir o keymap de origem)
    elif vp.get('km_same'):
        for k in sorted(int(x) for x in vp['km']): kmmap[k]=(k,km[k])
    else:
      shared=None
      for k in sorted(int(x) for x in vp['km']):
        if vp.get('share') and vp['km'][str(k)]!="silence" and shared is not None: kmmap[k]=shared; continue   # camadas iguais: 1 keymap so
        o=km[k]; size,_,_=kmsize(o); no=alloc(size); patch(PH,V+no,rd(V+o,size))
        kmmap[k]=(NKM+len(newkm),no); newkm.append(no)
        if vp.get('share') and vp['km'][str(k)]!="silence": shared=kmmap[k]
    for e in range(nel if not vp.get('inplace') else 0):
        p=u32(V+so+hl+4*e); k=u16(V+p+12)
        if k in kmmap or e in elmap:
            nk_=elmap[e][0] if e in elmap else kmmap[k][0]
            size=nxt(p)-p; eb=bytearray(rd(V+p,size)); struct.pack_into("<H",eb,12,nk_)
            if vp.get('el_template') is not None:   # parametros iguais em todos os elementos copiados (menos atenuacao, faixas e keymap)
                tp=u32(V+so+hl+4*vp['el_template']); tb=rd(V+tp,size)
                keep={0,4,5,6,7,12,13}; eb=bytearray(tb[i] if i not in keep else eb[i] for i in range(size))
            if vp.get('el_att') is not None and e<len(vp['el_att']) and vp['el_att'][e] is not None: eb[0]=vp['el_att'][e]
            for off,val in vp.get('el_set',{}).items(): eb[int(off)]=val   # experimento de parametro (ex.: release)
            np_=alloc(size); patch(PH,V+np_,bytes(eb)); struct.pack_into("<I",hdr,hl+4*e,np_); newel.append(np_)
    if not vp.get('inplace'):
      while NV+len(newvo) in SKIP:   # indices 202-204 (Preset Voice) derrubam o YC (v2.03.5/7/9, v2.04.0): entradas ocultas
          di=NV+len(newvo); newvo.append(vo[0]); assert pvn+len(newpv)==di
          drow=rd(V+MAP+0x48,1)[0]; drv=struct.unpack("<128H",rd(V+MENU+256*drow,256))
          dpc=next(i for i in range(128) if drv[i]==0xffff and i not in {e[2] for e in pv+newpv if e[1]==0x48})
          patch(PH,V+MENU+256*drow+2*dpc,struct.pack("<H",di)); newpv.append(bytes([0x00,0x48,dpc])+b"Not visible".ljust(13,b"\0"))
      nb=alloc(len(hdr)); patch(PH,V+nb,bytes(hdr)); vidx=NV+len(newvo); newvo.append(nb)
      cat=vp['cat']; row=rd(V+MAP+cat,1)[0]; assert row!=0xff
      rowv=struct.unpack("<128H",rd(V+MENU+256*row,256))
      usedpc={e[2] for e in pv+newpv if e[1]==cat}
      pc=next(i for i in range(128) if rowv[i]==0xffff and i not in usedpc)
      patch(PH,V+MENU+256*row+2*pc,struct.pack("<H",vidx))
      flags=0x00   # CK (como CP): byte 0 da entrada Preset Voice e 0 em todas as voices de fabrica
      ent=bytes([flags,cat,pc])+vp['name'].encode()[:13].ljust(13,b"\0"); newpv.append(ent)
    # zonas
    if vp['kind']=="cfx":
        W=I['waves']; tail=struct.pack("<H",13)+bytes(2)+struct.pack("<6h",0,0,0,0,0,0)+bytes(4)
        for zm in I['zones']:
            nk,no=kmmap[zm['km']]; zi=zm['zi']; z=V+no+4+84*zi; e=bytearray(rd(z,84))
            pass
            wl=W[str(zm['L'])]; wr=W[str(zm['R'])]; assert wl.get('shift',0)==wr.get('shift',0)
            e[4]=zm['root']+vp.get('rootshift',0)+wl.get('shift',0); assert e[4]<=127; e[5]=0
            e[6]=struct.pack("b",int(round(zm['fine']*vp.get('finescale',0))))[0]
            struct.pack_into("<IIII",e,12,first_id+wl['page_off'],0,wl['b'],wl['b']); e[28:48]=tail
            struct.pack_into("<IIII",e,48,first_id+wr['page_off'],0,wr['b'],wr['b']); e[64:84]=tail
            patch(PH,z,bytes(e))
        for kms,vc in vp['km'].items():   # key-off do piano mudo (silencio de outro conjunto)
            if vc!="silence": continue
            sd=vp.get('silence_data',vp['data']); sf=place(sd)-WBASE
            s_=json.load(open(os.path.join(sd,"index.json")))['silence']
            nk,no=kmmap[int(kms)]; n,t=struct.unpack("<HH",rd(V+no,4)); assert t==2
            for zi in range(n):
                z=V+no+4+84*zi; e=bytearray(rd(z,84))
                struct.pack_into("<IIII",e,12,sf+s_['page_off'],0,s_['b'],s_['b']); e[28:48]=tail
                struct.pack_into("<IIII",e,48,sf+s_['page_off'],0,s_['b'],s_['b']); e[64:84]=tail
                patch(PH,z,bytes(e))
    elif vp['kind']=="eps":
        Z=I['sets'][vp['tag']]; tail=struct.pack("<H",6)+bytes(2)+struct.pack("<6h",0,0,0,0,0,0)+bytes(4)
        for kms,vc in vp['km'].items():
            nk,no=kmmap[int(kms)]; n,t=struct.unpack("<HH",rd(V+no,4)); assert t==1
            for zi in range(n):
                z=V+no+4+48*zi; e=bytearray(rd(z,48)); key=min(max(e[4],0),127)
                if vc=="silence": q=dict(I['silence'],root=60)
                else:
                    c=[q for q in Z if q['key'][0]<=key<=q['key'][1] and q['vel'][0]<=vc<=q['vel'][1]]; assert len(c)==1; q=c[0]
                e[4]=q['root']+q.get('shift',0); assert e[4]<=127; e[5]=0; e[6]=0
                struct.pack_into("<IIII",e,12,first_id+q['page_off'],0,q['b'],q['b']); e[28:48]=tail
                patch(PH,z,bytes(e))
    elif vp['kind']=="stereo":
        Z=I['sets'][vp['tag']]; tail=struct.pack("<H",13)+bytes(2)+struct.pack("<6h",0,0,0,0,0,0)+bytes(4)
        def pick(key,vc):
            c=[q for q in Z if q['vel'][0]<=vc<=q['vel'][1]]
            inside=[q for q in c if q['key'][0]<=key<=q['key'][1]]
            if inside: assert len(inside)==1; return inside[0]
            return min(c,key=lambda q: min(abs(key-q['key'][0]),abs(key-q['key'][1])))
        for kms,vc in vp['km'].items():
            nk,no=kmmap[int(kms)]; n,t=struct.unpack("<HH",rd(V+no,4)); assert t==2
            for zi in range(n):
                z=V+no+4+84*zi; e=bytearray(rd(z,84))
                if vc=="silence":
                    s=I['silence']; wl=wr=s; e[4]=60
                elif vp.get('outside')=="silence" and not any(q['key'][0]<=e[4]<=q['key'][1] for q in Z if q['vel'][0]<=vc<=q['vel'][1]):
                    s=I['silence']; wl=wr=s; e[4]=60   # fora da extensao do SF2: mudo, como no original
                else:
                    q=pick(e[4],vc); wl,wr=q['L'],q['R']; e[4]=q['root']+q['shift']; assert e[4]<=127
                e[5]=0; e[6]=0
                struct.pack_into("<IIII",e,12,first_id+wl['page_off'],0,wl['b'],wl['b']); e[28:48]=tail
                struct.pack_into("<IIII",e,48,first_id+wr['page_off'],0,wr['b'],wr['b']); e[64:84]=tail
                patch(PH,z,bytes(e))
    elif vp['kind'] in ("none","custom"): pass
    else: raise SystemExit("kind?")
    log.append(dict(name=vp['name'],vprm_idx=vidx,pv_idx=(vp['pv_src'] if vp.get('inplace') else pvn+len(newpv)-1),cat=hex(cat),row=row,pc=pc,
                    keymaps={str(k):v[0] for k,v in kmmap.items()},first_wave_id=hex(first_id),pages=I['total_pages']))
# tabela de keymaps realocada
# o firmware deduz a contagem de keymaps como (km[0]-tabela)/4 (v2.03.3/v2.03.4): keymap 0 copiado logo apos a tabela
# o campo de keymap do elemento so usa 9 bits (v2.04.3: indices >= 512 tocam outro keymap / ficam mudos):
# keymaps de conteudo identico viram um so (camadas iguais, silencios) e os indices novos ficam compactos
canon={}; remap={}; final=[]
for i,o in enumerate(newkm):
    n_,t_=struct.unpack("<HH",rd(V+o,4)); kb=rd(V+o,4+n_*(84 if t_==2 else 48))
    if kb not in canon: canon[kb]=NKM+len(final); final.append(o)
    remap[NKM+i]=canon[kb]
for p in newel:
    k=u16(V+p+12)
    if k in remap and remap[k]!=k: patch(PH,V+p+12,struct.pack("<H",remap[k]))
for l in log: l['keymaps']={a_:remap.get(b_,b_) for a_,b_ in l['keymaps'].items()}
print("keymaps novos:",len(newkm),"-> unicos:",len(final),"; maior indice:",NKM+len(final)-1, file=sys.stderr)
assert NKM+len(final)<=1024, "mais de 1024 keymaps"   # CK: fabrica ja usa 884 -> campo >= 10 bits
newkm=final
NT=NKM+len(newkm); tk=alloc(4+4*NT,16); k0=tk+4+4*NT
sz0,_,_=kmsize(km[0]); patch(PH,V+k0,rd(V+km[0],sz0)); free=k0+sz0; assert free<=VSIZE
patch(PH,V+tk,struct.pack("<I",u32(V+KT-4))+struct.pack("<I",k0)+struct.pack("<%dI"%(NKM-1),*km[1:])+struct.pack("<%dI"%len(newkm),*newkm))
patch(PH,V+0x20,struct.pack("<I",tk+4))
# tabela de offsets de voice realocada
to=alloc(4*(NV+len(newvo)),16)
patch(PH,V+to,struct.pack("<%dI"%NV,*vo)+struct.pack("<%dI"%len(newvo),*newvo))
patch(PH,V+0x2c,struct.pack("<I",to))
# Preset Voice
assert set(rd(PV+16+16*pvn,16*len(newpv)))=={0xff}
patch(PH,PV+16+16*pvn,b"".join(newpv)); patch(PH,PV+12,(pvn+len(newpv)).to_bytes(4,"big"))
# ---------- Wave: anexar + PRST ----------
end=page                                  # primeira pagina apos os dados
N=end-WBASE
tailb=(((end-1)*4096+0x2000)+0x3ffff)&~0x3ffff   # roundup 256 KB: bate com a cauda de fabrica do CK, YC e CP
tailpage=tailb//4096-1; assert tailpage>=end
newsize=(tailpage+1)*4096
f.seek(WH+0x40); s=struct.unpack("<I",f.read(4))[0]
newprst=bytearray(prst); struct.pack_into(">I",newprst,4+4*5,N)
s=(s-sum(prst)+sum(newprst))&0xffffffff; f.seek(WB); f.write(newprst)
f.seek(WB+wsize); assert f.tell()==os.path.getsize(out)
for pg,b in waveblobs:
    assert f.tell()==WB+pg*4096; f.write(b); s=(s+sum(b))&0xffffffff
pad=tailpage*4096-(end*4096); f.write(bytes(pad))
f.write(newprst); s=(s+sum(newprst))&0xffffffff
assert f.tell()==WB+newsize
f.seek(WH+0x40); f.write(struct.pack("<I",s)); f.seek(WH+0x7c); f.write(struct.pack("<I",newsize))
# versao
for hh in (0x0,0x100080,0x140100,0x2100180):
    f.seek(hh+0x18); f.write(ver.encode().ljust(8,b"\0"))
for hdr,off in ((0x100080,0x1400E0),(0x140100,0x2000160)):
    patch(hdr,off,ver.encode().ljust(8,b"\0"))
f.close()
info=dict(base=base,voices=log,vprm_free_used=hex(free),keymap_table=hex(tk+4),voice_table=hex(to),
          wave=dict(old_size=hex(wsize),new_size=hex(newsize),data_pages=hex(N),tail_page=hex(tailpage)))
json.dump(info,open(os.path.join(outdir,"info.json"),"w"),indent=1); print(json.dumps(info,indent=1))
