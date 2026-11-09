# OpenGL coverage test (Python 2.6, run inside the desktop session). Compares GPU output to expected pixels.
from ctypes import *
import sys,struct
L=cdll.LoadLibrary('/System/Library/Frameworks/OpenGL.framework/OpenGL')
F=[c_float]
def g(n,*a):
    f=getattr(L,n); f.argtypes=list(a); f.restype=None; return f
Clear=g('glClear',c_uint); ClearC=g('glClearColor',c_float,c_float,c_float,c_float)
Begin=g('glBegin',c_uint); End=g('glEnd'); Color=g('glColor4f',c_float,c_float,c_float,c_float)
V=g('glVertex3f',c_float,c_float,c_float); T=g('glTexCoord2f',c_float,c_float); Finish=g('glFinish')
En=g('glEnable',c_uint); Dis=g('glDisable',c_uint); Blend=g('glBlendFunc',c_uint,c_uint)
Bind=g('glBindTexture',c_uint,c_uint); Param=g('glTexParameteri',c_uint,c_uint,c_int); Env=g('glTexEnvi',c_uint,c_uint,c_int)
Img=g('glTexImage2D',c_uint,c_int,c_int,c_int,c_int,c_int,c_uint,c_uint,c_char_p)
L.glGetString.restype=c_char_p; L.glGetError.restype=c_uint; ERR=L.glGetError
res=[]
def rd(x,y):
    p=(c_ubyte*4)(); L.glReadPixels(x,y,1,1,0x1908,0x1401,byref(p)); return list(p)
def check(n,got,want,tol=3):
    ok=all(abs(a-b)<=tol for a,b in zip(got,want)); res.append(ok); print ('PASS' if ok else 'FAIL'),n,'got',got,'want',want; sys.stdout.flush()
A=(c_int*10)(73,72,90,8,32,12,24,13,8,0)
pf=c_void_p(); np=c_int(0); L.CGLChoosePixelFormat(A,byref(pf),byref(np)); print 'pixel formats',np.value
ctx=c_void_p(); L.CGLCreateContext(pf,None,byref(ctx)); L.CGLSetCurrentContext(ctx)
pb=c_void_p(); L.CGLCreatePBuffer(256,256,0x0DE1,0x1908,0,byref(pb)); s=c_int(0); L.CGLGetVirtualScreen(ctx,byref(s)); L.CGLSetPBuffer(ctx,pb,0,0,s.value)
print 'renderer',L.glGetString(0x1F01); ext=L.glGetString(0x1F03)
L.glViewport(0,0,256,256); L.glMatrixMode(0x1701); L.glLoadIdentity(); L.glOrtho.argtypes=[c_double]*6; L.glOrtho(0,1,0,1,-1,1); L.glMatrixMode(0x1700); L.glLoadIdentity()
Env(0x2300,0x2200,0x1E01)
def bg(): Dis(0x0DE1); Dis(0x0BE2); Dis(0x0B71); Dis(0x0BC0); Dis(0x0C11); Dis(0x0B90); ClearC(0.1,0.2,0.3,1.0); Clear(0x4000|0x100|0x400)
def quad(x0=0.,y0=0.,x1=1.,y1=1.,z=0.,s1=1.,t1=1.):
    Begin(7); T(0,0); V(x0,y0,z); T(s1,0); V(x1,y0,z); T(s1,t1); V(x1,y1,z); T(0,t1); V(x0,y1,z); End()
def tex(ifmt,fmt,typ,w,h,data,target=0x0DE1,filt=0x2600):
    t=c_uint(0); L.glGenTextures(1,byref(t)); Bind(target,t.value); Param(target,0x2801,filt); Param(target,0x2800,filt); Param(target,0x2802,0x812F); Param(target,0x2803,0x812F)
    Img(target,0,ifmt,w,h,0,fmt,typ,data); return t.value
def two(px0,px1,w=8,h=8):
    return ''.join((px0 if x<w/2 else px1) for y in range(h) for x in range(w))
R,GG,B=(255,0,0,255),(0,255,0,255),(0,0,255,255)
def fmt_test(name,ifmt,fmt,typ,a,b,wa,wb,tol=3):
    bg(); En(0x0DE1); tex(ifmt,fmt,typ,8,8,two(a,b)); Color(1,1,1,1); quad(); Finish()
    check(name+' left',rd(64,128),wa,tol); check(name+' right',rd(192,128),wb,tol)
