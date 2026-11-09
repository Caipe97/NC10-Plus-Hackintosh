#!/usr/bin/env python3
"""Summarise bundle identity and PCI matching. usage: ids.py Info.plist..."""
import plistlib,sys
K=('IOPCIMatch','IOPCIPrimaryMatch','IOProviderClass','IOClass','IOProbeScore','IOGLBundleName','IOVARendererID','IOVABundleName','IOMatchCategory','IOSourceVersion')
for f in sys.argv[1:]:
    p=plistlib.load(open(f,'rb'))
    print(p.get('CFBundleIdentifier'),p.get('CFBundleVersion'),'exe=',p.get('CFBundleExecutable'))
    for n,v in (p.get('IOKitPersonalities') or dict()).items():
        print('  personality',n,dict((x,v[x]) for x in v if x in K))
    print('  libs',p.get('OSBundleLibraries'))
