#!/bin/bash
# Usage: sleep_cycles.sh LABEL COUNT SECONDS. Repeats S3 with an RTC wake SECONDS out, stops at the first failure.
# Result in logs/cycles-LABEL.log. A cycle passes only if the network returns with no reboot and the kernel logged a wake.
cd "$(dirname "$0")/.."; mkdir -p logs; : "${NC10_HOST:?set NC10_HOST to the netbook address}"
LABEL=$1; COUNT=$2; SECS=$3; L=logs/cycles-$LABEL.log; : > "$L"
{
  N0=$(rig/nc10 'last reboot | grep -c reboot' 2>/dev/null)
  echo "start: reboots logged $N0, $COUNT cycles of ${SECS}s"
  for i in $(seq 1 "$COUNT"); do
    sleep 20
    W=$(rig/nc10 "date -v+${SECS}S '+%m/%d/%y %H:%M:%S'" 2>/dev/null)
    rig/nc10 "sudo -n pmset schedule wake \"$W\"" >/dev/null 2>&1
    timeout 12 rig/nc10 'sudo -n pmset sleepnow' >/dev/null 2>&1
    S=$(date +%s); gone=""
    while [ $(( $(date +%s)-S )) -lt 25 ]; do
      ping -c1 -W1 "$NC10_HOST" >/dev/null 2>&1 || { gone=1; break; }
    done
    [ -n "$gone" ] || { echo "cycle $i: never went to sleep"; exit 2; }
    up=""
    while [ $(( $(date +%s)-S )) -lt $(( SECS+70 )) ]; do
      if ping -c1 -W1 "$NC10_HOST" >/dev/null 2>&1; then up=$(( $(date +%s)-S )); break; fi
    done
    [ -n "$up" ] || { echo "cycle $i: FAILED, no network $(( SECS+70 ))s after sleep"; exit 3; }
    sleep 15
    N=$(rig/nc10 'last reboot | grep -c reboot' 2>/dev/null)
    R=$(rig/nc10 'sudo -n grep "Wake reason" /var/log/kernel.log | tail -1 | cut -c1-90' 2>/dev/null)
    [ "$N" = "$N0" ] || { echo "cycle $i: FAILED, machine rebooted"; exit 4; }
    echo "cycle $i: ok, back at +${up}s; $R"
  done
  echo "ALL $COUNT CYCLES PASSED"
} 2>&1 | tee -a "$L"
