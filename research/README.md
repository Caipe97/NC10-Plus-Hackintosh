# Research material

Not needed to build or use the EFI. These are the tools behind the writeups, kept for anyone extending the work.

| Folder | Contents |
|---|---|
| `patch-stages/` | Intermediate GMA and framebuffer patches, in bring-up order. Stage 4 deliberately makes the kext's `start` fail after logging HEAD and EIR |
| `s3-instrumentation/` | Generators for the S3 probe SSDT and the kext and kernel marker patches |
| `re-tools/` | Mach-O helpers, a register tracer, the Ghidra export script and the Linux i915 capture script |
| `gl-tests/` | The OpenGL, Quartz Extreme and Core Image tests. Python 2.6, for 10.6's system Python |
| `rig/` | S3 cycle test, run from another machine over SSH |

## Running the GL tests

Run them inside the logged-in desktop session, because an SSH session only sees software GL:

```
sudo launchctl bsexec "$(ps -axo pid,comm | awk '/Dock$/{print $1}')" python qecheck.py
```

## Running the sleep cycle test

```
NC10_HOST=192.0.2.10 research/rig/sleep_cycles.sh LABEL COUNT SECONDS
```

`NC10_HOST` must be a plain address or hostname, because the script also pings it. Set the SSH user in `~/.ssh/config`. The script expects passwordless `sudo` for `pmset` and key-based SSH. The netbook's OpenSSH is old, so a current client needs these for that host:

```
KexAlgorithms +diffie-hellman-group14-sha1,diffie-hellman-group-exchange-sha1,diffie-hellman-group1-sha1
HostKeyAlgorithms +ssh-rsa
PubkeyAcceptedAlgorithms +ssh-rsa
Ciphers +aes128-ctr,aes128-cbc
```

Current OpenSSL may also refuse SHA-1 signatures for the RSA key, depending on your distribution's crypto policy.
