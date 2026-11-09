#!/usr/bin/env python3
"""Add OpenCore kernel patches to acpi_sleep_kernel in the 10.6.0 (10A432) i386 kernel.
Usage: mk_kernel_s3patch.py mach_kernel.i386 IN.plist OUT.plist [patched-copy]

- At 0x2aeb5d, replaces the panic on a nonzero pmCPUExitHaltToOff return: stores the low byte of the return code
  in CMOS 0xDF and continues the loop.
- Writes markers to CMOS 0xDE before each later call: C1 lapic_shutdown, C2 pmTimerSave, C3 vmx_suspend,
  C4 cpu_IA32e_disable, C5 acpi_sleep_cpu. Marker code sits in the nop padding after the function (0x2aeda1)."""
import plistlib, struct, sys

CAVE = 0x2AEDA1
SITES = [("C1", 0x2AEB7E, 0x2AD08C), ("C2", 0x2AEB8F, 0x2A74D7), ("C3", 0x2AEB94, 0x2B7ECD),
         ("C4", 0x2AEBA2, 0x2B84F5), ("C5", 0x2AEBC5, 0x2AF020)]
PANIC_AT, PANIC_END = 0x2AEB5D, 0x2AEB75


def load(path):
    b = open(path, "rb").read()
    assert struct.unpack_from("<I", b, 0)[0] == 0xFEEDFACE
    nc = struct.unpack_from("<I", b, 16)[0]
    o, segs = 28, []
    for _ in range(nc):
        c, s = struct.unpack_from("<2I", b, o)
        if c == 1:
            v, vs, fo, fs = struct.unpack_from("<4I", b, o + 24)
            segs.append((v, fs, fo))
        o += s
    return bytearray(b), segs


def main():
    b, segs = load(sys.argv[1])

    def off(v):
        for s, fs, fo in segs:
            if s <= v < s + fs:
                return fo + v - s
        raise ValueError(hex(v))

    def patch(name, vm, new, before=8, after=8):
        o = off(vm)
        ctx = bytes(b[o - before:o + len(new) + after])
        assert bytes(b).count(ctx) == 1, name
        rep, rm = bytearray(len(ctx)), bytearray(len(ctx))
        for j, v in enumerate(new):
            rep[before + j] = v
            rm[before + j] = 0xFF
        return {"Arch": "i386", "Base": "", "Comment": "S3 kernel: " + name, "Count": 1, "Enabled": True, "Find": ctx,
                "Identifier": "kernel", "Limit": 0, "Mask": b"", "MaxKernel": "", "MinKernel": "", "Replace": bytes(rep),
                "ReplaceMask": bytes(rm), "Skip": 0}

    mark = lambda v: bytes([0x50, 0xB0, 0xDE, 0xE6, 0x72, 0xB0, v, 0xE6, 0x73, 0x58])
    out, cave = [], bytearray()
    for name, site, target in SITES:
        o = off(site)
        assert b[o] == 0xE8 and o + 5 + struct.unpack_from("<i", b, o + 1)[0] == off(target), name
        c = CAVE + len(cave)
        cave += mark(int(name, 16)) + b"\xe9" + struct.pack("<i", target - (c + 15))
        # C3 sits right after C2, whose patch would change the bytes before it.
        out.append(patch(name, site, b"\xe8" + struct.pack("<i", c - (site + 5)), before=0 if name == "C3" else 8))
    # Sanity: padding really is nops and the panic block is what we expect.
    o = off(CAVE)
    assert bytes(b[o:o + len(cave)]) == b"\x90" * len(cave)
    o = off(PANIC_AT)
    assert bytes(b[o:o + 4]) == bytes.fromhex("85c07414")
    # mov %eax,%edx; mov $0xdf,%al; out %al,$0x72; mov %dl,%al; out %al,$0x73; then nops into the inc at 0x2aeb75.
    code = bytes.fromhex("89c2b0dfe67288d0e673")
    new = code + b"\x90" * (PANIC_END - PANIC_AT - len(code))
    out.insert(0, patch("record pmCPUExitHaltToOff result, skip panic", PANIC_AT, new))
    out.insert(0, patch("marker code", CAVE, bytes(cave), before=8, after=0))
    c = plistlib.load(open(sys.argv[2], "rb"))
    c["Kernel"]["Patch"] = list(c["Kernel"].get("Patch", [])) + out
    plistlib.dump(c, open(sys.argv[3], "wb"), sort_keys=False)
    if len(sys.argv) > 4:
        for p in out:
            i = bytes(b).find(p["Find"])
            assert bytes(b).count(p["Find"]) == 1, p["Comment"]
            for j, m in enumerate(p["ReplaceMask"]):
                if m:
                    b[i + j] = p["Replace"][j]
        open(sys.argv[4], "wb").write(b)
    print(len(out), "patches, cave", len(cave), "bytes")


if __name__ == "__main__":
    main()
