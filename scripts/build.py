#!/usr/bin/env python3
"""Assemble the bootable NC10 Plus EFI from this repository plus files you supply.

No Apple binaries live in this repository. This script takes your own stock 10.6.0 (10A432) kexts,
applies the patches, checks every input and output by SHA-256, and writes:

    out/EFI                         copy to the EFI partition
    out/boot                        BIOS boot file, copy to the root of the EFI partition
    out/system/AppleHDA.kext        patched audio driver for /System/Library/Extensions

usage:
    scripts/build.py --extensions DIR --hfsplus HfsPlus32.efi --macserial PATH
                     [--config FILE] [--out DIR]

DIR must hold stock AppleIntelGMA950.kext, AppleIntelIntegratedFramebuffer.kext and AppleHDA.kext.
"""
import argparse
import hashlib
import json
import pathlib
import plistlib
import secrets
import shutil
import subprocess
import sys
import uuid

REPO = pathlib.Path(__file__).resolve().parent.parent
PATCHES = REPO / "patches"

GMA_BIN = "Contents/MacOS/AppleIntelGMA950"
FB_BIN = "AppleIntelIntegratedFramebuffer"
HDA_BIN = "Contents/MacOS/AppleHDA"
TP_BIN = "Contents/MacOS/VoodooPS2Trackpad"
TP_KEXT = "VoodooPS2Controller.kext/Contents/PlugIns/VoodooPS2Trackpad.kext"

_SUMS = json.loads((PATCHES / "checksums.json").read_text())
STOCK, PATCHED = _SUMS["stock"], _SUMS["patched"]


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def check(name, path, table):
    got = sha256(path)
    if got != table[name]:
        sys.exit(f"{name}: unexpected SHA-256 {got}\n  file: {path}\n  expected: {table[name]}")
    print(f"ok  {name}")


def run(script, *args):
    subprocess.run([sys.executable, "-I", str(PATCHES / script), *map(str, args)],
                   check=True, stdout=subprocess.DEVNULL)


def edit_plist(path, change):
    data = plistlib.loads(path.read_bytes())
    change(data)
    path.write_bytes(plistlib.dumps(data))


def bump(version, boot_required=False):
    def change(data):
        data["CFBundleVersion"] = version
        if boot_required:
            data["OSBundleRequired"] = "Root"
    return change


def smbios(config, macserial):
    text = subprocess.run([macserial, "-m", "MacBook1,1", "-g", "-n", "1"], check=True,
                          capture_output=True, text=True).stdout
    serial, mlb = [x.strip() for x in text.strip().splitlines()[-1].split("|")]
    data = plistlib.loads(config.read_bytes())
    data["PlatformInfo"]["Generic"].update(
        SystemSerialNumber=serial, MLB=mlb, SystemUUID=str(uuid.uuid4()).upper(), ROM=secrets.token_bytes(6))
    config.write_bytes(plistlib.dumps(data, sort_keys=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extensions", required=True, type=pathlib.Path, help="folder with the stock 10A432 kexts")
    ap.add_argument("--hfsplus", required=True, type=pathlib.Path, help="HfsPlus32.efi from OcBinaryData")
    ap.add_argument("--macserial", required=True, type=pathlib.Path, help="macserial binary from the OpenCore release")
    ap.add_argument("--config", type=pathlib.Path, default=REPO / "EFI/OC/config.full.plist", help="config template to use")
    ap.add_argument("--out", type=pathlib.Path, default=REPO / "out")
    a = ap.parse_args()

    gma, fb, hda = (a.extensions / f"{n}.kext" for n in
                    ("AppleIntelGMA950", "AppleIntelIntegratedFramebuffer", "AppleHDA"))
    check("AppleIntelGMA950", gma / GMA_BIN, STOCK)
    check("AppleIntelIntegratedFramebuffer", fb / FB_BIN, STOCK)
    check("AppleHDA", hda / HDA_BIN, STOCK)
    check("HfsPlus32.efi", a.hfsplus, STOCK)

    shutil.rmtree(a.out, ignore_errors=True)
    efi, kexts = a.out / "EFI", a.out / "EFI/OC/Kexts"
    shutil.copytree(REPO / "EFI", efi)
    shutil.copy(REPO / "legacy-boot/boot", a.out / "boot")
    shutil.copy(a.config, efi / "OC/config.plist")
    shutil.copy(a.hfsplus, efi / "OC/Drivers/HfsPlus32.efi")
    for sub in ("Audio", "Font", "Image", "Label"):
        (efi / "OC/Resources" / sub).mkdir(parents=True, exist_ok=True)

    # Graphics pair: PCI match, patched binary, and the version bump used on the tested EFI.
    run("mk_test_kext.py", gma, kexts, "0xA0118086")
    run("patch_gma.py", gma / GMA_BIN, kexts / gma.name / GMA_BIN)
    edit_plist(kexts / gma.name / "Contents/Info.plist", bump("6.0.1", boot_required=True))
    run("mk_test_kext.py", fb, kexts, "0xA0118086")
    run("patch_fb.py", fb / FB_BIN, kexts / fb.name / FB_BIN)
    edit_plist(kexts / fb.name / "Info.plist", bump("6.0.1"))

    # PS/2 pair: touchpad jump filter and the multi-finger width limit.
    trackpad = kexts / TP_KEXT
    check("VoodooPS2Trackpad", trackpad / TP_BIN, STOCK)
    run("patch_trackpad.py", trackpad / TP_BIN, trackpad / (TP_BIN + ".new"))
    (trackpad / (TP_BIN + ".new")).replace(trackpad / TP_BIN)

    def limit(data):
        cfg = data["IOKitPersonalities"]["Synaptics TouchPad"]["Configuration"]
        assert cfg["MultiFingerWLimit"] == 9
        cfg["MultiFingerWLimit"] = 6
    edit_plist(trackpad / "Contents/Info.plist", limit)

    # AppleHDA goes on the system disk, not in the EFI.
    target = a.out / "system" / hda.name
    shutil.copytree(hda, target)
    run("patch_hda.py", hda / HDA_BIN, target / HDA_BIN)

    smbios(efi / "OC/config.plist", a.macserial)

    check("AppleIntelGMA950", kexts / gma.name / GMA_BIN, PATCHED)
    check("AppleIntelIntegratedFramebuffer", kexts / fb.name / FB_BIN, PATCHED)
    check("VoodooPS2Trackpad", trackpad / TP_BIN, PATCHED)
    check("AppleHDA", target / HDA_BIN, PATCHED)
    print(f"\nBuilt {a.out}. Next steps are in docs/INSTALL.md.")


if __name__ == "__main__":
    main()
