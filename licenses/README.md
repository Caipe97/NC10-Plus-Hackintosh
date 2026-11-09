# Third-party components

## Bundled in this repository

| Component | Version | Where | License | Source |
|---|---|---|---|---|
| OpenCore (BOOTIA32, OpenCore.efi, OpenRuntime, Ps2KeyboardDxe, boot0, boot1f32, bootIA32) | 1.0.8 | `EFI/`, `legacy-boot/` | BSD 3-Clause, [`OpenCorePkg-LICENSE.txt`](OpenCorePkg-LICENSE.txt) | [acidanthera/OpenCorePkg](https://github.com/acidanthera/OpenCorePkg) |
| Lilu | 1.7.2 | `EFI/OC/Kexts` | BSD 3-Clause, [`Lilu-LICENSE.txt`](Lilu-LICENSE.txt) | [acidanthera/Lilu](https://github.com/acidanthera/Lilu) |
| VirtualSMC | 1.3.8 | `EFI/OC/Kexts` | BSD 3-Clause, [`VirtualSMC-LICENSE.txt`](VirtualSMC-LICENSE.txt) | [acidanthera/VirtualSMC](https://github.com/acidanthera/VirtualSMC) |
| AppleALC | 1.9.8 | `EFI/OC/Kexts` | BSD 3-Clause, [`AppleALC-LICENSE.txt`](AppleALC-LICENSE.txt) | [acidanthera/AppleALC](https://github.com/acidanthera/AppleALC) |
| VoodooPS2Controller, AppleACPIPS2Nub | August 2009 build | `EFI/OC/Kexts` | None stated, see below | Community build, circulated on InsanelyMac |

The VoodooPS2 binaries came without a license file or source. They are included unmodified so the internal keyboard and touchpad work on first boot. If you hold rights in them and object, please open an issue and they will be removed.

## Not bundled, you supply these

| File | Why it isn't here |
|---|---|
| `AppleIntelGMA950.kext`, `AppleIntelIntegratedFramebuffer.kext`, `AppleHDA.kext` | Apple software. The repository contains only patchers, which change a small number of bytes in your own copy |
| `HfsPlus32.efi` | Apple's HFS+ driver, distributed by [acidanthera/OcBinaryData](https://github.com/acidanthera/OcBinaryData) |
