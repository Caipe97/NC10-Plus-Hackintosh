#!/usr/bin/env python3
"""Generate the S3 probe SSDT source.

  mk_s3probe.py dump OUT.dsl            read-only: publish the upper CMOS bank through _UID values
  mk_s3probe.py probe OUT.dsl 0xNN [nosmi,gpuoff,slpen]   also wrap _PTS/_WAK and add _GTS/_BFS, writing stage markers to CMOS 0xNN

The dump devices are \\_SB.NCxx, with _UID holding 2 CMOS bytes (little-endian, as decimal) starting at
0x80 + 2*xx (10.6 truncates _UID strings to 9 characters, so 4 bytes do not fit). \\_SB.NCRC holds the chipset RTC configuration register (RCBA+0x3400).
With a probe, \\_SB.NCMK has _UID = marker left by the previous boot's sleep attempt, or
0x100 + value if the marker byte held no probe marker. The marker is cleared at each boot.

_GTS(3) also stores, read back from the dump: 0xD3 firmware OS type (TPOS), 0xD4 SMI_EN[7:0] (bit 0 GBL_SMI_EN,
bit 4 SLP_SMI_EN), 0xD5 SMI_EN[23:16], 0xD6/0xD7 PM1_CNT.

Marker values (high nibble 0xA, low nibble the last stage reached):
  1 _PTS(3) entered   2 _PTS(3) returned   3 _GTS(3)   4 _BFS(3)   5 _WAK(3) entered   6 _WAK(3) returned   7 about to write SLP_EN from AML   8 that write returned
"""
import sys


def dump_devices():
    out = []
    for i in range(64):
        out.append(f"""
        Device (NC{i:02X})
        {{
            Name (_HID, EisaId ("NCP0000"))
            Name (_STA, 0x0B)
            Method (_UID, 0, NotSerialized)
            {{
                Return (RD2 (0x{0x80 + 2 * i:02X}))
            }}
        }}""")
    return "".join(out)


COMMON = """
    OperationRegion (NCP0, SystemIO, 0x72, 0x02)
    Field (NCP0, ByteAcc, NoLock, Preserve)
    {
        NCIX,   8,
        NCDT,   8
    }

    OperationRegion (NCP1, SystemMemory, 0xFED1F400, 0x04)
    Field (NCP1, DWordAcc, NoLock, Preserve)
    {
        NCRG,   32
    }

    Method (RD1, 1, NotSerialized)
    {
        Store (Arg0, NCIX)
        Return (NCDT)
    }

    Method (RD2, 1, NotSerialized)
    {
        Store (RD1 (Arg0), Local0)
        Or (Local0, ShiftLeft (RD1 (Add (Arg0, 1)), 8), Local0)
        Return (Local0)
    }
"""

RCDEV = """
        Device (NCRC)
        {
            Name (_HID, EisaId ("NCP0000"))
            Name (_STA, 0x0B)
            Method (_UID, 0, NotSerialized)
            {
                Return (NCRG)
            }
        }"""


