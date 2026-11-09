# Mac OS X 10.6 on the Samsung NC10 Plus, with Quartz Extreme and Core Image on the GMA 3150

OpenCore EFI, binary patches and writeups for running Snow Leopard 10.6.0 on a Samsung NC10 Plus (Intel Atom N450, GMA 3150).

The main result is **hardware OpenGL, Quartz Extreme and Core Image on the GMA 3150**. Apple never shipped a driver for this GPU. The patches here make Apple's own GMA 950 kexts drive it, including the real 3D path, at the panel's native 1024x600.

```
Renderer:                         Intel GMA 950 OpenGL Engine
OpenGL version:                   1.4 APPLE-1.6.0
CGDisplayUsesOpenGLAcceleration:  1
Core Image, GPU vs CPU:           44.44 fps vs 15.81 fps
GL soak, 18 minutes:              12,335 iterations, 0 pixel mismatches, 0 GL errors
```

Raw output is in [evidence/](evidence/). The full story is in [docs/gma3150-qe-ci.md](docs/gma3150-qe-ci.md).

## Status

| Feature | State | Notes |
|---|---|---|
| Graphics, 1024x600, cursor | Working | Patched GMA 950 kexts |
| Quartz Extreme and Core Image | Working | [Writeup](docs/gma3150-qe-ci.md) |
| Brightness | Working | SSDT only, no driver patch |
| Audio (ALC269) | Working | "Everything" install only. AppleALC plus a patched AppleHDA. Pops under some games, see [known issues](docs/known-issues.md) |
| Keyboard and touchpad | Working | Bundled 2009 VoodooPS2. The "Everything" install adds the touchpad jump filter and two-finger scrolling |
| USB 2.0 | Working | One OpenCore quirk |
| Ethernet | Working | Stock AppleYukon2 |
| S3 sleep and wake | Experimental | Worked 5 of 5 in the shipped config, but see [the writeup](docs/s3-sleep.md) before relying on it |
| Wi-Fi (AR9285) | Not working | Diagnosis in [known issues](docs/known-issues.md) |
| Bluetooth | Unreliable | Fails at most boots, predates this work |
| VGA output | Not working | Needs Pineview PLL maths in the framebuffer |
| H.264 decode | Not available | The driver has no such path |

## Requirements

- Samsung NC10 Plus with the N450, tested on BIOS 07JI.M065. The patches contain values captured from this panel and firmware, so other machines need changes.
- Mac OS X **10.6.0, build 10A432**, already installed. The build checks the SHA-256 of your stock files, and 10.6.2 and later dropped Atom support anyway.
- OpenCore 1.0.8 IA32, included here.

## Getting started

Apple's kexts can't be redistributed, so the EFI in this repository first boots without acceleration. You then run one script on the netbook, which patches the stock drivers already on your system and finishes the setup. Every input and output is verified by SHA-256.

The script offers two install options:

| Option | Adds to the first-boot setup |
|---|---|
| **Everything** | Graphics acceleration, audio and the touchpad fixes |
| **Graphics acceleration only** | Graphics acceleration. Your audio driver stays stock, so there is no sound |

The built-in keyboard and touchpad, brightness, USB 2.0 and the sleep patches come with the first-boot setup, so you get them with either option.

If you already boot this netbook with your own OpenCore setup, the script can build just the two GPU kexts instead.

The only extra download is `HfsPlus32.efi`. Follow [docs/INSTALL.md](docs/INSTALL.md).

## What's in the repository

| Path | Contents |
|---|---|
| `EFI/` | OpenCore 1.0.8 IA32, SSDTs, the bundled kexts, and three configs: `config.plist` for the first boot, then `config.full.plist` or `config.gpu.plist` for the finished setup |
| `legacy-boot/` | BIOS boot files, needed because this netbook has no UEFI |
| `patches/` | The patchers that produce the working drivers |
| `postinstall/` | The script that finishes the install on the netbook |
| `scripts/build.py` | Alternative: assembles the complete EFI on another machine |
| `acpi/` | SSDT sources |
| `config-variants/` | An alternative config with less S3 instrumentation, less reliable so far |
| `docs/` | Installation guide and writeups |
| `evidence/` | Unedited test output behind the claims above, with only the hostname replaced |
| `research/` | Earlier patch stages, instrumentation and test programs |
| `licenses/` | Licenses for the bundled third-party components |

## Writeups

- [GMA 3150 QE/CI](docs/gma3150-qe-ci.md): how Apple's GMA 950 driver was made to run on Pineview
- [S3 sleep](docs/s3-sleep.md): tracing a silent hang to a hidden kernel panic
- [Peripherals](docs/peripherals.md): brightness, audio, PS/2, touchpad and USB 2.0
- [Boot and kext injection](docs/boot-and-kext-injection.md): the prelinked cache problem and BIOS booting
- [Known issues](docs/known-issues.md): what still doesn't work and how far each diagnosis got

## Disclaimer

This patches kernel drivers and the kernel on old hardware. A bad sleep cycle has needed a battery pull to recover. Use it at your own risk and keep a backup of your EFI partition.

Not affiliated with or endorsed by Apple, Samsung or Intel.

## Third-party components

OpenCore, Lilu, VirtualSMC and AppleALC are from [Acidanthera](https://github.com/acidanthera), under the BSD 3-Clause licenses in [licenses/](licenses/). VoodooPS2 is a 2009 community build with no stated license. See [licenses/README.md](licenses/README.md) for what is and isn't bundled.
