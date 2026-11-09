# Quartz Extreme and Core Image on the GMA 3150

How Apple's GMA 950 kexts from Mac OS X 10.6.0 were made to drive the GMA 3150 in an Atom N450 (Pineview), with the real 3D path running.

All work is against build 10A432. Offsets are file offsets in the thin i386 binaries.

## Why it should be possible

The GMA 3150 is a close relative of the GMA 950 family. Linux drives both with `i915`, and Apple's GL user-space driver only sees what the kernel kext reports. If the kext can bring up the engine, display and memory on the new chip, the rest of Apple's stack has no reason to know the difference.

The obstacles are the places where Pineview really differs. The approach was to change as little as possible and let Apple's code run. Where the driver's behaviour was in doubt, the reference was what Linux actually does on this exact machine.

## Ground truth from Linux

[`research/re-tools/capture_i915.sh`](../research/re-tools/capture_i915.sh) boots a Debian live system with `i915` blacklisted, then records the registers before and after loading the driver, along with an mmiotrace. It gave the values the patches rely on:

| Register | Value | Meaning |
|---|---|---|
| Panel pipe | B | The internal panel is on pipe B |
| `DPLL_B` | `0x98046000` | Pixel clock setup for the panel |
| `FPB0` | `0x80059` | PLL divisors, 54.2 MHz |
| `HWS_PGA` | `0x00023000` | Status page address, a graphics address |

## The patches

The final patches are [`patches/patch_gma.py`](../patches/patch_gma.py) for the accelerator and [`patches/patch_fb.py`](../patches/patch_fb.py) for the framebuffer. Each verifies the bytes it replaces where those bytes are known, and refuses to overwrite any byte the kext linker relocates.

### Matching and identity

`Info.plist` gets `0xA0118086` added to `IOPCIPrimaryMatch` in both kexts, which is enough to load them. It is not enough to make them work, because both kexts also read the PCI ID themselves and choose code paths from it.

The ID reads in `probe` and `start` are replaced by `mov eax, 0x27A28086`, so both kexts believe they are on a 945GM. The GMA kext's engine setup, for example, branches on this ID when it programs fence registers.

### The hardware status page

Apple's engine setup gives the chip the physical address of the status page. This chip takes it through the GTT instead, which is also what the Linux capture shows, with `HWS_PGA` holding a graphics address.

The patch at `0x19111` writes a GTT entry for slot `0x1fffe` pointing at Apple's page (`phys | 7`, valid and snooped), sets `HWS_PGA` to `0x1fffe000`, and does a posting read. The slot is near the top of the GTT's 512 MB range, out of the way of Apple's allocations.

### Starting the ring

Apple's setup also programs the IP ring (`0x2040` to `0x204C`) and sets bit 7 of `INSTPM` (`0x20C0`). The jump at `0x19221` skips both. The render ring setup is untouched.

Early stages also skipped Apple's writes to fences 6 and 7 at `0x2018` and `0x201C`. The final patch keeps them, because Apple's tiled memory pools depend on them. The `Tiled256` cases in the GL test pass with them in place.

### Framebuffer

The framebuffer kext computes PLL values with 945 maths, which does not fit Pineview's PLL. Rather than reimplement it, `hwSetCRTC` is patched to load the two captured values:

- `FPB0 = 0x80059` at `0xA7D5`
- `DPLL_B = 0x98046000` at `0xA7E4`

This fixes the pixel clock at the panel's native timing, which is the reason the VGA port doesn't work. Lower modes still switch correctly, because the panel path keeps the same clock.

Two more fixes were needed once the desktop was up:

- **Cursor corruption.** `hwSetupMemory` is patched at `0x4711` and `0x4747` so the cursor bases come from GTT addresses.
- **Palette on pipe A.** `hwSetPowerState` saved the palette on pipe A during power-state changes. Pipe A isn't clocked on this machine, and Linux guards against that read. The patch at `0xB2FA` skips the save on pipe A and keeps the IMR and IER setup.

### Getting there in stages

The patches went in incrementally, with each stage tested by loading the kext from `/tmp` so a reboot returned to stock. The stages are in [`research/patch-stages/`](../research/patch-stages/).

| Stage | Result |
|---|---|
| Match only | Kext loaded and started, no hardware use |
| Status page and ring | Status page and ring set up, no 3D commands submitted yet |
| Stage 4, Apple's 3D tables | Apple's real 3D state tables ran on the chip: HEAD `0x108`, EIR 0 |
| Framebuffer stage 1 and 2 | Native 1024x600 and a clean cursor |
| Full pair at boot | Hardware OpenGL renderer listed and working |

One of the panics along the way was a bug in a patch's own jump target. Later patchers assert their jump arithmetic for that reason.

## Results

Tests run inside the Aqua session using `launchctl bsexec`, because an SSH session only sees software GL. Programs are in [`research/gl-tests/`](../research/gl-tests/), output in [`evidence/`](../evidence/).

| Test | Result | Log |
|---|---|---|
| Renderer | `Intel GMA 950 OpenGL Engine`, GL 1.4 APPLE-1.6.0, 83 extensions, 64 MB VRAM reported | `15-boot-accel.log` |
| Quartz Extreme | `CGDisplayUsesOpenGLAcceleration` = 1 | `16-qecheck.log` |
| Pixel readback | Triangle and clear colours correct | `16-qecheck.log` |
| Core Image into a hardware GL context | 44.44 fps on GPU, 15.81 fps with the software renderer | `21-ci-modes.log` |
| Mode switching | All 9 combinations of 1024x600, 640x480, 800x600 at 8, 16, 32 bpp returned no error | `22-modes-cycle.log` |
| Coverage test | 48 of 51 passed | `20-gltest.log` |
| Soak test | 18 minutes, 12,335 iterations, 0 mismatches, 0 GL errors | `23-soak-stop.log` |

Limits of this evidence:

- **The soak was planned for 60 minutes and stopped at about 18**, with no final line in its log. The system stayed up and the 18 minutes were clean, but a full hour has not been run.
- **The 3 coverage failures were not investigated.** Two are Alpha8 textures returning white RGB instead of black, which may be a wrong expectation in the test, since alpha is correct. The third is a 50% blend that is within 1 of the expected colour but has alpha 191 instead of 255.
- **An earlier Core Image test** ([`citest.py`](../research/gl-tests/citest.py)) showed 22.6 fps GPU-requested against 26.9 fps software, drawing into a bitmap context. The 44.44 figure comes from [`citest2.py`](../research/gl-tests/citest2.py), which renders into a hardware GL context, a more direct test of the GPU path.

## Limits

- GL 1.4 only, reported as a GMA 950. The name comes from Apple's GL driver and was deliberately left alone.
- Internal panel only, at its fixed clock. VGA would need Pineview PLL maths in `hwGetClockParams`.
- No H.264 decode path exists in this driver. MPEG-2 through `IODVDBundleName` is the realistic video target and has not been tried.
- 10.6.0 (10A432) only.

## Reproducing

Follow [INSTALL.md](INSTALL.md). A correct build produces binaries with the SHA-256 values listed in [`scripts/build.py`](../scripts/build.py), and those are the same files used for the results above.

The two kexts must be delivered as described in [Boot and kext injection](boot-and-kext-injection.md), or the stock copies will silently win.
