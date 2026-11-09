# Runs on the netbook in the desktop session (Python 2.6): Core Image GPU vs CPU, plus a GL soak.
import time,sys
from ctypes import *
import objc,Quartz
from Quartz import CIContext,CIFilter,CIVector,CGColorSpaceCreateDeviceRGB,CGBitmapContextCreate,CGRectMake
def run(sw):
    cs=CGColorSpaceCreateDeviceRGB(); bm=CGBitmapContextCreate(None,640,480,8,640*4,cs,2)
    c=CIContext.contextWithCGContext_options_(bm,{'kCIContextUseSoftwareRenderer':sw})
    g=CIFilter.filterWithName_('CICheckerboardGenerator'); g.setDefaults()
    b=CIFilter.filterWithName_('CIGaussianBlur'); b.setDefaults(); b.setValue_forKey_(g.valueForKey_('outputImage'),'inputImage'); b.setValue_forKey_(8.0,'inputRadius')
    img=b.valueForKey_('outputImage'); t=time.time(); n=0
    while time.time()-t<4:
        c.drawImage_inRect_fromRect_(img,CGRectMake(0,0,640,480),CGRectMake(0,0,640,480)); Quartz.CGContextFlush(bm); n+=1
    return n/(time.time()-t)
try:
    print 'CI gpu-requested fps %.1f'%run(False); print 'CI software fps %.1f'%run(True)
except Exception,e: print 'CI test error',repr(e)[:200]
L=cdll.LoadLibrary('/System/Library/Frameworks/OpenGL.framework/OpenGL')
A=(c_int*5)(73,72,90,0,0); pf=c_void_p(); np=c_int(0); L.CGLChoosePixelFormat(A,byref(pf),byref(np))
ctx=c_void_p(); L.CGLCreateContext(pf,None,byref(ctx)); L.CGLSetCurrentContext(ctx)
pb=c_void_p(); L.CGLCreatePBuffer(256,256,0x0DE1,0x1908,0,byref(pb)); s=c_int(0); L.CGLGetVirtualScreen(ctx,byref(s)); L.CGLSetPBuffer(ctx,pb,0,0,s.value)
L.glGetString.restype=c_char_p; ext=L.glGetString(0x1F03)
print 'fragment programs:', 'GL_ARB_fragment_program' in ext, 'vertex programs:','GL_ARB_vertex_program' in ext
L.glViewport(0,0,256,256); t=time.time(); n=0
while time.time()-t<30:
    L.glClearColor(c_float((n%60)/60.0),c_float(0.3),c_float(0.5),c_float(1.0)); L.glClear(0x4000)
    L.glBegin(4)
    for i in range(30):
        L.glColor3f(c_float(1),c_float(0),c_float(0)); L.glVertex2f(c_float(-1),c_float(-1)); L.glVertex2f(c_float(1),c_float(-1)); L.glVertex2f(c_float(0),c_float(1))
    L.glEnd(); L.glFinish(); n+=1
print 'GL soak frames',n,'fps %.1f'%(n/30.0),'glError',L.glGetError(); print 'DONE'
