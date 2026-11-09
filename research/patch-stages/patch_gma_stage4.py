#!/usr/bin/env python3
"""Stage-4 patch for the thin i386 AppleIntelGMA950 binary (10A432). File offsets.
 ID spoof in probe/start; status page via GTT slot 0x1fffe; ring started like Linux;
 initialize_hardware submits Apple's real 3D tables, waits, logs HEAD and EIR, returns 0 so start
 fails cleanly through Apple's stop path.  usage: patch_gma.py IN OUT"""
import struct,sys
ID=bytes.fromhex('b88680a227')
HWS=bytes.fromhex(
 '8b83480a0000'     # mov eax,[ebx+0xa48]        ; phys of status page
 '83c807'           # or  eax,7                  ; valid + snooped, as i915 did
 '8b8be8090000'     # mov ecx,[ebx+0x9e8]        ; GTT mapping
 '8981f8ff0700'     # mov [ecx+0x7fff8],eax      ; PTE for slot 0x1fffe
 '8b8be4090000'     # mov ecx,[ebx+0x9e4]        ; registers
 'c781802000 0000e0ff1f'.replace(' ','')+
 '8b8180200000'     # mov eax,[ecx+0x2080]       ; posting read
 '8b83ec090000'     # mov eax,[ebx+0x9ec]        ; what the next compare expects
 '90909090')
CAVEA=bytes.fromhex(
 '8b5508'        # mov edx,[ebp+8]
 '8b82e4090000'  # mov eax,[edx+0x9e4]
 '899830200000'  # mov [eax+0x2030],ebx ; tail: go
 'b900000008'    # mov ecx,0x8000000
 'e2fe'          # loop $
 'eb34')         # jmp cave B at 0x19194
CAVEB=bytes.fromhex(
 '8b8834200000'  # mov ecx,[eax+0x2034] ; HEAD
 '894c2408'      # mov [esp+8],ecx
 '8b88b0200000'  # mov ecx,[eax+0x20b0] ; EIR
 '894c240c'      # mov [esp+0xc],ecx
 'e9ed0c0000')   # jmp 0x19e9a
P=[
 ('probe: ID read -> mov eax,ID',0x1bf76,'ff90bc040000',ID+b'\x90'),
 ('start: load slot -> mov eax,ID',0x1c35d,'8b008b80bc040000',ID+b'\x90\x90\x90'),
 ('start: drop call eax',0x1c370,'ffd0',b'\x90\x90'),
 ('start: remove skip 1',0x1c95b,'0f84e0010000',b'\x90'*6),
 ('start: remove skip 2',0x1c969,'0f84d2010000',b'\x90'*6),
 ('engine: status page through GTT',0x19111,None,HWS),
 ('engine: skip 0x201c/0x2018 writes',0x19146,None,b'\xeb\x65'),
 ('cave A: kick, delay',0x19148,None,CAVEA),
 ('cave B: read HEAD EIR',0x19194,None,CAVEB),
 ('engine: skip IP ring and 0x20c0',0x19221,None,b'\xeb\x72'),
 ('init_hw: skip display setup (no framebuffer yet)',0x19db4,None,b'\xeb\x19'),
 ('init_hw: to cave A',0x19e7e,'8b55088b82',bytes.fromhex('e9c5f2ffff')),
 ('after IOLog: return 0',0x19eae,'8b55088b',bytes.fromhex('31c0eb14')),
]
d=bytearray(open(sys.argv[1],'rb').read())
ncmds=struct.unpack('<I',d[16:20])[0]; p=28; rel=set(); delta=None
for _ in range(ncmds):
    cmd,sz=struct.unpack('<II',d[p:p+8])
    if cmd==1:
        for i in range(struct.unpack('<I',d[p+48:p+52])[0]):
            q=p+56+68*i
            if d[q:q+16].rstrip(b'\0')==b'__text':
                a,s,o,al,ro,nr=struct.unpack('<6I',d[q+32:q+56]); delta=o-a
                for k in range(nr):
                    w0,w1=struct.unpack('<II',d[ro+8*k:ro+8*k+8])
                    rel.add((w0&0xffffff if w0&0x80000000 else w0)+delta)
    p+=sz
for name,off,old,new in P:
    if old is not None:
        o=bytes.fromhex(old); assert bytes(d[off:off+len(o)])==o and len(o)==len(new),name
    bad=[r for r in rel if off-3<=r<off+len(new)]
    assert not bad,(name,[hex(x) for x in bad])
    d[off:off+len(new)]=new; print('ok',hex(off),len(new),name)
assert len(HWS)==53; assert len(CAVEA)==24; assert len(CAVEB)==25
assert 0x19148+24+CAVEA[-1]==0x19194,'cave A jump target'
assert 0x19194+25+int.from_bytes(CAVEB[-4:],'little')==0x19e9a,'cave B jump target'
assert 0x19e83+int.from_bytes(bytes.fromhex('c5f2ffff'),'little',signed=True)==0x19148,'entry jump target'
open(sys.argv[2],'wb').write(d)
