# Core Image rendering into a hardware GL context, GPU vs CPU (Python 2.6, desktop session).
from ctypes import *
import time
class Pt(Structure): _fields_=[('x',c_float),('y',c_float)]
class Rc(Structure): _fields_=[('x',c_float),('y',c_float),('w',c_float),('h',c_float)]
o=cdll.LoadLibrary('/usr/lib/libobjc.dylib'); fnd=cdll.LoadLibrary('/System/Library/Frameworks/Foundation.framework/Foundation'); qc=cdll.LoadLibrary('/System/Library/Frameworks/QuartzCore.framework/QuartzCore'); L=cdll.LoadLibrary('/System/Library/Frameworks/OpenGL.framework/OpenGL')
o.objc_getClass.restype=c_void_p; o.sel_registerName.restype=c_void_p; o.objc_msgSend.restype=c_void_p
C=lambda n:c_void_p(o.objc_getClass(n)); S=lambda n:c_void_p(o.sel_registerName(n))
m=o.objc_msgSend; pool=m(m(C('NSAutoreleasePool'),S('alloc')) and C('NSAutoreleasePool'),S('new'))
def s(x): return c_void_p(m(C('NSString'),S('stringWithUTF8String:'),x))
A=(c_int*5)(73,72,90,0,0); pf=c_void_p(); np=c_int(0); L.CGLChoosePixelFormat(A,byref(pf),byref(np))
ctx=c_void_p(); L.CGLCreateContext(pf,None,byref(ctx)); L.CGLSetCurrentContext(ctx); pb=c_void_p(); L.CGLCreatePBuffer(512,512,0x0DE1,0x1908,0,byref(pb)); sc=c_int(0); L.CGLGetVirtualScreen(ctx,byref(sc)); L.CGLSetPBuffer(ctx,pb,0,0,sc.value)
L.glGetString.restype=c_char_p; print 'renderer',L.glGetString(0x1F01)
L.glViewport(0,0,512,512); L.glMatrixMode(0x1701); L.glLoadIdentity(); L.glOrtho.argtypes=[c_double]*6; L.glOrtho(0,512,0,512,-1,1); L.glMatrixMode(0x1700); L.glLoadIdentity()
kSW=c_void_p.in_dll(qc,'kCIContextUseSoftwareRenderer')
def run(sw):
    d=c_void_p(m(C('NSDictionary'),S('dictionaryWithObject:forKey:'),c_void_p(m(C('NSNumber'),S('numberWithBool:'),1 if sw else 0)),kSW))
    ci=c_void_p(m(C('CIContext'),S('contextWithCGLContext:pixelFormat:options:'),ctx,pf,d)); print 'ci context',bool(ci.value),'software requested',sw
    g=c_void_p(m(C('CIFilter'),S('filterWithName:'),s('CICheckerboardGenerator'))); m(g,S('setDefaults'))
    b=c_void_p(m(C('CIFilter'),S('filterWithName:'),s('CIGaussianBlur'))); m(b,S('setDefaults')); m(b,S('setValue:forKey:'),c_void_p(m(g,S('valueForKey:'),s('outputImage'))),s('inputImage')); m(b,S('setValue:forKey:'),c_void_p(m(C('NSNumber'),S('numberWithFloat:'),c_float(6.0))),s('inputRadius'))
    img=c_void_p(m(b,S('valueForKey:'),s('outputImage'))); t=time.time(); n=0
    L.glClearColor.argtypes=[c_float]*4; L.glClearColor(0,0,0,1)
    while time.time()-t<6:
        L.glClear(0x4000); m(ci,S('drawImage:atPoint:fromRect:'),img,Pt(0,0),Rc(0,0,512,512)); L.glFinish(); n+=1
    f=n/(time.time()-t); p=(c_ubyte*4)(); L.glReadPixels(100,100,1,1,0x1908,0x1401,byref(p)); q=(c_ubyte*4)(); L.glReadPixels(300,300,1,1,0x1908,0x1401,byref(q))
    print '  fps %.2f, samples'%f,list(p),list(q),'glError',L.glGetError(); return f
h=run(False); c=run(True); print 'GPU %.2f fps, CPU %.2f fps'%(h,c); print 'DONE'
