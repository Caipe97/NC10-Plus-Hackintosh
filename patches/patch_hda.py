#!/usr/bin/env python3
"""Clamp AppleHDAWidget::initForNodeID's processing-coefficient count to 32 (AppleHDA 1.7.4a1, 10A432).
 The stock code aborts codec setup when the count exceeds its 32-entry array; the ALC269 does.
 Patches the i386 slice of a fat AppleHDA binary, keeping clear of relocated bytes.
 usage: patch_hda.py IN OUT"""
import struct,sys
P=[
 # 1cb02: movzx eax,[edi+0x91] / cmp eax,32 / jbe 1cb13 / mov eax,32 / jmp 1cb22 / nop
 ('clamp count to 32',0x1cb02,'0fb6879100000089 87a000000031f683f820764d',
   '0fb68791000000 83f820 7605 b820000000 eb0d 90'),
 # 1cb22: mov [edi+0xa0],eax / xor esi,esi / jmp 1cb63 / nop nop
 ('store count, enter loop',0x1cb22,'c745c8bc0200e0e9a6010000',
   '8987a000000031f6eb379090'),
]
d=bytearray(open(sys.argv[1],'rb').read())
assert struct.unpack('>I',d[:4])[0]==0xcafebabe
n=struct.unpack('>I',d[4:8])[0]; base=size=None
for i in range(n):
    c,s,o,sz,a=struct.unpack('>5I',d[8+20*i:28+20*i])
    if c==7: base,size=o,sz
assert base is not None
TO=0x37c  # __text file offset in the slice, vmaddr 0
ncmds=struct.unpack('<I',d[base+16:base+20])[0]; p=base+28; rel=set()
for _ in range(ncmds):
    cmd,sz=struct.unpack('<II',d[p:p+8])
    if cmd==1:
        for i in range(struct.unpack('<I',d[p+48:p+52])[0]):
            q=p+56+68*i
            if d[q:q+16].rstrip(b'\0')==b'__text':
                a,s,o,al,ro,nr=struct.unpack('<6I',d[q+32:q+56]); assert (a,o)==(0,TO)
                for k in range(nr):
                    w0,w1=struct.unpack('<II',d[base+ro+8*k:base+ro+8*k+8])
                    rel.add(w0&0xffffff if w0&0x80000000 else w0)
    p+=sz
for name,va,old,new in P:
    o=bytes.fromhex(old.replace(' ','')); b=bytes.fromhex(new.replace(' ',''))
    off=base+TO+va
    assert len(b)==len(o),name
    assert bytes(d[off:off+len(o)])==o,(name,bytes(d[off:off+len(o)]).hex())
    bad=[hex(r) for r in rel if va-3<=r<va+len(b)]; assert not bad,(name,bad)
    d[off:off+len(b)]=b; print('ok',hex(va),name,len(o),len(b))
open(sys.argv[2],'wb').write(d)
