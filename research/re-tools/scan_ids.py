#!/usr/bin/env python3
"""Find little-endian PCI IDs (device<<16|vendor, and bare device word) in binaries. usage: scan_ids.py FILE..."""
import struct,sys,re
ID=[0x2582,0x2592,0x2772,0x27A2,0x27AE,0xA001,0xA011,0xA002,0xA012]
for f in sys.argv[1:]:
    d=open(f,'rb').read()
    print(f.rsplit('/',1)[-1],len(d))
    for i in ID:
        full=[m.start() for m in re.finditer(re.escape(struct.pack('<I',(i<<16)|0x8086)),d)]
        word=[m.start() for m in re.finditer(re.escape(struct.pack('<H',i)),d)]
        cmp32=[m.start() for m in re.finditer(re.escape(b'\x81')+b'[\xf8-\xff]'+re.escape(struct.pack('<I',(i<<16)|0x8086)),d)]
        print('  %04x vendor-pair@%s cmp-imm@%s word-hits=%d'%(i,[hex(x) for x in full[:8]],[hex(x) for x in cmp32[:8]],len(word)))
