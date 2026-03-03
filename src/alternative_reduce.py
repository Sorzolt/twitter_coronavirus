import argparse
import glob
import json
import os
import re
import subprocess
import tempfile
from datetime import date


def parse_day_from_filename(path: str) -> date | None:
    # Extract date from filenames like outputs/geoTwitter20-05-20.zip.lang
    base = os.path.basename(path)
    m = re.match(r"geoTwitter(\d{2})-(\d{2})-(\d{2})\.zip\.(lang|country)$", base)
    if not m:
        return None
    yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return date(2000 + yy, mm, dd)


def load_total_for_hashtag(day_path: str, hashtag: str) -> int:
    # Sum counts across language/country buckets for a given hashtag key.
    with open(day_path, encoding="utf-8") as f:
        d = json.load(f)
    if hashtag not in d:
        return 0
    return int(sum(d[hashtag].values()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hashtags", nargs="+", required=True)
    parser.add_argument("--suffix", choices=["lang", "country"], default="lang")
    parser.add_argument("--outputs_dir", default="outputs")
    parser.add_argument("--output_path", default="outputs/alternative_reduce.png")
    args = parser.parse_args()

    pattern = os.path.join(args.outputs_dir, f"geoTwitter20-*.zip.{args.suffix}")
    day_files = glob.glob(pattern)

    # Build sorted (date, path) list.
    dated = []
    for p in day_files:
        d = parse_day_from_filename(p)
        if d is not None:
            dated.append((d, p))
    dated.sort(key=lambda x: x[0])

    if not dated:
        raise RuntimeError(f"No daily files found matching: {pattern}")

    # Build one temp data file per hashtag: (day_index, count).
    tmp_paths = []
    try:
        for tag in args.hashtags:
            tf = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", prefix="alt_", suffix=".dat")
            tmp_paths.append(tf.name)
            with tf:
                for i, (_, path) in enumerate(dated, start=1):
                    tf.write(f"{i} {load_total_for_hashtag(path, tag)}\n")

        os.makedirs(os.path.dirname(args.output_path) or ".", exist_ok=True)

        # Compose gnuplot script.
        plot_parts = []
        for tag, p in zip(args.hashtags, tmp_paths):
            # Titles support UTF-8 with pngcairo.
            plot_parts.append(f'"{p}" using 1:2 with lines title "{tag}"')

        gp = f"""
set encoding utf8
set terminal pngcairo size 1100,450
set output "{args.output_path}"
set grid ytics
set xlabel "Day of year (2020)"
set ylabel "Tweet count (hashtag occurrences)"
set title "Hashtag frequency over 2020 ({args.suffix})"
plot {", ".join(plot_parts)}
"""
        subprocess.run(["gnuplot"], input=gp, text=True, check=True)
        print(args.output_path)

    finally:
        for p in tmp_paths:
            try:
                os.remove(p)
            except Exception:
                pass


if __name__ == "__main__":
    main()