fmt_test('RGBA8',0x8058,0x1908,0x1401,struct.pack('4B',200,10,20,255),struct.pack('4B',10,200,20,255),[200,10,20,255],[10,200,20,255])
fmt_test('BGRA8888',0x8058,0x80E1,0x8367,struct.pack('<I',0xFFC80A14),struct.pack('<I',0xFF0AC814),[200,10,20,255],[10,200,20,255])
fmt_test('RGB565',0x8D62 if 0 else 0x1907,0x1907,0x8363,struct.pack('<H',(25<<11)|(1<<5)|2),struct.pack('<H',(1<<11)|(50<<5)|2),[206,4,16,255],[8,206,16,255],12)
fmt_test('RGBA4444',0x1908,0x1908,0x8033,struct.pack('<H',(12<<12)|(1<<8)|(2<<4)|15),struct.pack('<H',(1<<12)|(12<<8)|(2<<4)|15),[204,17,34,255],[17,204,34,255],20)
fmt_test('Luminance',0x1909,0x1909,0x1401,struct.pack('B',180),struct.pack('B',60),[180,180,180,255],[60,60,60,255])
fmt_test('Alpha8',0x1906,0x1906,0x1401,struct.pack('B',128),struct.pack('B',64),[0,0,0,128],[0,0,0,64],6)
# large and non-power-of-two surfaces, where tiling layout errors would appear
def grad(w,h):
    b=bytearray(w*h*4); i=0
    for y in range(h):
        for x in range(w): b[i]=x*255/(w-1); b[i+1]=y*255/(h-1); b[i+2]=(x^y)&255; b[i+3]=255; i+=4
    return str(b)
def tile(n,w,h,target=0x0DE1,norm=True):
    bg(); En(target); tex(0x8058,0x1908,0x1401,w,h,grad(w,h),target); Color(1,1,1,1)
    if norm: quad()
    else: quad(s1=float(w),t1=float(h))
    Finish(); Dis(target)
    for x,y in ((16,16),(128,128),(240,40),(40,240),(200,200)):
        sx,sy=(x+0.5)/256.0*w,(y+0.5)/256.0*h; tx,ty=int(sx),int(sy); check('%s @%d,%d'%(n,x,y),rd(x,y),[tx*255/(w-1),ty*255/(h-1),(tx^ty)&255,255],6)
tile('Tiled256',256,256); tile('Tiled512',512,512); tile('Tiled1024',1024,1024)
if 'GL_ARB_texture_rectangle' in ext or 'GL_EXT_texture_rectangle' in ext: tile('Rect300x200',300,200,0x84F5,False)
# mipmaps, each level a different solid colour
bg(); En(0x0DE1); t=c_uint(0); L.glGenTextures(1,byref(t)); Bind(0x0DE1,t.value); Param(0x0DE1,0x2801,0x2700); Param(0x0DE1,0x2800,0x2600); Param(0x0DE1,0x2802,0x812F); Param(0x0DE1,0x2803,0x812F)
cols=[(255,0,0,255),(0,255,0,255),(0,0,255,255),(255,255,0,255),(255,0,255,255),(0,255,255,255),(255,255,255,255)]
for lv in range(7):
    w=64>>lv; Img(0x0DE1,lv,0x8058,w,w,0,0x1908,0x1401,struct.pack('4B',*cols[lv])*(w*w))
