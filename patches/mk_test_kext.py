#!/usr/bin/env python3
"""Build a test copy of a stock kext with extra PCI IDs in its match list.
usage: mk_test_kext.py SRC.kext OUTDIR PCI_ID [PCI_ID...]   e.g. 0xA0118086"""
import os,plistlib,shutil,sys
src,out=sys.argv[1],sys.argv[2]
dst=os.path.join(out,os.path.basename(src))
shutil.rmtree(dst,ignore_errors=True); shutil.copytree(src,dst)
shutil.rmtree(os.path.join(dst,'Contents','_CodeSignature'),ignore_errors=True)
p=os.path.join(dst,'Contents','Info.plist')
if not os.path.exists(p): p=os.path.join(dst,'Info.plist')
d=plistlib.load(open(p,'rb'))
for name,v in d['IOKitPersonalities'].items():
    if 'IOPCIPrimaryMatch' in v:
        have=v['IOPCIPrimaryMatch'].split()
        for i in sys.argv[3:]:
            if i not in have: have.append(i)
        v['IOPCIPrimaryMatch']=' '.join(have); print(name,v['IOPCIPrimaryMatch'])
plistlib.dump(d,open(p,'wb'))
