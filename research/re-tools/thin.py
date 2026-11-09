#!/usr/bin/env python3
"""Extract the i386 slice from every Mach-O universal binary given. usage: thin.py OUTDIR FILE..."""
import struct,sys,os
out=sys.argv[1]
for f in sys.argv[2:]:
    d=open(f,'rb').read()
    magic=struct.unpack('>I',d[:4])[0]
    if magic!=0xcafebabe: print(f,'not fat',hex(magic)); continue
    n=struct.unpack('>I',d[4:8])[0]; arches=[]
    for i in range(n):
        c,s,o,sz,a=struct.unpack('>5I',d[8+20*i:28+20*i]); arches.append((c,o,sz))
        if c==7:
            p=os.path.join(out,os.path.basename(f)+'.i386'); open(p,'wb').write(d[o:o+sz]); print(p,sz)
    print(os.path.basename(f),[hex(a[0]) for a in arches])
