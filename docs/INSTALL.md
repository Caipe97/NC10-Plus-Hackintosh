# Installation

For a Samsung NC10 Plus (Atom N450, tested on BIOS 07JI.M065) that already has Mac OS X **10.6.0, build 10A432** installed. Installing 10.6 itself isn't covered here.

**Back up your EFI partition and `/System/Library/Extensions` first.** These steps change boot sectors and system drivers.

The usual route is below: boot the EFI without acceleration, then run one script on the netbook. If you'd rather build everything on a Linux machine, see [Building on another machine](#building-on-another-machine).

## 1. Get the files

You need this repository and one download:

| File | Where to get it | Where it goes |
|---|---|---|
| `HfsPlus32.efi` | `Drivers/HfsPlus32.efi` in [acidanthera/OcBinaryData](https://github.com/acidanthera/OcBinaryData) | `EFI/OC/Drivers/` in this repository, **before** step 2 |

## 2. Prepare the USB drive

These commands are for a Linux host and a GPT drive whose first partition is a FAT32 EFI partition labelled `OPENCORE`. Replace `sdX` with your drive. **The wrong device name will destroy that disk.**

```
DISK=/dev/sdX; PART=/dev/sdX1

# Copy the files
sudo mount "$PART" /mnt
sudo cp -R EFI legacy-boot/boot /mnt/
sudo umount /mnt

# Partition boot sector: boot1f32, keeping the BIOS parameter block
sudo dd if="$PART" of=orig.bs bs=512 count=1
cp legacy-boot/boot1f32 new.bs
dd if=orig.bs of=new.bs skip=3 seek=3 bs=1 count=87 conv=notrunc
dd if=/dev/urandom of=new.bs skip=496 seek=496 bs=1 count=14 conv=notrunc
sudo dd if=new.bs of="$PART" bs=512 count=1 conv=fsync

# MBR boot code, leaving the partition table alone
sudo dd if=legacy-boot/boot0 of="$DISK" bs=1 count=446 conv=notrunc,fsync
```

The `EFI` folder must contain `OC/config.full.plist`, because the script in step 4 looks for it.

## 3. First boot

Set the BIOS ATA mode to **Compatible**, the setting used for the S3 tests, and select the USB drive as the boot device.

Verbose boot is on, so you'll see kernel text. OpenCore's default entry may not be your system volume, so choose it in the picker the first time.

macOS starts without graphics acceleration or sound. That's expected at this stage.

## 4. Run the post-install

Copy this whole folder to the netbook and leave the USB drive plugged in. Double-click `postinstall/Install.command` and enter your password. If it won't open, run this in Terminal from the `postinstall` folder:

```
sudo python install.py
```

The script asks whether you want **everything** or **graphics acceleration only**. Graphics only leaves your audio driver stock and skips the touchpad fixes. The keyboard, touchpad, brightness and sleep setup from the first boot stay in place either way.

It checks your stock drivers by SHA-256, patches them in a temporary folder and shows what it will change. Nothing changes until you type `yes`. It then:

- adds the patched drivers to the EFI partition and switches it to `config.full.plist` or `config.gpu.plist`, keeping the old config as `config.plist.before-postinstall`
- moves the stock graphics drivers to `/Library/Backups/nc10-stock-kexts`
- for everything, installs the patched `AppleHDA`, saving the original in the same folder
- rebuilds the kext caches and sets `hibernatemode` to 0

It is safe to run again. Restart when it finishes, and boot from the same USB drive. After this the system **needs this OpenCore copy** to get graphics acceleration.

The EFI ships with one sample set of SMBIOS values, shared by everyone using this repository. That has no practical effect on 10.6. To use your own, run `macserial` from the OpenCore release on another machine and edit `config.plist`.

## Check that it worked

```
kextstat | grep -E 'GMA950|IntegratedFramebuffer'    # both should show version 6.0.1
system_profiler SPDisplaysDataType | grep Resolution  # 1024 x 600
```

For Quartz Extreme, run [`research/gl-tests/qecheck.py`](../research/gl-tests/qecheck.py) inside the desktop session. See [research/README.md](../research/README.md).

## Recovery

- **Won't boot, or no acceleration.** Restore your EFI backup from another machine, then restore the stock kexts from `/Library/Backups/nc10-stock-kexts`, `touch /System/Library/Extensions`, and rerun both `kextcache` commands.
- **Sleep hung and the power switch doesn't respond.** Remove the battery. This resets CMOS, so the BIOS may boot the hard drive until you select USB again.
- **Stock drivers came back after a cache rebuild.** Check that the two GPU kexts are still out of `/System/Library/Extensions`.

## Using your own OpenCore

If you already boot this netbook with your own OpenCore setup and only want acceleration, build just the two GPU kexts on the netbook. This doesn't change anything on your system:

```
python postinstall/install.py --build-only ~/Desktop/nc10-gpu-kexts
```

Then:

1. Copy both kexts to `EFI/OC/Kexts`.
2. Under `Kernel > Add`, add `AppleIntelIntegratedFramebuffer.kext` first (`ExecutablePath` `AppleIntelIntegratedFramebuffer`, `PlistPath` `Info.plist`), then `AppleIntelGMA950.kext` (`ExecutablePath` `Contents/MacOS/AppleIntelGMA950`, `PlistPath` `Contents/Info.plist`). Set `Arch` to `i386` on both.
3. Copy the `PciRoot(0x0)/Pci(0x2,0x0)` entry from `DeviceProperties > Add` in `EFI/OC/config.gpu.plist`.
4. Move the stock kexts aside and rebuild the caches, or the stock copies will win without any error:

```
E=/System/Library/Extensions; BK=/Library/Backups/nc10-stock-kexts
sudo mkdir -p $BK
sudo mv $E/AppleIntelGMA950.kext $E/AppleIntelIntegratedFramebuffer.kext $BK/
sudo touch $E
sudo kextcache -system-prelinked-kernel
sudo kextcache -system-mkext
```

The framebuffer patch contains this panel's pixel clock, so another Pineview netbook would need its own values. See [gma3150-qe-ci.md](gma3150-qe-ci.md#framebuffer).

## Building on another machine

`scripts/build.py` produces the same files on a machine with Python 3, and generates unique SMBIOS values. Besides `HfsPlus32.efi`, it needs:

- stock `AppleIntelGMA950.kext`, `AppleIntelIntegratedFramebuffer.kext` and `AppleHDA.kext` from an unmodified 10A432 install, in one folder
- `macserial` from `Utilities/macserial/` in the [OpenCore 1.0.8 release](https://github.com/acidanthera/OpenCorePkg/releases)

```
python3 scripts/build.py \
  --extensions /path/to/stock-kexts \
  --hfsplus /path/to/HfsPlus32.efi \
  --macserial /path/to/macserial
```

The result goes in `out/`, which git ignores. It contains patched Apple binaries, so don't publish it. Copy `out/EFI` and `out/boot` to the USB drive as in step 2, using `out/` in place of the repository's own `EFI` and `legacy-boot/boot`.

`--config EFI/OC/config.gpu.plist` builds the graphics-only setup. `--config config-variants/config.clean-s3.plist` selects the alternative config. It is less reliable so far, see [s3-sleep.md](s3-sleep.md).

Run these on the netbook, with `out/system` copied over. They move the stock GPU drivers aside so the injected copies win, and install the patched audio driver. [Boot and kext injection](boot-and-kext-injection.md) explains why.

```
E=/System/Library/Extensions; BK=/Library/Backups/nc10-stock-kexts
sudo mkdir -p $BK
sudo cp -Rp $E/AppleHDA.kext $BK/
sudo mv $E/AppleIntelGMA950.kext $E/AppleIntelIntegratedFramebuffer.kext $BK/

sudo cp system/AppleHDA.kext/Contents/MacOS/AppleHDA $E/AppleHDA.kext/Contents/MacOS/AppleHDA
sudo chown root:wheel $E/AppleHDA.kext/Contents/MacOS/AppleHDA
sudo chmod 755 $E/AppleHDA.kext/Contents/MacOS/AppleHDA

sudo touch $E
sudo kextcache -system-prelinked-kernel
sudo kextcache -system-mkext
sudo pmset -a hibernatemode 0
```

After this, the system **needs this OpenCore copy** to get graphics acceleration.
