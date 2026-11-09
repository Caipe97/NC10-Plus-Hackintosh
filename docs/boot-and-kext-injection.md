# Boot and kext injection

Two things about this setup that aren't obvious: why stock kexts can silently win over injected ones, and how a BIOS-only netbook boots OpenCore.

## Stock kexts in the prelinked cache beat injected ones

The patched graphics and audio kexts have the same bundle IDs as Apple's. OpenCore injected them successfully until macOS rebuilt its prelinked kernel cache. The new cache contained the stock kexts, and from then on the patched copies were not used. Graphics and audio dropped out with no error.

Everything tried on the injection side failed:

| Attempt | Result |
|---|---|
| `KernelCache` = `Mkext` | Stock kexts still used |
| `Kernel > Block` with `Exclude` | **Kernel panic at boot**: `Error unserializing prelink plist: forward reference detected`. Do not use this on a 10.6 prelinked cache |
| `KernelCache` = `Cacheless` | Stock kexts still used |
| Higher `CFBundleVersion` on the patched copies | Stock kexts still used |
| Adding `OSBundleRequired` | Stock kexts still used |

**What works is making sure the system has no same-ID copy to prefer**, in one of two ways:

1. **Injection, used for the GPU kexts.** Move the stock kexts out of `/System/Library/Extensions` and rebuild the caches. With nothing in the cache to compete, the injected copies load, shown by `kextstat` reporting version 6.0.1.
2. **Replacement, used for AppleHDA.** Replace the binary in `/System/Library/Extensions` and don't inject it.

Injection has a real advantage for development: patches can be tested by swapping files on the USB drive. The cost is that the system can't load the GPU drivers without that OpenCore copy.

A macOS update that replaces these kexts would undo the changes. On 10.6.0 that should only matter if you run Software Update, which you shouldn't on this machine.

## Booting OpenCore from BIOS

The NC10 Plus has no UEFI. OpenCore starts through DuetPkg, using boot sectors:

- `boot0` in the MBR
- `boot1f32` in the FAT32 partition's boot sector, keeping its BIOS parameter block
- `boot` (`bootIA32` from the OpenCore release) at the root of the partition

Three more details from this machine:

- OpenDuet keeps no boot-default variable, so the default picker entry is set by `HideAuxiliary` and by marking other entries as auxiliary with a `.contentVisibility` file containing `Auxiliary`.
- `dd` to `/dev/rdisk0` fails with "Resource busy" while macOS is running from that disk. Use `sudo fdisk -f boot0 -u -y /dev/rdisk0`, which also keeps the partition table.
- Each OpenCore copy is independent. If you have one on USB and one on the internal disk, edit the one you actually booted.

`config.plist` has `ScanPolicy` 0, `SecureBootModel` Disabled and verbose boot on (`-v keepsyms=1 debug=0x100`), which are useful while this is still experimental.
