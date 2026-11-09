#!/bin/bash
# Ground-truth capture of Linux i915 bringing up the GMA 3150.
# Boot Debian live with the kernel option modprobe.blacklist=i915, then run as root:
#   mkdir -p /mnt/oc && mount LABEL=OPENCORE /mnt/oc && bash /mnt/oc/capture_i915.sh
# Results go to the OPENCORE partition under i915-capture/.
set -u
OUT=/mnt/oc/i915-capture
mkdir -p "$OUT" || exit 1
exec > >(tee "$OUT/run.log") 2>&1
echo "== start $(date)"; uname -a; cat /proc/cmdline

if lsmod | grep -q '^i915 '; then
  echo "ERROR: i915 is already loaded. Reboot and add modprobe.blacklist=i915 to the boot options."
  exit 2
fi

GPU=/sys/bus/pci/devices/0000:00:02.0
T=/sys/kernel/tracing
[ -d "$T/events" ] || mount -t tracefs nodev "$T"
mountpoint -q /sys/kernel/debug || mount -t debugfs nodev /sys/kernel/debug

lspci -nn > "$OUT/lspci.txt" 2>&1
lspci -vvvxxx -s 00:02.0 > "$OUT/lspci-gpu.txt" 2>&1
lspci -vvvxxx -s 00:02.1 >> "$OUT/lspci-gpu.txt" 2>&1
lspci -vvvxxx -s 00:00.0 > "$OUT/lspci-host.txt" 2>&1
cat /proc/iomem > "$OUT/iomem.txt"

cat > /tmp/regs.py <<'PY'
import mmap, struct, sys
# Only named registers: reading arbitrary MMIO can hang the GPU.
R = {0x2020:'PGETBL_CTL',0x2080:'HWS_PGA',0x2018:'INSTPM',0x201c:'MI_MODE?',0x209c:'0x209c',
 0x20c0:'0x20c0',0x20a0:'IER',0x20a4:'IIR',0x20a8:'IMR',
 0x2030:'LP_TAIL',0x2034:'LP_HEAD',0x2038:'LP_START',0x203c:'LP_CTL',
 0x2040:'IP_TAIL',0x2044:'IP_HEAD',0x2048:'IP_START',0x204c:'IP_CTL',
 0x6014:'DPLL_A',0x6040:'FPA0',0x6044:'FPA1',0x70008:'PIPEACONF',
 0x70080:'CURACNTR',0x70084:'CURABASE',0x70088:'CURAPOS',
 0x70180:'DSPACNTR',0x70184:'DSPABASE',0x70188:'DSPASTRIDE',
 0x61180:'LVDS',0x61254:'BLC_PWM_CTL'}
f = open(sys.argv[1], 'r+b')
m = mmap.mmap(f.fileno(), 0x80000)
for a, n in sorted(R.items()):
    v = struct.unpack('<I', m[a:a+4])[0]
    print('%06x %08x %s' % (a, v, n))
PY
if command -v python3 >/dev/null; then
  echo 1 > "$GPU/enable" 2>/dev/null
  timeout 20 python3 /tmp/regs.py "$GPU/resource0" > "$OUT/regs-before.txt" 2>&1
  echo "regs-before exit $?"
else
  echo "python3 missing, skipping register snapshots"
fi

HAVE_TRACE=0
if grep -qw mmiotrace "$T/available_tracers" 2>/dev/null; then HAVE_TRACE=1; fi
echo "mmiotrace available: $HAVE_TRACE"; cat "$T/available_tracers"

if [ "$HAVE_TRACE" = 1 ]; then
  echo 64000 > "$T/buffer_size_kb"
  echo mmiotrace > "$T/current_tracer"
  gzip -1 < "$T/trace_pipe" > "$OUT/mmiotrace.txt.gz" &
  TP=$!
  sleep 2
fi

echo "== loading i915 $(date)"
modprobe i915 enable_guc=0 2>&1 || modprobe i915 2>&1
echo "modprobe exit $?"
sleep 25

if [ "$HAVE_TRACE" = 1 ]; then
  echo nop > "$T/current_tracer"
  sleep 3
  kill "$TP" 2>/dev/null
  wait "$TP" 2>/dev/null
fi

if command -v python3 >/dev/null; then
  timeout 20 python3 /tmp/regs.py "$GPU/resource0" > "$OUT/regs-after.txt" 2>&1
  echo "regs-after exit $?"
fi

D=$(ls -d /sys/kernel/debug/dri/* 2>/dev/null | head -1)
if [ -n "$D" ]; then
  mkdir -p "$OUT/debugfs"
  for f in i915_capabilities i915_engine_info i915_gem_objects i915_display_info \
           i915_frequency_info i915_gtt_info i915_swizzle_info i915_runtime_pm_status; do
    [ -e "$D/$f" ] && timeout 10 cat "$D/$f" > "$OUT/debugfs/$f" 2>&1
  done
fi

dmesg > "$OUT/dmesg.txt"
lsmod > "$OUT/lsmod.txt"
sync
ls -la "$OUT"
echo "== DONE $(date). You can now reboot into Mac OS X."
touch "$OUT/DONE"
sync
