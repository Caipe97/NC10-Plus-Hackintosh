# Known issues

What doesn't work yet, and how far each diagnosis got. Items marked as hypotheses have not been proven.

## S3 sleep reliability

See [s3-sleep.md](s3-sleep.md). The shipped config passed 5 of 5 cycles, and a cleaner config hung or lost network. The cause is unknown.

## Wi-Fi (Atheros AR9285, 168c:002b)

The card is unclaimed on 10.6.0. Its `AirPortAtheros` 411.19.4 can't drive this chip: the HAL rejects `0x2b`, and there are no Kite tables or 4K EEPROM code, so spoofing the ID won't help.

10.6.3's `AirPortAtheros21.kext` 422.9.8 has full AR9285 code and an i386 slice, and its HAL accepts `0x2b`. Only the `Info.plist` lacks the ID. With the ID added, it passes `kextutil -nt` against 10.6.0's IO80211Family 300.20.

It has not been loaded. The open question is whether the 422 driver is ABI-compatible with the 300.20 family.

## Bluetooth

The kernel log shows `hardwareSetupComplete Failed setup: 0x10` and HCI timeouts on most boots, going back to October 2009, so this predates all of this work. It also fails again around sleep and wake.

**Hypothesis:** it only initialises after a true cold start. The boots where it succeeded line up with forced power-offs and battery pulls. No cold-boot test has been run.

## Audio popping and game freezes

Constant pops in some games, and some games freezing after loading. Native clean playback has not yet been compared.

**Hypothesis, not measured during play:** the affected games (Jedi Knight II, Quake 3, Medal of Honor) are PowerPC builds running under Rosetta on the Atom, which may starve the audio thread.

Other facts that may matter:

- The layout uses `AFGLowPowerState` 3 and the engine stops when idle, so codec power transitions could also pop.
- The DSDT and SSDTs have no HPET device, though the firmware has an HPET table at `0xFED00000`.
- `AppleIntelCPUPowerManagement` loads but never starts.

Changing the audio quality in Jedi Outcast once hung both the game and audio, without a crash report or panic in the logs.

## VGA output

The framebuffer patch fixes the PLL to the panel's clock. VGA needs real Pineview PLL maths in `hwGetClockParams`.

## Video decode

The driver has no H.264 path. MPEG-2 through `IODVDBundleName` is the realistic target and hasn't been tried.

## GL soak length

The soak ran for 18 clean minutes out of a planned 60. See [gma3150-qe-ci.md](gma3150-qe-ci.md#results).
