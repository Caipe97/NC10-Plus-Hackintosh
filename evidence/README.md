# Test output

Output captured on the netbook during development, November 2026. The only edit is replacing the machine's hostname.

| File | What it shows |
|---|---|
| `15-boot-accel.log` | Hardware renderer listed, GL 1.4, 83 extensions |
| `16-qecheck.log` | Quartz Extreme active, pixel readback correct |
| `17-citest.log` | First Core Image test and a 30-second GL run, 179.5 fps |
| `18-fence.log` | QE check with Apple's fence setup kept |
| `20-gltest.log` | OpenGL coverage test, 48 of 51 |
| `21-ci-modes.log` | Core Image GPU vs CPU, and the mode list |
| `22-modes-cycle.log` | Switching through every mode and depth |
| `23-soak-stop.log` | End of the soak test, which stopped at about 18 minutes |
| `35-usb-qe.log` | QE check with the GPU kexts injected from USB |
| `cycles-diag.log` | S3 cycles, diagnostic config, 5 of 5 |
| `cycles-stage1.log` | S3 cycles, the config shipped as `EFI/OC/config.plist`, 5 of 5 |
| `cycles-final.log` | S3 cycles, `config-variants/config.clean-s3.plist`, failed on cycle 3 |

`Bluetooth`, `display: Not usable` and kext-style warning lines in these logs appear on most boots and are unrelated to the test.
