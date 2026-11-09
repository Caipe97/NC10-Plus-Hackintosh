# Runs on the netbook (Python 2.6). Reports OpenGL renderers and tries a hardware-only context.
from ctypes import *
L=cdll.LoadLibrary('/System/Library/Frameworks/OpenGL.framework/OpenGL')
r=c_void_p(); n=c_int(0)
print 'query', L.CGLQueryRendererInfo(0xffffffff,byref(r),byref(n)),'renderers',n.value
for i in range(n.value):
    a=c_int(0); rid=c_int(0); mem=c_int(0); acc=c_int(0)
    L.CGLDescribeRenderer(r,i,70,byref(rid)); L.CGLDescribeRenderer(r,i,73,byref(acc)); L.CGLDescribeRenderer(r,i,120,byref(mem))
    print ' renderer',i,hex(rid.value&0xffffffff),'accelerated',acc.value,'vram',mem.value
A=(c_int*4)(73,72,0,0)   # accelerated, no-recovery
pf=c_void_p(); np=c_int(0)
print 'choose',L.CGLChoosePixelFormat(A,byref(pf),byref(np)),'pixel formats',np.value
if not pf.value: raise SystemExit('no hardware pixel format')
ctx=c_void_p(); print 'create',L.CGLCreateContext(pf,None,byref(ctx)); print 'current',L.CGLSetCurrentContext(ctx)
L.glGetString.restype=c_char_p
for k,v in (('vendor',0x1F00),('renderer',0x1F01),('version',0x1F02)): print k,L.glGetString(v)
print 'extensions',len((L.glGetString(0x1F03) or '').split())
L.glClearColor(c_float(0.1),c_float(0.2),c_float(0.3),c_float(1.0)); L.glClear(0x4000); L.glFinish()
print 'glError',L.glGetError(); print 'DONE'
