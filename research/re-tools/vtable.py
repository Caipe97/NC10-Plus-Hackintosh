#!/usr/bin/env python3
"""Resolve a vtable byte offset to a method name in an i386 Mach-O object.
usage: vtable.py BINARY VTABLE_SYMBOL OFFSET [OFFSET...]  (OFFSET counted from the object's vptr)"""
import struct,sys
d=open(sys.argv[1],'rb').read(); base=0
if struct.unpack('>I',d[:4])[0]==0xcafebabe:
    for i in range(struct.unpack('>I',d[4:8])[0]):
        c,s,o,sz,a=struct.unpack('>5I',d[8+20*i:28+20*i])
        if c==7: base=o
m=struct.unpack('<I',d[base:base+4])[0]; assert m==0xfeedface,hex(m)
nc=struct.unpack('<I',d[base+16:base+20])[0]; p=base+28; secs=[]; sym=None
for _ in range(nc):
    cmd,sz=struct.unpack('<II',d[p:p+8])
    if cmd==1:
        ns=struct.unpack('<I',d[p+48:p+52])[0]
        for i in range(ns):
            q=p+56+68*i; n=d[q:q+16].rstrip(b'\0').decode(); a,s,o,al,ro,nr=struct.unpack('<6I',d[q+32:q+56]); secs.append((n,a,s,ro,nr,o))
    if cmd==2: sym=struct.unpack('<4I',d[p+8:p+24])
    p+=sz
so,ns,st,_=sym; syms=[]
for i in range(ns):
    x,t,sc,de,v=struct.unpack('<IBBHI',d[base+so+12*i:base+so+12*i+12]); e=d.index(b'\0',base+st+x); syms.append((d[base+st+x:e].decode(),t,sc,v))
tv=[s for s in syms if s[0]==sys.argv[2]]; print('vtable',tv)
_,_,sc,va=tv[0]; n,a,s,ro,nr,fo=secs[sc-1]; rel={}
byval=dict((x[3],x[0]) for x in syms if x[1]&0x0e==0x0e)
print('section',n,'vaddr',hex(a))
for i in range(nr):
    w0,w1=struct.unpack('<II',d[base+ro+8*i:base+ro+8*i+8])
    if w0&0x80000000: continue
    if (w1>>27)&1: rel[w0]=syms[w1&0xffffff][0]
for off in sys.argv[3:]:
    o=int(off,0)
    for k in(-8,-4,0,4,8):
        q=(va-a)+8+o+k; w=struct.unpack('<I',d[base+fo+q:base+fo+q+4])[0]
        print(hex(o+k),rel.get(q) or byval.get(w) or hex(w))
