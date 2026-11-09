#!/usr/bin/env python3
"""Stage-2 patch for AppleIntelIntegratedFramebuffer (10A432, thin i386). File offsets.
 ID spoof in probe/start; FPB0 and DPLL_B forced to the values Linux i915 used for
 the NC10 Plus panel (1024x600, 54.2 MHz); cursors use GTT addresses.  usage: patch_fb.py IN OUT"""
from __future__ import print_function  # runs on Python 3 and on the Python 2.6 in Mac OS X 10.6
import binascii,struct,sys
def unhex(s): return binascii.unhexlify(s.replace(' ','').encode('ascii'))
def unpack(f,b): return struct.unpack(f,bytes(b))
ID=unhex('b88680a227')
P=[
 ('probe: ID read',0x2dec,'ff90bc040000',ID+b'\x90'),
 ('start: ID read',0x68f2,'8b108b92bc040000',ID+b'\x90\x90\x90'),
 ('start: drop call edx',0x6905,'ffd2',b'\x90\x90'),
 ('hwSetCRTC: FPB0=0x80059',0xa7d5,'8b93d8000000',unhex('ba5900080090')),
 ('hwSetCRTC: DPLL_B=0x98046000',0xa7e4,'8b93d4000000',unhex('ba0060049890')),
 ('hwSetupMemory: cursor bases from GTT offset',0x4711,None,unhex(
   '8b4d08'        # mov ecx,[ebp+8]
   '8b4160'        # mov eax,[ecx+0x60]    ; GTT address of the 1 MB region
   '898104010000'  # mov [ecx+0x104],eax
   '0500000400'    # add eax,0x40000
   '898108010000'  # mov [ecx+0x108],eax
   '0500000400'    # add eax,0x40000
   '89817c010000'  # mov [ecx+0x17c],eax
   '0500000400'    # add eax,0x40000
   'eb0d'          # jmp 0x4747
   '909090')),
 ('hwSetupMemory: last cursor base',0x4747,None,unhex('898180010000eb0c')),
 ('hwSetPowerState: skip palette save on pipe A (unclocked, Linux guards this)',0xb2fa,
  '8b4758'+'c780a8200000ffffffff'+'8b4758'+'c780a020000000000000'+'c7042400040000',unhex(
   '8b4758'                # mov eax,[edi+0x58]
   'c780a8200000ffffffff'  # mov dword [eax+0x20a8],-1   ; IMR, as stock
   '8998a0200000'          # mov [eax+0x20a0],ebx        ; IER=0, ebx is 0 here
   '837d1400'              # cmp dword [ebp+0x14],0      ; pipe A?
   '7452'                  # je 0xb365                   ; skip IOMalloc and the palette loop
   'c7042400040000'        # mov dword [esp],0x400
   '90')),
]
d=bytearray(open(sys.argv[1],'rb').read())
ncmds=unpack('<I',d[16:20])[0]; p=28; rel=set()
for _ in range(ncmds):
    cmd,sz=unpack('<II',d[p:p+8])
    if cmd==1:
        for i in range(unpack('<I',d[p+48:p+52])[0]):
            q=p+56+68*i
            if d[q:q+16].rstrip(b'\0')==b'__text':
                a,s,o,al,ro,nr=unpack('<6I',d[q+32:q+56])
                for k in range(nr):
                    w0,w1=unpack('<II',d[ro+8*k:ro+8*k+8])
                    rel.add((w0&0xffffff if w0&0x80000000 else w0)+o-a)
    p+=sz
for name,off,old,new in P:
    if old is not None:
        o=unhex(old); assert bytes(d[off:off+len(o)])==o and len(o)==len(new),name
    bad=[r for r in rel if off-3<=r<off+len(new)]; assert not bad,(name,[hex(x) for x in bad])
    d[off:off+len(new)]=new; print('ok',hex(off),name)
open(sys.argv[2],'wb').write(d)
