"""
Write the ROMS input file of an application from its run.yaml and params.yaml.
EXPERIMENTAL: Runs/moana.in is still the file in use.

  python scripts/make_roms_in.py Apps/moana              # -> Apps/moana/roms_moana.in
  python scripts/make_roms_in.py Apps/moana --draft      # write also when values are "(yet to decide)"
  python scripts/make_roms_in.py Apps/moana -o test.in   # other output file

  1. Read the ROMS default input file (roms/User/External/roms.in) as the template
  2. Collect the new values: params.yaml (grid, vertical, time), then run.yaml
  3. Work out the values that come from others: NTIMES, DSTART, TIDE_START, NHIS, ..., NFFILES
  4. Stop if a value is "(yet to decide)" (not with --draft)
  5. Write the template with the new values; all other lines stay as they are

The draft file keeps the text "(yet to decide)", so ROMS cannot run with it by mistake.
"""
import argparse
import datetime
import difflib
import re
import sys
from pathlib import Path

import yaml

# %% 0. Settings
REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "roms" / "User" / "External" / "roms.in"
OPEN = "(yet to decide)"

# keys that params.yaml owns: section -> ROMS keywords
PARAMS_KEYS = {
    "grid": ["Lm", "Mm"],
    "vertical": ["N", "Vtransform", "Vstretching", "THETA_S", "THETA_B", "TCLINE"],
    "time": ["TIME_REF", "DT", "NDTFAST"],
}
# run.yaml output section -> (keyword for the interval in time steps, prefix of the variable switches)
OUTPUT = {
    "history": ("NHIS", "Hout"),
    "average": ("NAVG", "Aout"),
    "quick": ("NQCK", "Qout"),
    "diagnostics": ("NDIA", "Dout"),
    "restart": ("NRST", None),
}
# file keyword -> keyword that counts its files
FILE_COUNTS = {"FRCNAME": "NFFILES", "BRYNAME": "NBCFILES", "CLMNAME": "NCLMFILES"}

# "   KEY == value" (a line that starts with "!" is a comment)
KEYWORD = re.compile(r"^(\s*)([A-Za-z][\w()]*)(\s*==?\s*)(.*)$")


def read_template(path):
    """Template lines, and for each keyword: first line number, number of lines,
    text before the value, comment of each line, and the values."""
    lines = path.read_text().splitlines()
    entries = {}
    i = 0
    while i < len(lines):
        m = KEYWORD.match(lines[i])
        if not m or lines[i].lstrip().startswith("!"):
            i += 1
            continue
        indent, key, sep, rest = m.groups()
        value, _, comment = rest.partition("!")
        values = value.replace("\\", " ").split()
        comments = [comment.strip()]
        n = 1
        while value.rstrip().endswith("\\"):            # value goes on in the next line
            value, _, comment = lines[i + n].partition("!")
            values += value.replace("\\", " ").split()
            comments.append(comment.strip())
            n += 1
        if key in entries:
            sys.exit(f"Template has {key} twice: {path}")
        entries[key] = {"line": i, "n_lines": n, "prefix": indent + key + sep,
                        "comments": comments, "values": values}
        i += n
    return lines, entries


def fortran(v):
    """One YAML value as ROMS input text: true -> T, 25.0 -> 25.0d0, 1.0e-5 -> 1.0d-05."""
    if isinstance(v, bool):
        return "T" if v else "F"
    if isinstance(v, float):
        mantissa, _, exponent = repr(v).partition("e")
        if "." not in mantissa:
            mantissa += ".0"
        return f"{mantissa}d{exponent or 0}"
    return str(v)


def flat(v):
    """[[a, b], [c, d]] -> [a, b, c, d]; a -> [a]."""
    if not isinstance(v, list):
        return [v]
    return [x for item in v for x in flat(item)]


def render(key, value, entry):
    """Text lines for one keyword. A value that is in more than one template line
    is split the same way (for example LBC(isTvar): one line per tracer)."""
    values = [fortran(x) for x in flat(value)]
    n = entry["n_lines"]
    if key.endswith("NAME") and len(values) > 1:       # file names: one per line
        rows = [[x] for x in values]
    elif n > 1 and len(values) % n == 0:
        k = len(values) // n
        rows = [values[j * k:(j + 1) * k] for j in range(n)]
    else:
        rows = [values]
    pad = " " * len(entry["prefix"])
    out = []
    for j, row in enumerate(rows):
        text = (entry["prefix"] if j == 0 else pad) + "  ".join(row)
        if j < len(rows) - 1:
            text += " \\"
        if len(rows) == n and entry["comments"][j]:   # same lines as the template: keep its comments
            text += "    ! " + entry["comments"][j]
        out.append(text)
    return out


def is_open(*values):
    return any(OPEN in flat(v) for v in values)


def to_date(v):
    """2026-01-01 (YAML date) or 20260101 (TIME_REF) -> date."""
    if isinstance(v, datetime.date):
        return v
    return datetime.datetime.strptime(str(v).split(".")[0].replace("-", ""), "%Y%m%d").date()


