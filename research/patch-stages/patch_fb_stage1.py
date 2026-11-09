#!/usr/bin/env python3
"""Stage-1 patch for AppleIntelIntegratedFramebuffer (10A432, thin i386). File offsets.
 ID spoof in probe/start; FPB0 and DPLL_B forced to the values Linux i915 used for
 the NC10 Plus panel (1024x600, 54.2 MHz).  usage: patch_fb.py IN OUT"""
import struct,sys
ID=bytes.fromhex('b88680a227')
P=[
 ('probe: ID read',0x2dec,'ff90bc040000',ID+b'\x90'),
 ('start: ID read',0x68f2,'8b108b92bc040000',ID+b'\x90\x90\x90'),
 ('start: drop call edx',0x6905,'ffd2',b'\x90\x90'),
 ('hwSetCRTC: FPB0=0x80059',0xa7d5,'8b93d8000000',bytes.fromhex('ba5900080090')),
 ('hwSetCRTC: DPLL_B=0x98046000',0xa7e4,'8b93d4000000',bytes.fromhex('ba0060049890')),
]
d=bytearray(open(sys.argv[1],'rb').read())
ncmds=struct.unpack('<I',d[16:20])[0]; p=28; rel=set()
for _ in range(ncmds):
    cmd,sz=struct.unpack('<II',d[p:p+8])
    if cmd==1:
        for i in range(struct.unpack('<I',d[p+48:p+52])[0]):
            q=p+56+68*i
            if d[q:q+16].rstrip(b'\0')==b'__text':
                a,s,o,al,ro,nr=struct.unpack('<6I',d[q+32:q+56])
                for k in range(nr):
                    w0,w1=struct.unpack('<II',d[ro+8*k:ro+8*k+8])
                    rel.add((w0&0xffffff if w0&0x80000000 else w0)+o-a)
    p+=sz
for name,off,old,new in P:
    o=bytes.fromhex(old); assert bytes(d[off:off+len(o)])==o and len(o)==len(new),name
    bad=[r for r in rel if off-3<=r<off+len(new)]; assert not bad,(name,[hex(x) for x in bad])
    d[off:off+len(o)]=new; print('ok',hex(off),name)
open(sys.argv[2],'wb').write(d)
