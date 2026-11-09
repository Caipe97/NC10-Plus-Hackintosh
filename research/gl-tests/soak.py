# One-hour mixed GPU soak with pixel verification (Python 2.6, desktop session). Logs once a minute.
from ctypes import *
import os,time,sys
class Pt(Structure): _fields_=[('x',c_float),('y',c_float)]
class Rc(Structure): _fields_=[('x',c_float),('y',c_float),('w',c_float),('h',c_float)]
DUR=int(sys.argv[1]) if len(sys.argv)>1 else 3600
o=cdll.LoadLibrary('/usr/lib/libobjc.dylib'); cdll.LoadLibrary('/System/Library/Frameworks/Foundation.framework/Foundation'); cdll.LoadLibrary('/System/Library/Frameworks/QuartzCore.framework/QuartzCore'); L=cdll.LoadLibrary('/System/Library/Frameworks/OpenGL.framework/OpenGL')
o.objc_getClass.restype=c_void_p; o.sel_registerName.restype=c_void_p; o.objc_msgSend.restype=c_void_p; m=o.objc_msgSend
C=lambda n:c_void_p(o.objc_getClass(n)); S=lambda n:c_void_p(o.sel_registerName(n)); s=lambda x:c_void_p(m(C('NSString'),S('stringWithUTF8String:'),x))
m(C('NSAutoreleasePool'),S('new'))
A=(c_int*5)(73,72,90,0,0); pf=c_void_p(); np=c_int(0); L.CGLChoosePixelFormat(A,byref(pf),byref(np)); ctx=c_void_p(); L.CGLCreateContext(pf,None,byref(ctx)); L.CGLSetCurrentContext(ctx)
pb=c_void_p(); L.CGLCreatePBuffer(256,256,0x0DE1,0x1908,0,byref(pb)); sc=c_int(0); L.CGLGetVirtualScreen(ctx,byref(sc)); L.CGLSetPBuffer(ctx,pb,0,0,sc.value)
L.glGetString.restype=c_char_p; print 'renderer',L.glGetString(0x1F01); sys.stdout.flush()
for n,a in (('glClearColor',[c_float]*4),('glTexCoord2f',[c_float]*2),('glVertex2f',[c_float]*2)): getattr(L,n).argtypes=a
L.glOrtho.argtypes=[c_double]*6; L.glViewport(0,0,256,256); L.glMatrixMode(0x1701); L.glLoadIdentity(); L.glOrtho(0,1,0,1,-1,1); L.glMatrixMode(0x1700); L.glLoadIdentity()
tx=c_uint(0); L.glGenTextures(1,byref(tx)); L.glBindTexture(0x0DE1,tx.value)
for p,v in ((0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812F),(0x2803,0x812F)): L.glTexParameteri(0x0DE1,p,v)
L.glTexEnvi(0x2300,0x2200,0x1E01)
ci=c_void_p(m(C('CIContext'),S('contextWithCGLContext:pixelFormat:options:'),ctx,pf,None)); g=c_void_p(m(C('CIFilter'),S('filterWithName:'),s('CICheckerboardGenerator'))); m(g,S('setDefaults')); b=c_void_p(m(C('CIFilter'),S('filterWithName:'),s('CIGaussianBlur'))); m(b,S('setDefaults')); m(b,S('setValue:forKey:'),c_void_p(m(g,S('valueForKey:'),s('outputImage'))),s('inputImage')); img=c_void_p(m(b,S('valueForKey:'),s('outputImage')))
t0=time.time(); last=t0; lastw=t0; it=bad=err=0; p=(c_ubyte*4)()
while time.time()-t0<DUR:
    d=os.urandom(256*256*4); L.glEnable(0x0DE1); L.glBindTexture(0x0DE1,tx.value); L.glTexImage2D(0x0DE1,0,0x8058,256,256,0,0x1908,0x1401,d)
    L.glBegin(7); L.glTexCoord2f(0,0); L.glVertex2f(0,0); L.glTexCoord2f(1,0); L.glVertex2f(1,0); L.glTexCoord2f(1,1); L.glVertex2f(1,1); L.glTexCoord2f(0,1); L.glVertex2f(0,1); L.glEnd(); L.glFinish()
    for x,y in ((3,7),(100,50),(200,131),(250,250)):
        L.glReadPixels(x,y,1,1,0x1908,0x1401,byref(p)); w=[ord(c) for c in d[(y*256+x)*4:(y*256+x)*4+3]]
        if [p[0],p[1],p[2]]!=w: bad+=1
    L.glDisable(0x0DE1); m(ci,S('drawImage:atPoint:fromRect:'),img,Pt(0,0),Rc(0,0,256,256)); L.glFinish(); e=L.glGetError(); err+=1 if e else 0; it+=1
    now=time.time()
    if now-lastw>30:
        lastw=now; os.system("osascript -e 'tell application \"Finder\" to make new Finder window' -e 'delay 2' -e 'tell application \"Finder\" to close front window' >/dev/null 2>&1 &")
    if now-last>60:
        last=now; print time.strftime('%H:%M:%S'),'t=%d iter=%d mismatches=%d glErrors=%d'%(now-t0,it,bad,err); sys.stdout.flush()
print 'FINAL iter=%d mismatches=%d glErrors=%d seconds=%d'%(it,bad,err,time.time()-t0); print 'DONE'; sys.stdout.flush()
