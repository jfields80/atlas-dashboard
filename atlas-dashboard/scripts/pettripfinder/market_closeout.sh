#!/usr/bin/env bash
#
# Everything a market work order does AFTER the last paid call, in order.
#
#   scripts/pettripfinder/market_closeout.sh st-louis-mo PTF-ST-LOUIS-PAID-ACQUISITION-002
#
# Every step is offline and free. They are sequenced here rather than run by
# hand because the ORDER is load-bearing: the observation store reads the merged
# acquisition view, closure reads the store, the founder package reads closure's
# inputs, and the benchmark reads all of them. Running one against a stale
# predecessor is the failure this file exists to make impossible.
set -euo pipefail

MARKET="${1:?market id, e.g. st-louis-mo}"
WORK_ORDER="${2:?work order id}"
AS_OF="${3:-$(date -u +%Y-%m-%d)}"
# Every acquisition run directory this market has, oldest first. Named rather
# than derived: a run directory is chosen by whoever launched the run, and a
# script that GUESSES the name silently examines nothing when it guesses wrong.
shift 3 2>/dev/null || shift $#
RUN_DIRS=("$@")
if [ ${#RUN_DIRS[@]} -eq 0 ]; then
  echo "usage: $0 <market> <work-order> <as-of> <run-dir> [run-dir ...]" >&2
  exit 2
fi

SLUG="${MARKET//-/_}"
PKG="launch_packages/pettripfinder"
PRIOR="$PKG/${SLUG}_direct_http_pilot_001.json"
PAID="$PKG/${SLUG}_paid_acquisition_002.json"
MERGED="$PKG/${SLUG}_acquisition_merged_002.json"
RECOVERY="$PKG/${SLUG}_zero_cost_recovery_002.json"
STORE="$PKG/${SLUG}_observation_store_002.json"
CLOSURE="$PKG/${SLUG}_closure_ledger_002.json"
PARTITION="$PKG/${SLUG}_final_partition_002.json"
PACKET="$PKG/${SLUG}_founder_review_packet_002.json"

echo "== 1. offline recovery over EVERY pass's declined evidence =="
# Every run directory, not just the newest. Asking only the paid pass reports
# that this market's offline recovery examined nothing, while the documents an
# earlier pass preserved sit on disk unread.
RUN_DIR_ARGS=()
for dir in "${RUN_DIRS[@]}"; do RUN_DIR_ARGS+=(--run-dir "$dir"); done
python scripts/pettripfinder/acquisition/zero_cost_recovery.py \
  "${RUN_DIR_ARGS[@]}" \
  --market "$MARKET" --work-order "$WORK_ORDER" --out "$RECOVERY"

echo "== 2. fold every acquisition pass into one current-state view =="
python scripts/pettripfinder/acquisition/acquisition_merge.py \
  --market "$MARKET" --work-order "$WORK_ORDER" \
  --pass "$PRIOR" --pass "$PAID" --out "$MERGED"

echo "== 3. observation store, rebuilt from the merged view =="
python scripts/pettripfinder/acquisition/market_observation_store.py \
  --pilot "$MERGED" --run-id "${MARKET}-002" --out "$STORE"

echo "== 4. active eligibility, partition, closure ledger =="
python scripts/pettripfinder/market_closure_cli.py \
  --market "$MARKET" --observations "$STORE" --pilot "$MERGED" \
  --as-of "$AS_OF" --work-order "$WORK_ORDER" \
  --closure-out "$CLOSURE" --partition-out "$PARTITION"

echo "== 5. founder-review package =="
python scripts/pettripfinder/market_founder_review_cli.py \
  --market "$MARKET" --observations "$STORE" \
  --as-of "$AS_OF" --work-order "$WORK_ORDER" --out "$PACKET"

echo
echo "closeout complete for $MARKET ($WORK_ORDER)"
