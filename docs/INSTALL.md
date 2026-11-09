# Installation

For a Samsung NC10 Plus (Atom N450, tested on BIOS 07JI.M065) that already has Mac OS X **10.6.0, build 10A432** installed. Installing 10.6 itself isn't covered here.

**Back up your EFI partition and `/System/Library/Extensions` first.** These steps change boot sectors and system drivers.

## 1. Collect the inputs

You need Python 3 and these four things. The build checks each by SHA-256, so a wrong version stops the build rather than producing a bad driver.

| Input | Where to get it |
|---|---|
| Stock `AppleIntelGMA950.kext`, `AppleIntelIntegratedFramebuffer.kext`, `AppleHDA.kext` | `/System/Library/Extensions` of an unmodified 10A432 install. Copy them to one folder |
| `VoodooPS2.zip` | The August 2009 build, circulated on InsanelyMac. The tested archive's SHA-256 is `9fc682b9407ac5178944dca5966cdc3bb547f73bf5bb3e184f5eeab868e8a8e0`. The build checks the trackpad binary, so a repackaged zip is fine |
| `HfsPlus32.efi` | `Drivers/HfsPlus32.efi` in [acidanthera/OcBinaryData](https://github.com/acidanthera/OcBinaryData) |
| `macserial` | `Utilities/macserial/` in the [OpenCore 1.0.8 release](https://github.com/acidanthera/OpenCorePkg/releases). Use `macserial.linux` on Linux |

## 2. Build

```
python3 scripts/build.py \
  --extensions /path/to/stock-kexts \
  --voodoo /path/to/VoodooPS2.zip \
  --hfsplus /path/to/HfsPlus32.efi \
  --macserial /path/to/macserial
```

The result goes in `out/`, which git ignores. It contains patched Apple binaries, so don't publish it. The build generates a fresh serial number, board serial, UUID and ROM for your `config.plist`.

`--config config-variants/config.clean-s3.plist` selects the alternative config. It is less reliable so far, see [s3-sleep.md](s3-sleep.md).

To check the result, run `ocvalidate` from the OpenCore release on `out/EFI/OC/config.plist`.

## 3. Prepare the USB drive

These commands are for a Linux host and a GPT drive whose first partition is a FAT32 EFI partition labelled `OPENCORE`. Replace `sdX` with your drive. **The wrong device name will destroy that disk.**

```
DISK=/dev/sdX; PART=/dev/sdX1

# Copy the files
sudo mount "$PART" /mnt
sudo cp -R out/EFI out/boot /mnt/
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

## 4. Change the system disk

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

## 5. BIOS and first boot

Set the BIOS ATA mode to **Compatible**, the setting used for the S3 tests. Select the USB drive as the boot device.

Verbose boot is on, so you'll see kernel text. OpenCore's default entry may not be your system volume, so choose it in the picker the first time.

## 6. Check that it worked

```
kextstat | grep -E 'GMA950|IntegratedFramebuffer'    # both should show version 6.0.1
system_profiler SPDisplaysDataType | grep Resolution  # 1024 x 600
```

For Quartz Extreme, run [`research/gl-tests/qecheck.py`](../research/gl-tests/qecheck.py) inside the desktop session. See [research/README.md](../research/README.md).

## Recovery

- **Won't boot, or no acceleration.** Restore your EFI backup from another machine, then restore the stock kexts from `/Library/Backups/nc10-stock-kexts`, `touch /System/Library/Extensions`, and rerun both `kextcache` commands.
- **Sleep hung and the power switch doesn't respond.** Remove the battery. This resets CMOS, so the BIOS may boot the hard drive until you select USB again.
- **Stock drivers came back after a cache rebuild.** Check that the two GPU kexts are still out of `/System/Library/Extensions`.
