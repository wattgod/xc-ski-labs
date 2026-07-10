#!/bin/bash
set -e
cd /Users/mattirowe/Documents/NordicLab/nordic-race-automation

# Load API key from .env — NEVER hardcode keys in scripts
if [ -f .env ]; then
    export $(grep -E '^ANTHROPIC_API_KEY=' .env | xargs)
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set. Add it to .env or export it."
    exit 1
fi

# Get all races needing enrichment (without videos)
SLUGS=$(python3 -c "
import json, glob
slugs = []
for f in sorted(glob.glob('race-data/*.json')):
    if '_schema' in f: continue
    d = json.load(open(f))
    r = d.get('race', {}).get('nordic_lab_rating', {})
    yt = d.get('race', {}).get('youtube_data', {})
    if not yt.get('videos'):
        slugs.append(d['race']['slug'])
print(' '.join(slugs))
")

TOTAL=$(echo $SLUGS | wc -w | tr -d ' ')
echo "=== YouTube enrichment batch: $TOTAL races ==="
echo "Started: $(date)"

COUNT=0
SUCCESS=0
FAIL=0

for slug in $SLUGS; do
    COUNT=$((COUNT + 1))
    echo ""
    echo "[$COUNT/$TOTAL] Researching: $slug"

    # Research phase
    python3 scripts/youtube_research.py --slug "$slug" --max-results 8 --transcript --output youtube-research-results/ 2>&1 | grep -E "Found|Query|SUMMARY"

    # Enrich phase
    if python3 scripts/youtube_enrich.py --slug "$slug" 2>&1; then
        SUCCESS=$((SUCCESS + 1))
    else
        FAIL=$((FAIL + 1))
    fi

    # Rate limit: 1 second between races
    sleep 1
done

echo ""
echo "=== BATCH COMPLETE ==="
echo "Total: $TOTAL | Success: $SUCCESS | Failed: $FAIL"
echo "Finished: $(date)"
