#!/bin/bash
# Compare ROMS energy diagnostics against a reference, within a tolerance.
# Usage:  scripts/compare_energy.sh <reference_energy.txt> <energy.txt> [rtol]
#
# Both files have one line per time step as ROMS prints it:
#
#   step  date  time  kinetic  potential  total  volume
#
# ("#" lines in the reference are comments). Step, date and time must match
# exactly. Each number may differ from the reference by at most
# rtol * (largest absolute value in that column of the reference); scaling by
# the column's largest value keeps values near zero (kinetic energy at the
# start) from failing on tiny absolute differences. rtol defaults to the
# "# rtol: <value>" line in the reference.
#
# Results differ in the last digits between CPU types and machines (different
# math library code paths), so exact digits are only expected on the same
# node type; the tolerance allows for that but not for real changes.
#
# Prints the largest relative difference per column, then PASS or FAIL;
# exits 0 on PASS, 1 on FAIL.

set -uo pipefail

ref=${1:?usage: scripts/compare_energy.sh <reference> <energy.txt> [rtol]}
new=${2:?usage: scripts/compare_energy.sh <reference> <energy.txt> [rtol]}
rtol=${3:-$(awk '/^# *rtol:/ {print $3; exit}' "${ref}")}
[ -n "${rtol}" ] || { echo "no rtol given and no '# rtol:' line in ${ref}"; exit 1; }

awk -v rtol="${rtol}" -v refname="${ref}" '
  function abs(x) { return x < 0 ? -x : x }
  NR == FNR {                                   # reference
    if ($0 ~ /^#/ || NF == 0) next
    nr++; for (i = 1; i <= 7; i++) r[nr, i] = $i
    for (i = 4; i <= 7; i++) if (abs($i) > big[i]) big[i] = abs($i)
    next
  }
  NF > 0 {                                      # new run
    nn++; for (i = 1; i <= 7; i++) n[nn, i] = $i
  }
  END {
    split("kinetic potential total volume", name, " ")
    bad = 0
    if (nr == 0) { print "FAIL: no reference lines in " refname; exit 1 }
    if (nn != nr) {
      printf "FAIL: %d time steps, reference has %d\n", nn, nr; exit 1
    }
    for (k = 1; k <= nr; k++) {
      if (n[k, 1] != r[k, 1] || n[k, 2] != r[k, 2] || n[k, 3] != r[k, 3]) {
        printf "FAIL: line %d is step %s %s %s, reference has %s %s %s\n", \
          k, n[k, 1], n[k, 2], n[k, 3], r[k, 1], r[k, 2], r[k, 3]; exit 1
      }
      for (i = 4; i <= 7; i++) {
        d = big[i] > 0 ? abs(n[k, i] - r[k, i]) / big[i] : abs(n[k, i] - r[k, i])
        if (d > worst[i]) worst[i] = d
        if (d > rtol && bad++ < 10)
          printf "  step %s %s: %s, reference %s (%.2e > rtol)\n", \
            r[k, 1], name[i - 3], n[k, i], r[k, i], d
      }
    }
    printf "largest relative difference (rtol %s):", rtol
    for (i = 4; i <= 7; i++) printf " %s %.2e", name[i - 3], worst[i]
    printf "\n"
    if (bad) { printf "FAIL: %d value(s) outside the tolerance\n", bad; exit 1 }
    printf "PASS: %d time steps within the tolerance\n", nr
  }
' "${ref}" "${new}"
