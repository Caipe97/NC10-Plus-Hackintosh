#!/usr/bin/env python3
"""List relocation addresses in __text of a thin i386 Mach-O object. usage: relocs.py BIN START END (section-relative)"""
import struct,sys
d=open(sys.argv[1],'rb').read(); lo,hi=int(sys.argv[2],0),int(sys.argv[3],0)
ncmds=struct.unpack('<I',d[16:20])[0]; p=28
for _ in range(ncmds):
    cmd,sz=struct.unpack('<II',d[p:p+8])
    if cmd==1:
        for i in range(struct.unpack('<I',d[p+48:p+52])[0]):
            q=p+56+68*i
            if d[q:q+16].rstrip(b'\0')==b'__text':
                a,s,o,al,ro,nr=struct.unpack('<6I',d[q+32:q+56])
                out=[]
                for k in range(nr):
                    w0,w1=struct.unpack('<II',d[ro+8*k:ro+8*k+8])
                    ad=w0&0xffffff if w0&0x80000000 else w0
                    if lo<=ad<hi: out.append(ad)
                print('nreloc',nr,'in range',sorted(set(out)))
    p+=sz
