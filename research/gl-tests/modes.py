# List display modes; with argument "cycle" switch through them, restoring native. (Python 2.6, desktop session)
from ctypes import *
import sys,time
CF=cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'); CG=cdll.LoadLibrary('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
for f in ('CFArrayGetValueAtIndex','CFDictionaryGetValue','CFStringCreateWithCString'): getattr(CF,f).restype=c_void_p
CF.CFArrayGetCount.argtypes=[c_void_p]; CG.CGDisplayAvailableModes.restype=c_void_p; CG.CGDisplayCurrentMode.restype=c_void_p
d=CG.CGMainDisplayID(); k=lambda n:c_void_p(CF.CFStringCreateWithCString(None,n,0x600))
def num(m,n):
    v=c_int(0); x=CF.CFDictionaryGetValue(c_void_p(m),k(n))
    if x: CF.CFNumberGetValue(c_void_p(x),9,byref(v))
    return v.value
def desc(m): return (num(m,'Width'),num(m,'Height'),num(m,'BitsPerPixel'),num(m,'RefreshRate'))
arr=CG.CGDisplayAvailableModes(d); n=CF.CFArrayGetCount(arr); modes=[CF.CFArrayGetValueAtIndex(c_void_p(arr),c_int(i)) for i in range(n)]
print 'count',n; cur=CG.CGDisplayCurrentMode(d); print 'current',desc(cur)
for i,m in enumerate(modes): print i,desc(m)
if len(sys.argv)>1 and sys.argv[1]=='cycle':
    CG.CGDisplaySwitchToMode.argtypes=[c_uint32,c_void_p]; seen=set()
    for m in modes:
        dsc=desc(m)
        if dsc[:3] in seen: continue
        seen.add(dsc[:3]); print time.strftime('%H:%M:%S'),'switch',dsc,'err',CG.CGDisplaySwitchToMode(d,m); sys.stdout.flush(); time.sleep(5)
    print time.strftime('%H:%M:%S'),'restore',desc(cur),'err',CG.CGDisplaySwitchToMode(d,cur); time.sleep(3); print 'DONE'
