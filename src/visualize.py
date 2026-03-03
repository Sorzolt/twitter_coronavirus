#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile


def sanitize_for_filename(s: str) -> str:
    out = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    if out:
        return out
    h = hashlib.md5(s.encode("utf-8")).hexdigest()[:8]
    return f"key_{h}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--percent", action="store_true")
    parser.add_argument("--output_path", default="")
    args = parser.parse_args()

    with open(args.input_path, encoding="utf-8") as f:
        counts = json.load(f)

    if args.key not in counts:
        raise KeyError(f"Key not found in reduced file: {args.key}")

    raw = counts[args.key]
    values = {}

    if args.percent:
        denom = counts.get("_all", {})
        for k, v in raw.items():
            d = denom.get(k, 0)
            values[k] = (v / d) if d else 0.0
    else:
        for k, v in raw.items():
            values[k] = float(v)

    top = sorted(values.items(), key=lambda kv: kv[1], reverse=True)[:10]
    top = sorted(top, key=lambda kv: kv[1])

    if args.output_path:
        out_path = args.output_path
    else:
        base = os.path.basename(args.input_path)
        stem = os.path.splitext(base)[0]
        suffix = "percent" if args.percent else "count"
        out_name = f"{stem}_{sanitize_for_filename(args.key)}_{suffix}.png"
        out_path = os.path.join("outputs", out_name)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", prefix="viz_", suffix=".dat") as tf:
        data_path = tf.name
        for label, val in top:
            tf.write(f"{label} {val}\n")

    title = f"{args.key} ({'percent' if args.percent else 'count'})"
    ylabel = "Percent" if args.percent else "Count"

    gp = f"""
set terminal pngcairo size 1000,400
set output "{out_path}"
set boxwidth 0.75
set style fill solid 1.0
set style data histograms
set grid ytics
set xtics rotate by -45
set xlabel "Key"
set ylabel "{ylabel}"
set title "{title}"
plot "{data_path}" using 2:xtic(1) notitle
"""
    try:
        subprocess.run(["gnuplot"], input=gp, text=True, check=True)
    finally:
        try:
            os.remove(data_path)
        except Exception:
            pass

    print(out_path)


if __name__ == "__main__":
    main()
