#!/usr/bin/env python3
"""Turn the diagnostic S3 config into the minimal working one.
Usage: mk_clean_s3config.py mach_kernel.i386 IN.plist OUT.plist [nc10-oc-copy value]
Keeps the _WAK rename and USB _PRW renames, drops the probe SSDT, XOSI and every marker patch, and replaces the
kernel marker patches with one change: the panic check after pmCPUExitHaltToOff in acpi_sleep_kernel becomes a jump
(10.6.0 10A432 only; AICPM never starts on this Atom, so that call returns 4)."""
import plistlib, struct, sys


def main():
    b = open(sys.argv[1], "rb").read()
    assert struct.unpack_from("<I", b, 0)[0] == 0xFEEDFACE
    nc = struct.unpack_from("<I", b, 16)[0]
    o, off = 28, None
    site = 0x2AEB5F
    for _ in range(nc):
        c, s = struct.unpack_from("<2I", b, o)
        if c == 1:
            v, _, fo, fs = struct.unpack_from("<4I", b, o + 24)
            if v <= site < v + fs:
                off = fo + site - v
        o += s
    assert b[off - 2:off + 2] == bytes.fromhex("85c07414")
    find = b[off - 10:off + 10]
    assert b.count(find) == 1
    rep = bytearray(len(find))
    rm = bytearray(len(find))
    rep[10] = 0xEB
    rm[10] = 0xFF
    c = plistlib.load(open(sys.argv[2], "rb"))
    k = [p for p in c["Kernel"]["Patch"] if not p["Comment"].startswith(("S3 marks", "S3 kernel"))]
    k.append({"Arch": "i386", "Base": "", "Comment": "S3: skip pmCPUExitHaltToOff panic in acpi_sleep_kernel (10A432)",
              "Count": 1, "Enabled": True, "Find": find, "Identifier": "kernel", "Limit": 0, "Mask": b"", "MaxKernel": "",
              "MinKernel": "", "Replace": bytes(rep), "ReplaceMask": bytes(rm), "Skip": 0})
    c["Kernel"]["Patch"] = k
    c["ACPI"]["Patch"] = [p for p in c["ACPI"]["Patch"] if "_PTS" not in p["Comment"]]
    for p in c["ACPI"]["Patch"]:
        p["Comment"] = p["Comment"].replace("S3 probe: ", "S3: ")
    c["ACPI"]["Add"] = [a for a in c["ACPI"]["Add"] if "S3PROBE" not in a["Path"] and "XOSI" not in a["Path"]]
    c["ACPI"]["Add"].append({"Comment": "_WAK returns the package the spec requires", "Enabled": True, "Path": "SSDT-WAK.aml"})
    if len(sys.argv) > 4:
        c["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["nc10-oc-copy"] = sys.argv[4].encode()
    plistlib.dump(c, open(sys.argv[3], "wb"), sort_keys=False)


if __name__ == "__main__":
    main()
