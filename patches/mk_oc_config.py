#!/usr/bin/env python3
"""Add the patched framebuffer and panel properties. usage: mk_oc_config.py GOOD OUT"""
import plistlib,sys
c=plistlib.load(open(sys.argv[1],'rb'))
c['DeviceProperties']['Add']['PciRoot(0x0)/Pci(0x2,0x0)']={
 'AAPL,HasPanel':bytes.fromhex('01000000'),'AAPL01,BacklightIntensity':bytes.fromhex('3F000008'),
 'AAPL01,BootDisplay':bytes.fromhex('01000000'),'AAPL01,DataJustify':bytes.fromhex('01000000'),
 'AAPL01,DualLink':bytes.fromhex('00'),'model':b'Intel GMA 3150\0'}
c['Kernel']['Add']=[k for k in c['Kernel']['Add'] if k['BundlePath']!='AppleIntelIntegratedFramebuffer.kext']
c['Kernel']['Add'].append({'Arch':'i386','BundlePath':'AppleIntelIntegratedFramebuffer.kext','Comment':'patched GMA3150 framebuffer','Enabled':True,'ExecutablePath':'AppleIntelIntegratedFramebuffer','MaxKernel':'','MinKernel':'','PlistPath':'Info.plist'})
c['Kernel']['Add']=[k for k in c['Kernel']['Add'] if k['BundlePath']!='AppleIntelGMA950.kext']
c['Kernel']['Add'].append({'Arch':'i386','BundlePath':'AppleIntelGMA950.kext','Comment':'patched GMA3150 accelerator','Enabled':True,'ExecutablePath':'Contents/MacOS/AppleIntelGMA950','MaxKernel':'','MinKernel':'','PlistPath':'Contents/Info.plist'})
plistlib.dump(c,open(sys.argv[2],'wb'))
print([k['BundlePath'] for k in c['Kernel']['Add']],c['NVRAM']['Add']['7C436110-AB2A-4BBB-A880-FE41995C9F82']['boot-args'])
