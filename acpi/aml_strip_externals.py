#!/usr/bin/env python3
"""Remove the leading If (Zero) { External ... } block that modern iasl emits into an SSDT.
Mac OS X 10.6's ACPI interpreter predates opcode 0x15 and abandons the whole table when it meets it.
Usage: aml_strip_externals.py in.aml out.aml"""
import struct, sys

b = bytearray(open(sys.argv[1], "rb").read())
i = 36
if b[i] != 0xA0 or b[i + 2] != 0x00 or b[i + 3] != 0x15:
    sys.exit("no leading If (Zero) { External } block found")
pkg = b[i + 1]
if pkg & 0xC0:
    sys.exit("multi-byte package length not handled")
j = i + 3
end = i + 1 + pkg
while j < end:
    if b[j] != 0x15 or b[j + 1] != 0x5C:
        sys.exit(f"unexpected opcode {b[j]:#x} in External block")
    j += 8                      # 0x15, '\\', 4-char name, type, arg count
if j != end:
    sys.exit("External block length mismatch")
del b[i:end]
struct.pack_into("<I", b, 4, len(b))
b[9] = 0
b[9] = (-sum(b)) & 0xFF
if b.count(0x15) and any(b[k] == 0x15 and b[k + 1] == 0x5C for k in range(36, len(b) - 1)):
    sys.exit("External opcode still present")
open(sys.argv[2], "wb").write(b)
print(f"stripped {end - i} bytes, new length {len(b)}")
