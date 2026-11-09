#!/usr/bin/env python3
"""Summarise key register writes from a gzipped (possibly truncated) mmiotrace.
usage: trace_regs.py trace.gz"""
import gzip,sys,collections,zlib
MMIO=0xf0300000; GTT=0xf0000000; GTT_END=GTT+0x80000
W={0x2020:'PGETBL_CTL',0x2080:'HWS_PGA',0x2030:'LP_TAIL',0x2034:'LP_HEAD',0x2038:'LP_START',0x203c:'LP_CTL',0x20c0:'0x20c0',0x209c:'0x209c',0x201c:'0x201c',0x2018:'0x2018',0x20a0:'IER',0x20a8:'IMR',
 0x70080:'CURACNTR',0x70084:'CURABASE',0x700c0:'CURBCNTR',0x700c4:'CURBBASE',0x71008:'PIPEBCONF',0x71180:'DSPBCNTR',0x71184:'DSPBBASE',0x71188:'DSPBSTRIDE',0x6018:'DPLL_B',0x6048:'FPB0',0x604c:'FPB1',0x61180:'LVDS',0x61204:'PP_CONTROL'}
def lines(p):
    d=zlib.decompressobj(31); f=open(p,'rb'); buf=b''
    while True:
        c=f.read(1<<16)
        if not c: break
        try: o=d.decompress(c)
        except zlib.error: break
        buf+=o; *ls,buf=buf.split(b'\n')
        for l in ls: yield l.decode('ascii','replace')
n=0; first={}; seen=collections.OrderedDict(); gtt=[]; marks=[]; last=None; cnt=collections.Counter()
for l in lines(sys.argv[1]):
    n+=1; p=l.split()
    if not p: continue
    if p[0] in('MAP','UNMAP','MARK'): marks.append(l[:100])
    if p[0] in('W','R') and len(p)>=6:
        try: sz,ts,_,a,v=int(p[1]),float(p[2]),p[3],int(p[4],16),int(p[5],16)
        except: continue
        last=ts
        cnt[p[0]]+=1
        if p[0]=='W' and MMIO<=a<MMIO+0x80000:
            o=a-MMIO
            if o in W: seen.setdefault(o,[]).append((ts,v))
        if p[0]=='W' and GTT<=a<GTT_END: gtt.append((ts,(a-GTT)//4,v))
print('lines',n,'events',cnt,'last ts',last)
print('\n'.join(marks[:14]))
for o,v in seen.items():
    print('%06x %-11s n=%-5d first %s ts=%.3f | last %s'%(o,W[o],len(v),hex(v[0][1]),v[0][0],hex(v[-1][1])), ' uniq', [hex(x) for x in list(dict.fromkeys(y for _,y in v))[:6]])
print('gtt writes',len(gtt))
want=[0x23,0x2,0x20,0x21,0x22,0x24,0]
last=dict()
for ts,i,v in gtt: last[i]=(ts,v)
for i in sorted(want): print('pte',hex(i),hex(i<<12),'->',hex(last[i][1]) if i in last else None)
print('sample ptes',[(hex(i),hex(last[i][1])) for i in sorted(last)[:12]])
