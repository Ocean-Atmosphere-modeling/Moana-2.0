#!/bin/bash
# Shell functions shared by the submit and job scripts.
# Usage:  source scripts/run_lib.sh
#
#   in_get <file.in> <KEY>            print the value of a ROMS input keyword
#   in_set <file.in> <KEY> <value>    change it in place (exactly one match)
#   bp_get <blueprint.yaml> <a.b.c>   print one value from a blueprint
#   seg_dir <run_dir> <k> <n>         directory of segment k of an n-segment run

# ROMS input files have lines like "      NTIMES == 1440   ! comment"
# ("=" or "=="). Only the first value on the line is read or replaced.
in_get () {
  awk -v k="$2" '$1 == k && ($2 == "=" || $2 == "==") {print $3; exit}' "$1"
}

in_set () {
  local file=$1 key=$2 value=$3 n
  n=$(awk -v k="${key}" '$1 == k && ($2 == "=" || $2 == "==")' "${file}" | wc -l)
  if [ "${n}" -ne 1 ]; then
    echo "in_set: expected one '${key}' line in ${file}, found ${n}" >&2
    return 1
  fi
  awk -v k="${key}" -v v="${value}" '
    $1 == k && ($2 == "=" || $2 == "==") {
      match($0, /^ */); printf "%*s%s %s %s\n", RLENGTH, "", $1, $2, v; next
    }
    { print }' "${file}" > "${file}.tmp" && mv "${file}.tmp" "${file}"
}

# Blueprints are a small subset of YAML: nested "key: value" lines indented
# by two spaces per level, no lists. bp_get file compile_time.header
bp_get () {
  awk -v want="$2" '
    /^[[:space:]]*(#|$)/ { next }
    {
      match($0, /^ */); d = RLENGTH / 2
      line = $0; sub(/^ +/, "", line)
      k = line; sub(/:.*/, "", k)
      v = line; sub(/^[^:]*: */, "", v); sub(/ +#.*$/, "", v); gsub(/^"|"$/, "", v)
      path[d] = k; p = path[0]
      for (i = 1; i <= d; i++) p = p "." path[i]
      if (p == want) { print v; exit }
    }' "$1"
}

# A run with one segment keeps everything in the run directory; a chained
# run gives each segment its own seg_NN/ folder.
seg_dir () {
  if [ "$3" -eq 1 ]; then echo "$1"; else printf '%s/seg_%02d\n' "$1" "$2"; fi
}