def days(a, b):
    """Days from date b to date a, as a float."""
    return float((to_date(a) - to_date(b)).days)


def whole_steps(seconds, dt, what):
    """seconds / DT; stops when it is not a whole number of time steps."""
    steps = seconds / dt
    if steps != int(steps):
        sys.exit(f"{what}: {seconds} s is not a whole number of time steps of DT = {dt} s")
    return int(steps)


# %% 1. Template and inputs
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("app", type=Path, help="application folder with run.yaml and params.yaml, e.g. Apps/moana")
parser.add_argument("-o", "--out", type=Path, help="output file (default: <app>/roms_<app name>.in)")
parser.add_argument("--draft", action="store_true", help='write also when values are "(yet to decide)"')
args = parser.parse_args()

lines, entries = read_template(TEMPLATE)
params = yaml.safe_load((args.app / "params.yaml").read_text())
run = yaml.safe_load((args.app / "run.yaml").read_text())
out_file = args.out or args.app / f"roms_{args.app.resolve().name}.in"

# %% 2. New values: params.yaml first, then run.yaml
new = {}
for section, keys in PARAMS_KEYS.items():
    for key in keys:
        new[key] = params[section][key]
start, end = params["time"]["start"], params["time"]["end"]

owned_by_params = [k for keys in PARAMS_KEYS.values() for k in keys]
tide_date = None
for section, items in run.items():
    if section in ("schema_version", "output"):
        continue
    for key, value in items.items():
        if key == "tide_zero_phase_date":
            tide_date = value
        elif key in owned_by_params:
            sys.exit(f"run.yaml: {key} belongs in params.yaml")
        else:
            new[key] = value

# %% 3. Values that come from others
dt, time_ref = new["DT"], new["TIME_REF"]
if not is_open(time_ref):
    new["TIME_REF"] = float(to_date(time_ref).strftime("%Y%m%d"))
new["NTIMES"] = OPEN if is_open(start, end, dt) else whole_steps(
    (to_date(end) - to_date(start)).total_seconds(), dt, "start to end")
new["DSTART"] = OPEN if is_open(start, time_ref) else days(start, time_ref)
if tide_date is not None:
    new["TIDE_START"] = OPEN if is_open(tide_date, time_ref) else days(tide_date, time_ref)

open_vars = []                                          # output sections with vars "(yet to decide)"
for name, spec in run.get("output", {}).items():
    if name not in OUTPUT:
        sys.exit(f"run.yaml output: unknown section {name}; use one of {list(OUTPUT)}")
    step_key, prefix = OUTPUT[name]
    hours = spec["every_hours"]
    new[step_key] = OPEN if is_open(hours, dt) else whole_steps(hours * 3600, dt, f"output {name}")
    if "vars" not in spec:
        continue
    if is_open(spec["vars"]):
        open_vars.append(f"output {name} vars")
        continue
    switches = [k for k in entries if k.startswith(prefix + "(")]
    ids = [k[len(prefix) + 1:-1] for k in switches]
    unknown = [v for v in spec["vars"] if v not in ids]
    if unknown:
        sys.exit(f"run.yaml output {name}: unknown ids {unknown}; see {prefix}(...) in {TEMPLATE}")
    for key, id_ in zip(switches, ids):
        new[key] = [id_ in spec["vars"]] * len(entries[key]["values"])

for name_key, count_key in FILE_COUNTS.items():
    if name_key in new and not is_open(new[name_key]):
        new[count_key] = len(flat(new[name_key]))

# %% 4. Checks
unknown = [k for k in new if k not in entries]
for key in unknown:
    close = difflib.get_close_matches(key, entries, n=3)
    print(f"Not a ROMS keyword: {key}" + (f" (did you mean {', '.join(close)}?)" if close else ""))
if unknown:
    sys.exit(1)

still_open = [k for k, v in new.items() if is_open(v)] + open_vars
if still_open:
    print(f'{len(still_open)} values are "{OPEN}":\n  ' + "\n  ".join(still_open))
    if not args.draft:
        sys.exit("Nothing written. Decide them in run.yaml / params.yaml, or use --draft.")

# %% 5. Write
replace = {entries[k]["line"]: k for k in new}
text = [
    f"! Made by scripts/make_roms_in.py from {args.app}/run.yaml and {args.app}/params.yaml.",
    "! Template: roms/User/External/roms.in. Do not edit this file; edit run.yaml and run the script again.",
]
if still_open:
    text.append(f'! DRAFT: {len(still_open)} values are "{OPEN}". ROMS cannot run with this file.')
i = 0
while i < len(lines):
    if i in replace:
        key = replace[i]
        text += render(key, new[key], entries[key])
        i += entries[key]["n_lines"]
    else:
        text.append(lines[i])
        i += 1
out_file.write_text("\n".join(text) + "\n")
print(f"Wrote {out_file} ({len(new)} keywords changed from the ROMS defaults)")
