# Runs on the netbook inside the desktop session (Python 2.6).
from ctypes import *
CG=cdll.LoadLibrary('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
L=cdll.LoadLibrary('/System/Library/Frameworks/OpenGL.framework/OpenGL')
d=CG.CGMainDisplayID(); print 'display',hex(d&0xffffffff)
CG.CGDisplayUsesOpenGLAcceleration.restype=c_int
print 'Quartz Extreme (CGDisplayUsesOpenGLAcceleration):',CG.CGDisplayUsesOpenGLAcceleration(d)
A=(c_int*6)(73,72,5,0,0,0)     # accelerated, no-recovery, doublebuffer off slot, pbuffer below
A=(c_int*5)(73,72,90,0,0)      # kCGLPFAPBuffer=90
pf=c_void_p(); np=c_int(0); print 'choose',L.CGLChoosePixelFormat(A,byref(pf),byref(np)),np.value
ctx=c_void_p(); print 'create',L.CGLCreateContext(pf,None,byref(ctx)); print 'current',L.CGLSetCurrentContext(ctx)
pb=c_void_p(); print 'pbuffer',L.CGLCreatePBuffer(64,64,0x0DE1,0x1908,0,byref(pb))
scr=c_int(0); print 'virtual screen',L.CGLGetVirtualScreen(ctx,byref(scr)),scr.value
print 'setpb',L.CGLSetPBuffer(ctx,pb,0,0,scr.value)
L.glGetString.restype=c_char_p; print 'renderer',L.glGetString(0x1F01)
L.glViewport(0,0,64,64); L.glClearColor(c_float(0.1),c_float(0.2),c_float(0.3),c_float(1.0)); L.glClear(0x4000)
# flat red triangle covering the lower-left half
L.glMatrixMode(0x1701); L.glLoadIdentity(); L.glOrtho(c_double(0),c_double(1),c_double(0),c_double(1),c_double(-1),c_double(1))
L.glMatrixMode(0x1700); L.glLoadIdentity(); L.glDisable(0x0B71)
L.glColor3f(c_float(1.0),c_float(0.0),c_float(0.0)); L.glBegin(4)
L.glVertex2f(c_float(0),c_float(0)); L.glVertex2f(c_float(1),c_float(0)); L.glVertex2f(c_float(0),c_float(1)); L.glEnd()
L.glFinish(); print 'glError',L.glGetError()
p=(c_ubyte*4)(); L.glReadPixels(5,5,1,1,0x1908,0x1401,byref(p)); print 'inside triangle (want 255 0 0):',list(p)
p=(c_ubyte*4)(); L.glReadPixels(60,60,1,1,0x1908,0x1401,byref(p)); print 'cleared corner (want ~26 51 77):',list(p)
print 'DONE'
