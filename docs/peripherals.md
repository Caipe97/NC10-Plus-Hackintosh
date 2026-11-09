# Peripherals: brightness, audio, keyboard, touchpad and USB 2.0

How each was brought up on top of the patched GMA 3150 graphics.

Machine: Samsung NC10 Plus, N150/N210/N220 family board, Atom N450, BIOS 07JI.M065. OpenCore 1.0.8 IA32, `KernelArch i386-user32`, SMBIOS MacBook1,1.

## Brightness

**Cause.** `AppleBacklight.kext` has a personality, `AppleIntelPanelA`, that matches an ACPI device named `backlight`. This firmware has none, so the panel attached as a plain `AppleDisplay` with no brightness control.

**Fix.** [`acpi/SSDT-PNLF.dsl`](../acpi/SSDT-PNLF.dsl) adds `\_SB.PNLF` with `_HID APP0002`, `_CID "backlight"`, `_UID 10` and `_STA 0x0B`. `_UID 10` selects the F10 family in `AppleBacklight`'s panel tables.

No framebuffer patch is needed. The stock framebuffer already drives the same PWM register as Linux (`BLC_PWM_CTL`, `0x61254`).

**Result.** The panel attaches as `AppleBacklightDisplay` with a brightness range of 0 to 128.

## Audio

Hardware: Realtek ALC269 on Intel 8086:27d8. Pins: speaker 0x14, headphone 0x15, external mic 0x18, internal mic 0x19.

There were two separate problems.

**1. AppleHDA never bound.** It only recognises a device named `HDEF`, and the firmware has no ACPI entry for the audio controller. AppleALC 1.9.8 has an i386 slice, supports 10.6 in 32-bit mode and renames the device itself, so no SSDT is needed. The config sets `alc-layout-id` to `24000000` (layout 36) on `PciRoot(0x0)/Pci(0x1B,0x0)`. Layouts 13, 33, 35, 44 and 138 share this pinout.

The log line `alc: error: no layout-id property found in configuration` still appears and is harmless.

**2. AppleHDA then aborted codec setup.**

```
Sound assertion "32 < fNumProcessingCoefficients" failed in ".../AppleHDAWidget.cpp" at line 308
```

`AppleHDAWidget::initForNodeID` reads a node's processing-coefficient count into a 32-entry array and fails the whole codec if the count is above 32. [`patches/patch_hda.py`](../patches/patch_hda.py) clamps the count to 32 in the i386 slice of AppleHDA 1.7.4a1. The clamp replaces the abort without removing the bound, since removing it would overflow the array.

**Delivery.** A failed AppleHDA leaves objects behind and can't be unloaded, so it can't be swapped on a running system. The patched binary replaces the stock one in `/System/Library/Extensions`.

macOS then lists speaker, headphone, line in and internal mic.

## Keyboard and touchpad

Hardware: PS/2 controller at `KBC0` (`PNP0303`) and `MSE0` (`PNP0F13`), Synaptics touchpad, firmware 7.2. 10.6 has no PS/2 driver, and the current acidanthera VoodooPS2 is x86_64 only.

The usable build is a `VoodooPS2.zip` from August 2009 with its own `AppleACPIPS2Nub.kext`.

**Panic about 125 seconds after boot.** `vm_map_unwire: entry is unwired`, with a backtrace through `OSKext::autounloadKext`. The Synaptics driver wins the match, so `VoodooPS2Mouse.kext` has no instance and macOS tries to auto-unload it. A kext injected by OpenCore is apparently not safe to unload. The config disables only that plugin.

**General rule for this setup:** don't inject a kext through OpenCore unless something will keep it in use.

### Two-finger taps sending the cursor flying

The driver's move path has no delta or width filter. A second finger makes the pad report a point between the fingers, and that leap went straight to the cursor.

[`patches/patch_trackpad.py`](../patches/patch_trackpad.py) adds a filter to the i386 slice. If X or Y moves more than 300 units in one packet, the last position is re-based so the computed delta is zero. The code sits in the ALPS packet handler, unused on a Synaptics pad.

The filter passed emulation. Its effect on the real touchpad has not been separately confirmed.

### Two-finger scrolling

This pad never reached the driver's multi-finger width test (W >= 9 or W < 3). Lowering `MultiFingerWLimit` to 6 in the trackpad kext's `Info.plist` made two-finger scrolling work. The build script applies this.

## USB 2.0

`AppleUSBEHCI` failed at every boot with `0xe00002be`, which meant `EHCI controller unable to take control from BIOS`. USB fell back to UHCI speed. Log entries from October 2009 show the same failure, so it predates this work.

Setting `UEFI > Quirks > ReleaseUsbOwnership` to true gives 480 Mb/s.
