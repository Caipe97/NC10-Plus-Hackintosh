# S3 sleep on the NC10 Plus

How a silent sleep hang was traced to a kernel panic nobody could see, and what it takes to make S3 work.

**Status: experimental.** The shipped config passed 5 of 5 RTC-wake cycles. A cleaner config did worse, and the reason is unknown. See [Current state](#current-state).

## The symptom

With the GPU kexts loaded, `pmset sleepnow` left the netbook hung: power LED solid, fans on, no network, nothing in the logs.

An early test without the GPU kexts seemed to sleep fine, but that was misleading. The kernel logged `System Doze` and the panel stayed lit, so it never reached S3.

## Instrumentation

With no screen and no logs, the only channel that survives a hang is CMOS.

1. **An SSDT probe** ([`mk_s3probe.py`](../research/s3-instrumentation/mk_s3probe.py)) wraps `_PTS` and `_WAK`, adds `_GTS` and `_BFS`, and writes stage markers to CMOS `0xD2`. After a forced reboot the markers are read back through the `_UID` of small ACPI devices in `ioreg`.
2. **Kext markers** ([`mk_acpi_marks.py`](../research/s3-instrumentation/mk_acpi_marks.py)) add OpenCore patches to `AppleACPIPlatform` that write markers between its sleep steps, using an unused function for the code.
3. **Kernel markers** ([`mk_kernel_s3patch.py`](../research/s3-instrumentation/mk_kernel_s3patch.py)) do the same inside `acpi_sleep_kernel`.

Two oddities of 10.6's ACPI interpreter mattered here. It rejects the `If (Zero) { External ... }` block that a modern `iasl` emits, and one such block fails the whole SSDT, so [`aml_strip_externals.py`](../acpi/aml_strip_externals.py) removes it from the AML. It also truncates `_UID` strings to 9 characters.

## The wrong turns

The `_GTS` marker (`0xA3`) was the last thing written. That looked like a hang at the final write to `SLP_EN`, so several theories were tested against it:

| Theory | Test | Result |
|---|---|---|
| Firmware behaves differently by OS | Spoofed Windows 7 through `_OSI`, confirmed `TPOS` = 0x20 | Same hang |
| BIOS SMI handler traps the sleep write | Cleared `SLP_SMI_EN`, confirmed by read-back | Same hang |
| Display still running blocks entry | Disabled pipe B and `DPLL_B` from AML, confirmed by read-back | Same hang |
| Second CPU | Booted with `cpus=1` | Same hang, for reasons never measured |

Writing `SLP_EN` directly from AML did put the machine into real S3, with the sleep LED blinking, proving the hardware could do it. macOS couldn't resume from that, because the kernel had not saved its CPU state.

Decompiling `AppleACPIPlatform` then showed the premise was wrong. `_GTS` runs in `AcpiEnterSleepStatePrep`, well before the final write. Between the two come interrupt shutdown, PCI bridge power changes, and the kernel's `acpi_sleep_kernel`. Those earlier tests were therefore inconclusive, not negative.

## The cause

Kext markers placed the hang inside `acpi_sleep_kernel`, before Apple's callback. In the 10.6.0 i386 kernel, that function starts by taking every other CPU offline:

```
pmCPUExitHaltToOff(cpu)      nonzero return -> panic("Error %d trying to transition CPU %d to OFF")
```

`AppleIntelCPUPowerManagement` never starts on this Atom, so the power management dispatch table is not set up and the call returns an error. The kernel panics at a moment when the panel is already off, so the panic is invisible. It looks exactly like a hang.

A patch recording the return code in CMOS read back **4**, which confirmed it. With the panic skipped, the markers showed the whole path running through to `acpi_sleep_cpu`, and the first log with `System Sleep` followed by `System Wake` on the same boot appeared.

## The fix

**Kernel patch.** At `0x2AEB5F` in `acpi_sleep_kernel`, the `je` that jumps over the panic becomes an unconditional `jmp`. It is one byte, in `Kernel > Patch`, and matches 10A432 only.

**USB wake.** The machine then woke after about 3 seconds, with `Wake reason = USB1 USB2 USB3 EUSB`. OpenCore `ACPI > Patch` entries rename the `_PRW` methods for GPEs 3, 4, 0xC, 0xE and 0xD to `XPRW`, so the USB controllers can't wake it. This disables wake from USB devices.

After both, one run slept for 152 seconds and woke on the RTC on the same boot at 1024x600. Screen, keyboard, trackpad and lid sleep were confirmed by hand on the diagnostic config.

`hibernatemode` must be 0: `sudo pmset -a hibernatemode 0`.

## Current state

Repeated with [`sleep_cycles.sh`](../research/rig/sleep_cycles.sh), RTC wake 60 seconds after sleep. Output is in [`evidence/`](../evidence/).

| Config | Contents | Result |
|---|---|---|
| Diagnostic | Probe SSDT, kernel and kext markers | 5 of 5 |
| **Stage 1, shipped as `EFI/OC/config.plist`** | Probe SSDT, one-byte kernel patch | 5 of 5 |
| `config-variants/config.clean-s3.plist` | No probe, `SSDT-WAK` only | First attempt hung at resume, needing a battery pull. A second run passed 2 cycles, then lost network in cycle 3 |

In that third cycle the machine did wake: the kernel logged a normal wake with no reboot, and the wake was confirmed in person. The network didn't return within the test's 130 seconds, answered briefly much later, then stopped. It was not diagnosed.

The only differences between the shipped config and the clean one are the probe SSDT's `_PTS`, `_GTS` and `_BFS` wrappers with their CMOS writes, and the `_WAK` wrapper. It is not known why those would help. Five cycles is a small sample and the failure may be intermittent, so the clean config may not be truly worse.

The shipped config writes diagnostic bytes to CMOS `0xD2` and above on every sleep. It has only been run on BIOS 07JI.M065.

## Warnings

- A hung resume may ignore the power switch. Recovery is a battery pull, which resets CMOS, so the BIOS may then boot the hard drive until the USB drive is reselected.
- The USB installer volume dropped on wake once (`disk1s2` media not present). Keep your system on the internal disk.
- Sustained sleep has been tested to about 150 seconds, not for hours.
