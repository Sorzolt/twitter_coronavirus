#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import zipfile
from collections import Counter, defaultdict


def extract_text(tweet_obj: dict) -> str:
    """
    Extract tweet text in a robust manner across common Twitter JSON variants.
    """
    if not isinstance(tweet_obj, dict):
        return ""

    # Standard text field.
    text = tweet_obj.get("text")
    if isinstance(text, str) and text:
        return text

    # Extended tweet field.
    ext = tweet_obj.get("extended_tweet")
    if isinstance(ext, dict):
        full_text = ext.get("full_text")
        if isinstance(full_text, str) and full_text:
            return full_text

    # Fallback fields sometimes present in datasets.
    full_text = tweet_obj.get("full_text")
    if isinstance(full_text, str) and full_text:
        return full_text

    return ""


def extract_country_code(tweet_obj: dict) -> str:
    """
    Extract country code from tweet['place']['country_code'] if present.
    Return 'NA' when unavailable or malformed.
    """
    if not isinstance(tweet_obj, dict):
        return "NA"

    place = tweet_obj.get("place")
    if isinstance(place, dict):
        cc = place.get("country_code")
        if isinstance(cc, str) and cc:
            return cc

    return "NA"


def main() -> None:
    # Command line arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", required=True)
    parser.add_argument("--hashtags_path", default="hashtags")
    args = parser.parse_args()

    # Load hashtag list.
    hashtag_keys = []
    with open(args.hashtags_path, encoding="utf-8") as f:
        for line in f:
            tag = line.strip()
            if tag:
                hashtag_keys.append(tag)

    hashtag_pairs = [(tag, tag.lower()) for tag in hashtag_keys]

    # Initialize counters.
    counter_lang = defaultdict(Counter)
    counter_country = defaultdict(Counter)

    # Open the zipfile and process each inner text file.
    with zipfile.ZipFile(args.input_path) as archive:
        for filename in archive.namelist():
            print(datetime.datetime.now(), args.input_path, filename)

            with archive.open(filename) as f:
                for raw_line in f:
                    # Decode JSON line safely.
                    try:
                        line = raw_line.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        continue
                    if not line:
                        continue

                    try:
                        tweet = json.loads(line)
                    except Exception:
                        continue

                    # Extract language, country, and text fields.
                    lang = tweet.get("lang", "und")
                    if not isinstance(lang, str) or not lang:
                        lang = "und"

                    country = extract_country_code(tweet)

                    text = extract_text(tweet)
                    text_lower = text.lower() if isinstance(text, str) else ""

                    # Update overall counts exactly once per tweet.
                    counter_lang["_all"][lang] += 1
                    counter_country["_all"][country] += 1

                    # Search hashtags and update per-hashtag counts.
                    for tag_key, tag_lower in hashtag_pairs:
                        if tag_lower and tag_lower in text_lower:
                            counter_lang[tag_key][lang] += 1
                            counter_country[tag_key][country] += 1

    # Ensure output directory exists.
    os.makedirs("outputs", exist_ok=True)

    # Construct output paths.
    base_name = os.path.basename(args.input_path)
    output_lang = os.path.join("outputs", base_name + ".lang")
    output_country = os.path.join("outputs", base_name + ".country")

    # Convert Counters to dict for JSON serialization.
    out_lang_obj = {k: dict(v) for k, v in counter_lang.items()}
    out_country_obj = {k: dict(v) for k, v in counter_country.items()}

    # Write outputs.
    with open(output_lang, "w", encoding="utf-8") as f:
        json.dump(out_lang_obj, f, ensure_ascii=False)

    with open(output_country, "w", encoding="utf-8") as f:
        json.dump(out_country_obj, f, ensure_ascii=False)

    print(output_lang)
    print(output_country)


if __name__ == "__main__":
    main()