Color(1,1,1,1); quad(0,0,1,1); quad(0,0,0.5,0.5) ; Finish()
check('Mip level 0-ish',rd(200,200),[255,0,0,255],4)
bg(); En(0x0DE1); Bind(0x0DE1,t.value); Color(1,1,1,1); quad(0,0,0.0625,0.0625); Finish(); check('Mip level 2',rd(8,8),[0,0,255,255],4); Dis(0x0DE1)
# blending, depth, alpha test, scissor, stencil
bg(); En(0x0BE2); Blend(0x0302,0x0303); Color(1,0,0,0.5); quad(); Finish(); check('Blend 50% red',rd(100,100),[140,25,38,255],8)
bg(); En(0x0B71); L.glDepthFunc(0x0201); Color(1,0,0,1); quad(z=0.5); Color(0,1,0,1); quad(z=-0.5); Finish(); check('Depth keeps nearer quad',rd(100,100),[255,0,0,255],4)
bg(); En(0x0C11); L.glScissor(0,0,128,256); Color(0,0,1,1); quad(); Finish(); Dis(0x0C11); check('Scissor inside',rd(64,128),[0,0,255,255],3); check('Scissor outside',rd(192,128),[26,51,77,255],3)
bg(); L.glStencilFunc(0x0207,1,0xff); L.glStencilOp(0x1E00,0x1E00,0x1E01); En(0x0B90); Color(1,0,0,1); quad(0,0,0.5,1); L.glStencilFunc(0x0202,1,0xff); L.glStencilOp(0x1E00,0x1E00,0x1E00); Color(0,1,0,1); quad(); Finish(); Dis(0x0B90); check('Stencil pass',rd(64,128),[0,255,0,255],4); check('Stencil reject',rd(192,128),[26,51,77,255],3)
# multitexture modulate
bg(); L.glActiveTexture(0x84C0); En(0x0DE1); tex(0x8058,0x1908,0x1401,1,1,struct.pack('4B',255,128,0,255)); Env(0x2300,0x2200,0x2100)
L.glActiveTexture(0x84C1); En(0x0DE1); tex(0x8058,0x1908,0x1401,1,1,struct.pack('4B',128,255,255,255)); Env(0x2300,0x2200,0x2100); L.glActiveTexture(0x84C0)
Color(1,1,1,1); quad(); Finish(); check('Multitexture modulate',rd(128,128),[128,128,0,255],6)
L.glActiveTexture(0x84C1); Dis(0x0DE1); L.glActiveTexture(0x84C0); Dis(0x0DE1); Env(0x2300,0x2200,0x1E01)
# render to texture by copy, then draw it
bg(); Color(1,0,0,1); quad(0,0,0.5,1); Color(0,0,1,1); quad(0.5,0,1,1); Finish(); c=c_uint(0); L.glGenTextures(1,byref(c)); Bind(0x0DE1,c.value); Param(0x0DE1,0x2801,0x2600); Param(0x0DE1,0x2800,0x2600); Img(0x0DE1,0,0x8058,256,256,0,0x1908,0x1401,None); L.glCopyTexSubImage2D(0x0DE1,0,0,0,0,0,256,256)
bg(); En(0x0DE1); Bind(0x0DE1,c.value); Color(1,1,1,1); quad(); Finish(); Dis(0x0DE1); check('CopyTex left',rd(64,128),[255,0,0,255],4); check('CopyTex right',rd(192,128),[0,0,255,255],4)
# framebuffer objects
if 'GL_EXT_framebuffer_object' in ext:
    fb=c_uint(0); tt=c_uint(0); L.glGenFramebuffersEXT(1,byref(fb)); L.glGenTextures(1,byref(tt)); Bind(0x0DE1,tt.value); Param(0x0DE1,0x2801,0x2600); Param(0x0DE1,0x2800,0x2600); Img(0x0DE1,0,0x8058,128,128,0,0x1908,0x1401,None)
    L.glBindFramebufferEXT(0x8D40,fb.value); L.glFramebufferTexture2DEXT(0x8D40,0x8CE0,0x0DE1,tt.value,0); st=L.glCheckFramebufferStatusEXT(0x8D40); check('FBO complete',[st],[0x8CD5],0)
    L.glViewport(0,0,128,128); ClearC(0,1,0,1); Clear(0x4000); Finish(); L.glBindFramebufferEXT(0x8D40,0); L.glViewport(0,0,256,256)
    bg(); En(0x0DE1); Bind(0x0DE1,tt.value); Color(1,1,1,1); quad(); Finish(); Dis(0x0DE1); check('FBO colour',rd(128,128),[0,255,0,255],4)
else: print 'SKIP FBO not exposed'
# ARB programs
def prog(target,src):
    p=c_uint(0); L.glGenProgramsARB(1,byref(p)); L.glBindProgramARB(target,p.value); L.glProgramStringARB(target,0x8875,len(src),src); e=ERR()
    if e: 
        L.glGetString.restype=c_char_p; print 'program error',hex(e),L.glGetString(0x8874)
    return p.value,e
if 'GL_ARB_fragment_program' in ext:
    p,e=prog(0x8804,"!!ARBfp1.0\nPARAM c={0.25,0.5,0.75,1.0};\nMOV result.color,c;\nEND\n"); check('FP compile',[e],[0],0); bg(); En(0x8804); quad(); Finish(); Dis(0x8804); check('FP constant',rd(128,128),[64,128,191,255],4)
    bg(); t2=tex(0x8058,0x1908,0x1401,1,1,struct.pack('4B',40,200,120,255)); p,e=prog(0x8804,"!!ARBfp1.0\nTEMP t;\nTEX t,fragment.texcoord[0],texture[0],2D;\nMUL result.color,t,{1.0,0.5,1.0,1.0};\nEND\n"); check('FP tex compile',[e],[0],0); En(0x8804); En(0x0DE1); Bind(0x0DE1,t2); quad(); Finish(); Dis(0x8804); Dis(0x0DE1); check('FP texture',rd(128,128),[40,100,120,255],5)
if 'GL_ARB_vertex_program' in ext:
    p,e=prog(0x8620,"!!ARBvp1.0\nPARAM m[4]={state.matrix.mvp};\nDP4 result.position.x,m[0],vertex.position;\nDP4 result.position.y,m[1],vertex.position;\nDP4 result.position.z,m[2],vertex.position;\nDP4 result.position.w,m[3],vertex.position;\nMOV result.color,{1,1,0,1};\nEND\n"); check('VP compile',[e],[0],0); bg(); En(0x8620); quad(); Finish(); Dis(0x8620); check('VP colour',rd(128,128),[255,255,0,255],4)
print 'glError',ERR(); print 'RESULT %d passed, %d failed of %d'%(sum(res),len(res)-sum(res),len(res)); print 'DONE'
