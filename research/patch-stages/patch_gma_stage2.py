#!/usr/bin/env python3
"""Stage-2a patch for the thin i386 AppleIntelGMA950 binary (10A432), file offsets.
Forces the PCI ID to 0x27A28086 in probe and start, and makes start fail at
initialize_hardware (after logging) before the ring or status page are programmed.
usage: patch_gma.py IN OUT"""
import sys
ID=bytes.fromhex('b88680a227')
P=[
 ('probe: ID read -> mov eax,ID',0x1bf76,'ff90bc040000',ID+b'\x90'),
 ('start: load vtable slot -> mov eax,ID',0x1c35d,'8b008b80bc040000',ID+b'\x90\x90\x90'),
 ('start: drop call eax',0x1c370,'ffd0',b'\x90\x90'),
 ('start: remove skip 1',0x1c95b,'0f84e0010000',b'\x90'*6),
 ('start: remove skip 2',0x1c969,'0f84d2010000',b'\x90'*6),
 ('initialize_hardware: jump to its IOLog',0x19da9,None,bytes.fromhex('e9e0000000')),
 ('after IOLog: return 0 before touching 0x2030',0x19eae,'8b55088b',bytes.fromhex('31c0eb14')),
]
d=bytearray(open(sys.argv[1],'rb').read())
for name,off,old,new in P:
    if old is None:
        print('replacing',bytes(d[off:off+len(new)]).hex()); d[off:off+len(new)]=new; print('ok',hex(off),name); continue
    o=bytes.fromhex(old); assert bytes(d[off:off+len(o)])==o and len(o)==len(new),name
    d[off:off+len(o)]=new; print('ok',hex(off),name)
open(sys.argv[2],'wb').write(d)
