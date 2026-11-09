#!/usr/bin/env python3
"""Drop impossible per-packet position jumps in VoodooPS2Trackpad 1.1.0 (i386 slice of the fat binary).
 A second finger on this Synaptics pad moves the reported point to somewhere between the fingers, and the
 stock move code sends that leap to the cursor. After packet decode, if X or Y moved more than LIMIT units since
 the last packet, last-X/last-Y (this+0x108/0x10c) are re-based so the driver computes a zero delta.
 The code lives in ApplePS2ALPSGlidePoint::dispatchRelativePointerEventWithPacket, unused on a Synaptics pad.
 usage: patch_trackpad.py IN OUT [LIMIT]   (default 300 units per packet)"""
from __future__ import print_function  # runs on Python 3 and on the Python 2.6 in Mac OS X 10.6
import binascii,struct,sys
def unhex(s): return binascii.unhexlify(s.replace(' ','').encode('ascii'))
def unpack(f,b): return struct.unpack(f,bytes(b))
TO=756              # __text file offset in the slice, vmaddr 0
HOOK,RET=0x182c,0x1832
CAVE=0x4902
HOOK_OLD='8945d4 8b4508'                     # mov [ebp-0x2c],eax / mov eax,[ebp+8]
CAVE_OLD='5589e553 83ec44 c745f400000000'    # ALPS handler prologue
limit=int(sys.argv[3],0) if len(sys.argv)>3 else 300
lim=binascii.hexlify(struct.pack('<I',limit)).decode('ascii')
code=unhex(''.join([
 '8945d4',                   # mov [ebp-0x2c],eax    displaced: store W
 '8b5508',                   # mov edx,[ebp+8]       this
 '8b45e0',                   # mov eax,[ebp-0x20]    x
 '2b8208010000',             # sub eax,[edx+0x108]   last x
 '7902','f7d8',              # jns +2 / neg eax
 '3d'+lim,                   # cmp eax,LIMIT
 '7f14',                     # jg rebase
 '8b45dc',                   # mov eax,[ebp-0x24]    y
 '2b820c010000',             # sub eax,[edx+0x10c]   last y
 '7902','f7d8',              # jns +2 / neg eax
 '3d'+lim,                   # cmp eax,LIMIT
 '7e12',                     # jle done
 '8b45e0','898208010000',    # rebase: last x = x
 '8b45dc','89820c010000',    #         last y = y
 '8b4508',                   # done: mov eax,[ebp+8] displaced
]))
end=CAVE+len(code)+5
code+=b'\xe9'+struct.pack('<i',RET-end)
hook=b'\xe9'+struct.pack('<i',CAVE-(HOOK+5))+b'\x90'
d=bytearray(open(sys.argv[1],'rb').read())
assert unpack('>I',d[:4])[0]==0xcafebabe
base=None
for i in range(unpack('>I',d[4:8])[0]):
    c,s,o,sz,a=unpack('>5I',d[8+20*i:28+20*i])
    if c==7: base=o
assert base is not None
ncmds=unpack('<I',d[base+16:base+20])[0]; p=base+28; rel=set()
for _ in range(ncmds):
    cmd,sz=unpack('<II',d[p:p+8])
    if cmd==1:
        for i in range(unpack('<I',d[p+48:p+52])[0]):
            q=p+56+68*i
            if d[q:q+16].rstrip(b'\0')==b'__text':
                a,s,o,al,ro,nr=unpack('<6I',d[q+32:q+56]); assert (a,o)==(0,TO)
                for k in range(nr):
                    w0,w1=unpack('<II',d[base+ro+8*k:base+ro+8*k+8])
                    rel.add(w0&0xffffff if w0&0x80000000 else w0)
    p+=sz
for name,va,old,new in (('hook',HOOK,HOOK_OLD,hook),('cave',CAVE,CAVE_OLD,code)):
    o=unhex(old.replace(' ','')); off=base+TO+va
    assert bytes(d[off:off+len(o)])==o,(name,binascii.hexlify(bytes(d[off:off+len(o)])))
    bad=[hex(r) for r in rel if va-3<=r<va+len(new)]; assert not bad,(name,bad)
    d[off:off+len(new)]=new
    print(name,hex(va),len(new),'bytes')
open(sys.argv[2],'wb').write(d); print('limit',limit)
