#!/usr/bin/env bash
# run.sh — Build and run the Tech Job Scraper in Docker
# Usage: ./run.sh [--location "Bengaluru"] [--pages 3] [--sources naukri linkedin]

set -e

IMAGE="tech-job-scraper"
OUTPUT_DIR="$(pwd)/output"
mkdir -p "$OUTPUT_DIR"

echo "==> Building Docker image..."
docker build -t "$IMAGE" .

echo "==> Running scraper..."
docker run --rm \
  --shm-size=2g \
  -v "$OUTPUT_DIR:/app/output" \
  "$IMAGE" \
  --location "Bengaluru" \
  --pages 3 \
  --sources naukri linkedin \
  --output /app/output/tech_jobs.json \
  "$@"

echo ""
echo "Done! Results saved to: $OUTPUT_DIR/tech_jobs.json"
echo "Job count: $(python3 -c "import json; d=json.load(open('$OUTPUT_DIR/tech_jobs.json')); print(d['total'])" 2>/dev/null || echo '(install python3 to count)')"
