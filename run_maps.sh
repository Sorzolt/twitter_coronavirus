#!/bin/bash

MAX_JOBS=8

for file in "/data/Twitter dataset"/geoTwitter20-*.zip
do
    base=$(basename "$file")

    # Skip if country output already exists.
    if [ -f "outputs/${base}.country" ]; then
        continue
    fi

    while [ $(jobs -r | wc -l) -ge $MAX_JOBS ]
    do
        sleep 2
    done

    echo "Processing $file"
    python3 -u src/map.py --input_path "$file" \
        > outputs/map_$(basename "$file" .zip).log 2>&1 &
done