def probe_parts(addr, bypass=False, gpuoff=False, slpen=False):
    # Optional last step of _GTS: enter S3 from AML, as ACPICA does (SLP_TYP=5, then SLP_TYP+SLP_EN; SCI_EN stays set).
    # Marker 7 is set just before the write, marker 8 if the write returned and 0.5 s passed.
    slp_regions = """    OperationRegion (NCP5, SystemIO, 0x1004, 0x02)
    Field (NCP5, WordAcc, NoLock, Preserve)
    {
        NPMW,   16
    }

""" if slpen else ""
    slp = """
            MARK (7)
            Store (0x1401, NPMW)
            Store (0x3401, NPMW)
            Store (Zero, Local0)
            While (LLess (Local0, 5000))
            {
                Stall (100)
                Increment (Local0)
            }
            MARK (8)""" if slpen else ""
    # Optional last step of _GTS: stop the BIOS trapping the SLP_EN write, and store the read-back in CMOS 0xD8.
    nosmi = """
            Store (And (NSM0, 0xEF), NSM0)
            WR1 (0xD8, NSM0)""" if bypass else ""
    # Optional: shut down pipe B the way i915 does (plane, pipe, LVDS port, PLL). GMA MMIO BAR is 0xF0300000.
    # CMOS: 0xD9 DSPBCNTR[31:24] before, 0xDA PIPEBCONF[31:24] before, 0xDB DPLL_B[31:24] before,
    #       0xDC PIPEBCONF[31:24] after, 0xDD DPLL_B[31:24] after. Stall loops only: no scheduler here.
    gpu_regions = """    OperationRegion (NGP0, SystemMemory, 0xF0371000, 0x0200)
    Field (NGP0, DWordAcc, NoLock, Preserve)
    {{
        Offset (0x08),
        NPCF,   32,
        Offset (0x180),
        NDCT,   32,
        NDAD,   32
    }}

    OperationRegion (NGP1, SystemMemory, 0xF0306018, 0x04)
    Field (NGP1, DWordAcc, NoLock, Preserve)
    {{
        NDPL,   32
    }}

    OperationRegion (NGP2, SystemMemory, 0xF0361180, 0x04)
    Field (NGP2, DWordAcc, NoLock, Preserve)
    {{
        NLVD,   32
    }}

""".replace("{{", "{").replace("}}", "}") if gpuoff else ""
    gpu = """
            WR1 (0xD9, ShiftRight (NDCT, 24))
            WR1 (0xDA, ShiftRight (NPCF, 24))
            WR1 (0xDB, ShiftRight (NDPL, 24))
            Store (And (NDCT, 0x7FFFFFFF), NDCT)
            Store (NDAD, NDAD)
            Store (Zero, Local0)
            While (LLess (Local0, 200))
            {
                Stall (100)
                Increment (Local0)
            }
            Store (And (NPCF, 0x7FFFFFFF), NPCF)
            Store (Zero, Local0)
            While (LAnd (LNotEqual (And (NPCF, 0x40000000), Zero), LLess (Local0, 500)))
            {
                Stall (100)
                Increment (Local0)
            }
            Store (And (NLVD, 0x7FFFFFFF), NLVD)
            Store (And (NDPL, 0x7FFFFFFF), NDPL)
            WR1 (0xDC, ShiftRight (NPCF, 24))
            WR1 (0xDD, ShiftRight (NDPL, 24))""" if gpuoff else ""
    root = f"""
    External (XPTS, MethodObj)
    External (XWAK, MethodObj)

    Method (MARK, 1, NotSerialized)
    {{
        Store (0x{addr:02X}, NCIX)
        Store (Or (0xA0, Arg0), NCDT)
    }}

    Method (_PTS, 1, NotSerialized)
    {{
        If (LEqual (Arg0, 3)) {{ MARK (1) }}
        XPTS (Arg0)
        If (LEqual (Arg0, 3)) {{ MARK (2) }}
    }}

    OperationRegion (NCP2, SystemIO, 0x1030, 0x04)
    Field (NCP2, ByteAcc, NoLock, Preserve)
    {{
        NSM0,   8,
        Offset (0x02),
        NSM2,   8
    }}

    OperationRegion (NCP3, SystemIO, 0x1004, 0x02)
    Field (NCP3, ByteAcc, NoLock, Preserve)
    {{
        NPM0,   8,
        NPM1,   8
    }}

    OperationRegion (NCP4, SystemMemory, 0x7F5C2EBC, 0x01)
    Field (NCP4, ByteAcc, NoLock, Preserve)
    {{
        NTPO,   8
    }}

{gpu_regions}{slp_regions}    Method (WR1, 2, NotSerialized)
    {{
        Store (Arg0, NCIX)
        Store (Arg1, NCDT)
    }}

    Method (_GTS, 1, NotSerialized)
    {{
        If (LEqual (Arg0, 3))
        {{
            MARK (3)
            WR1 (0xD3, NTPO)
            WR1 (0xD4, NSM0)
            WR1 (0xD5, NSM2)
            WR1 (0xD6, NPM0)
            WR1 (0xD7, NPM1){nosmi}{gpu}{slp}
        }}
    }}

    Method (_BFS, 1, NotSerialized)
    {{
        If (LEqual (Arg0, 3)) {{ MARK (4) }}
    }}

    Method (_WAK, 1, NotSerialized)
    {{
        If (LEqual (Arg0, 3)) {{ MARK (5) }}
        XWAK (Arg0)
        If (LEqual (Arg0, 3)) {{ MARK (6) }}
        Return (Package (0x02) {{ 0x00, 0x00 }})
    }}
"""
    dev = f"""
        Device (NCMK)
        {{
            Name (_HID, EisaId ("NCP0000"))
            Name (_STA, 0x0B)
            Name (SAVD, 0xFFFF)
            Method (_INI, 0, NotSerialized)
            {{
                Store (RD1 (0x{addr:02X}), Local0)
                If (LEqual (And (Local0, 0xF0), 0xA0))
                {{
                    Store (Local0, SAVD)
                }}
                Else
                {{
                    Store (Add (0x0100, Local0), SAVD)
                }}
                Store (0x{addr:02X}, NCIX)
                Store (0xA0, NCDT)
            }}
            Method (_UID, 0, NotSerialized)
            {{
                Return (SAVD)
            }}
        }}"""
    return root, dev


def main():
    mode, out = sys.argv[1], sys.argv[2]
    root, dev = "", ""
    if mode == "probe":
        addr = int(sys.argv[3], 16)
        if not 0x80 <= addr <= 0xFF:
            sys.exit("marker address must be in the upper bank, 0x80-0xFF")
        opts = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else set()
        root, dev = probe_parts(addr, "nosmi" in opts, "gpuoff" in opts, "slpen" in opts)
    elif mode != "dump":
        sys.exit(__doc__)
    text = f"""/* Generated by tools/mk_s3probe.py {mode}. See that file for how to read the results. */
DefinitionBlock ("", "SSDT", 2, "NC10", "S3PROBE", 0x00000001)
{{{COMMON}{root}
    Scope (\\_SB)
    {{{RCDEV}{dev}{dump_devices()}
    }}
}}
"""
    open(out, "w").write(text)


if __name__ == "__main__":
    main()
