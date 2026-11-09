#!/usr/bin/env python3
"""Accelerator patch for the thin i386 AppleIntelGMA950 binary (10A432). File offsets.
 ID spoof in probe/start; status page via GTT slot 0x1fffe; ring started like Linux;
 Apple's fence 6/7 setup is kept, because its tiled pools depend on it.  usage: patch_gma.py IN OUT"""
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
P=[
 ('probe: ID read -> mov eax,ID',0x1bf76,'ff90bc040000',ID+b'\x90'),
 ('start: load slot -> mov eax,ID',0x1c35d,'8b008b80bc040000',ID+b'\x90\x90\x90'),
 ('start: drop call eax',0x1c370,'ffd0',b'\x90\x90'),
 ('engine: status page through GTT',0x19111,None,HWS),
 ('engine: skip IP ring and 0x20c0',0x19221,None,b'\xeb\x72'),
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
assert len(HWS)==53
open(sys.argv[2],'wb').write(d)
