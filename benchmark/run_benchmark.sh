#!/bin/sh
set -eu

if [ -z "${CUSTOM_SERVER_URL:-}" ]; then
    echo "CUSTOM_SERVER_URL is not set"
    exit 1
fi

if [ -z "${NGINX_SERVER_URL:-}" ]; then
    echo "NGINX_SERVER_URL is not set"
    exit 1
fi

RESULTS_FILE="/tmp/benchmark-results.txt"
: > "$RESULTS_FILE"

run_benchmark() {
    name="$1"
    url="$2"
    run="$3"
    output_file="/tmp/ab-${name}-${run}.txt"

    echo
    echo "========================================"
    echo "$name - Run $run"
    echo "========================================"

    ab -n 1000 -c 10 "$url" | tee "$output_file"

    requests_per_second=$(awk -F: '/Requests per second:/ { gsub(/^[ \t]+/, "", $2); print $2 + 0 }' "$output_file")
    time_per_request=$(awk -F: '/Time per request:/ && /mean/ && !/across all concurrent requests/ { gsub(/^[ \t]+/, "", $2); print $2 + 0 }' "$output_file")
    failed_requests=$(awk -F: '/Failed requests:/ { gsub(/^[ \t]+/, "", $2); print $2 + 0 }' "$output_file")
    transfer_rate=$(awk -F: '/Transfer rate:/ { gsub(/^[ \t]+/, "", $2); print $2 + 0 }' "$output_file")

    printf "%s|%s|%.2f|%.3f|%s|%.2f\n" \
        "$name" "$run" "$requests_per_second" "$time_per_request" "$failed_requests" "$transfer_rate" \
        >> "$RESULTS_FILE"
}

for run in 1 2 3; do
    run_benchmark "Custom Python Server" "$CUSTOM_SERVER_URL" "$run"
    sleep 2
done

for run in 1 2 3; do
    run_benchmark "nginx" "$NGINX_SERVER_URL" "$run"
    if [ "$run" -lt 3 ]; then
        sleep 2
    fi
done

echo
echo "========================================"
echo "Summary"
echo "========================================"
printf "%-22s %-6s %-14s %-20s %-16s %-14s\n" \
    "Target" "Run" "Req/sec" "Time/req mean ms" "Failed requests" "KB/sec"

awk -F'|' '{
    printf "%-22s %-6s %-14.2f %-20.3f %-16s %-14.2f\n", $1, $2, $3, $4, $5, $6
}' "$RESULTS_FILE"

custom_avg_rps=$(awk -F'|' '$1 == "Custom Python Server" { total += $3; count++ } END { printf "%.2f", total / count }' "$RESULTS_FILE")
custom_avg_time=$(awk -F'|' '$1 == "Custom Python Server" { total += $4; count++ } END { printf "%.3f", total / count }' "$RESULTS_FILE")
nginx_avg_rps=$(awk -F'|' '$1 == "nginx" { total += $3; count++ } END { printf "%.2f", total / count }' "$RESULTS_FILE")
nginx_avg_time=$(awk -F'|' '$1 == "nginx" { total += $4; count++ } END { printf "%.3f", total / count }' "$RESULTS_FILE")
ratio=$(awk -v nginx="$nginx_avg_rps" -v custom="$custom_avg_rps" 'BEGIN { printf "%.2f", nginx / custom }')

echo
echo "Custom Python Server average requests/sec: $custom_avg_rps"
echo "Custom Python Server average mean time/request: $custom_avg_time ms"
echo "nginx average requests/sec: $nginx_avg_rps"
echo "nginx average mean time/request: $nginx_avg_time ms"
echo "nginx is ${ratio}x faster by requests per second."
