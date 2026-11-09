#!/usr/bin/env python3
"""Add OpenCore kernel patches to a config: AppleACPIPlatform writes a stage marker to CMOS 0xDE during S3 entry.
Usage: mk_acpi_marks.py KEXT.i386 IN.plist OUT.plist

Markers: B1 sleepPlatform started   B2 AcpiEnterSleepStatePrep (_PTS/_GTS) returned   B3 before picSleepWake
         B4 before setPCIBridgePowerState   B5 before systemWillSleep
         B6 inside the sleep callback, before the AppleRTC message (after acpi_sleep_kernel saved state)
         B7 AppleRTC done, about to run AcpiEnterSleepState (the real SLP_EN write)
         B8 systemWillSleep returned, about to call acpi_sleep_kernel (written between B5 and B6)
Code goes in AcpiEnterSleepStateS4bios, unused here. Bytes the linker relocates are masked out of the search."""
import plistlib, struct, sys

IDENT = "com.apple.driver.AppleACPIPlatform"
CAVE = 0x1A4A1
CAVE_MAX = 147
SITES = [("B1", 0x960C, 0x94A0), ("B2", 0x9649, 0x028C), ("B3", 0x966C, 0x821C),
         ("B4", 0x9681, 0x8274), ("B5", 0x96A1, 0xE29E)]


def load(path):
    b = open(path, "rb").read()
    magic, _, _, _, nc, _, _ = struct.unpack_from("<7I", b, 0)
    assert magic == 0xFEEDFACE
    o, secs = 28, []
    for _ in range(nc):
        c, s = struct.unpack_from("<2I", b, o)
        if c == 1:
            ns = struct.unpack_from("<I", b, o + 48)[0]
            p = o + 56
            for _ in range(ns):
                n = b[p:p + 16].split(b"\0")[0]
                a, z, of, _, ro, nr = struct.unpack_from("<6I", b, p + 32)
                secs.append((n, a, z, of, ro, nr))
                p += 68
        o += s
    t = next(x for x in secs if x[0] == b"__text")
    rel = set()
    for _, a, _, _, ro, nr in secs:
        for k in range(nr):
            x = struct.unpack_from("<I", b, ro + 8 * k)[0]
            rel.add(a + (x & 0xFFFFFF if x & 0x80000000 else x))
    return bytes(b[t[3]:t[3] + t[2]]), rel


def masked(text, rel, a, n):
    f = bytearray(text[a:a + n])
    m = bytearray(b"\xff" * n)
    for r in rel:
        for j in range(4):
            if a <= r + j < a + n:
                f[r + j - a] = 0
                m[r + j - a] = 0
    return f, m


def count(text, f, m):
    c = 0
    for i in range(len(text) - len(f) + 1):
        if all((text[i + j] & m[j]) == f[j] for j in range(len(f))):
            c += 1
    return c


def patch(comment, find, mask, rep, rmask):
    return {"Arch": "i386", "Base": "", "Comment": comment, "Count": 1, "Enabled": True, "Find": bytes(find),
            "Identifier": IDENT, "Limit": 0, "Mask": bytes(mask), "MaxKernel": "", "MinKernel": "",
            "Replace": bytes(rep), "ReplaceMask": bytes(rmask), "Skip": 0}


def site_patch(text, rel, name, site, new):
    a, n = site - 8, 8 + len(new) + 8
    f, m = masked(text, rel, a, n)
    assert count(text, f, m) == 1, name
    rep = bytearray(n)
    rm = bytearray(n)
    for j, v in enumerate(new):
        rep[8 + j] = v
        rm[8 + j] = 0xFF
    return patch("S3 marks: " + name, f, m, rep, rm)


def main():
    text, rel = load(sys.argv[1])
    mark = lambda v: bytes([0x50, 0xB0, 0xDE, 0xE6, 0x72, 0xB0, v, 0xE6, 0x73, 0x58])
    cave, out = bytearray(), []
    here = lambda: CAVE + len(cave)
    for name, site, target in SITES:
        c = here()
        cave += mark(int(name, 16)) + b"\xe9" + struct.pack("<i", target - (c + 15))
        out.append(site_patch(text, rel, name, site, b"\xe8" + struct.pack("<i", c - (site + 5))))
    c = here()
    cave += mark(0xB6) + bytes.fromhex("ffa0b0040000")
    out.append(site_patch(text, rel, "B6", 0x9216, b"\xe8" + struct.pack("<i", c - (0x9216 + 5)) + b"\x90"))
    c = here()
    cave += mark(0xB7) + b"\xe9" + struct.pack("<i", 0x1A534 - (c + 15))
    out.append(site_patch(text, rel, "B7", 0x9240, b"\xe9" + struct.pack("<i", c - (0x9240 + 5))))
    # B8: replaces the movb just after systemWillSleep returns; the cave does the movb and returns.
    c = here()
    cave += mark(0xB8) + bytes.fromhex("c6838f00000001") + b"\xc3"
    out.append(site_patch(text, rel, "B8", 0x96A6, b"\xe8" + struct.pack("<i", c - (0x96A6 + 5)) + b"\x90\x90"))
    assert len(cave) <= CAVE_MAX
    f, m = masked(text, rel, CAVE, len(cave))
    assert count(text, f, m) == 1, "cave"
    out.insert(0, patch("S3 marks: code in unused AcpiEnterSleepStateS4bios", f, m, cave, b"\xff" * len(cave)))
    c = plistlib.load(open(sys.argv[2], "rb"))
    c["Kernel"]["Patch"] = list(c["Kernel"].get("Patch", [])) + out
    plistlib.dump(c, open(sys.argv[3], "wb"), sort_keys=False)
    print(f"{len(out)} patches, cave {len(cave)} bytes")


if __name__ == "__main__":
    main()
