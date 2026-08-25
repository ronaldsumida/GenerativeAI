import re, json, statistics

LOG_PATH = "data/app.log"
DEPLOYS_PATH = "data/deploys.json"
COMMITS_PATH = "data/commits.json"

MAX_RESULTS = 200 # Max lines to return from app.log in a single tool call

def _load_lines():
    with open(LOG_PATH) as f:
        return f.readlines()

def _load_json(path):
    with open(path) as f:
        return json.load(f)

# ISO-8601 timestamps (2026-07-14T14:32:05.034Z) sort correctly as plain
# strings, so we can filter start/end with simple string comparison instead
# of parsing datetimes on every line -- much faster over ~34k lines.
def _in_range(ts, start, end):
    if start and ts < start:
        return False
    if end and ts > end:
        return False
    return True

def search_logs(query: str = "", level: str = None, service: str = None,
                start: str = None, end: str = None) -> str:
    """
    Search application logs for lines matching a text query.

    Args:
        query: Substring or regex to match against the log message
            (case-insensitive). Optional -- omit or leave empty to match
            every line, useful when filtering purely by level/service/date.
        level: Optional exact filter, one of INFO, DEBUG, WARN, ERROR.
        service: Optional exact filter, e.g. "checkout-service".
        start: Optional ISO-8601 timestamp lower bound, e.g., "2026-07-14T14:00:00".
        end: Optional ISO-8601 timestamp upper bound.

    Returns:
        Up to 200 matching log lines, newest first, plus a count of total
        matches if truncated.
    """

    pattern = re.compile(query, re.IGNORECASE) if query else None
    matches = []

    for line in _load_lines():
        ts = line[:24]  # timestamp is a fixed-width prefix
        if level and f" {level:<5} " not in line:
            continue
        if service and f" {service:<18} " not in line:
            continue
        if not _in_range(ts, start, end):
            continue
        if pattern is None or pattern.search(line):
            matches.append(line.rstrip())

    total = len(matches)
    matches = matches[-MAX_RESULTS:]
    header = f"{total} matching lines" + (f" (showing most recent {MAX_RESULTS})" if total > MAX_RESULTS else "")
    return header + "\n" + "\n".join(matches)

def get_deploys(service: str = None, start: str = None, end: str = None) -> str:
    """
    Look up deploy history, optionally filtered by service and/or time window.

    Args:
        service: Optional exact service name filter, e.g. "checkout-service".
        start: Optional ISO-8601 timestamp lower bound.
        end: Optional ISO-8601 timestamp upper bound.

    Returns:
        JSON list of matching deploy records (deploy_id, timestamp, service,
        version, commit, author, notes).
    """

    deploys = _load_json(DEPLOYS_PATH)
    out = []

    for d in deploys:
        if service and d["service"] != service:
            continue
        if not _in_range(d["timestamp"], start, end):
            continue
        out.append(d)

    return json.dumps(out, indent=2)

def get_commit(sha: str) -> str:
    """
    Look up a single commit by its SHA.

    Args:
        sha: The commit hash, e.g. "a1b2c3d" (as found in a deploy record).

    Returns:
        JSON commit record (sha, timestamp, author, message, files), or an
        error message if not found.
    """

    commits = _load_json(COMMITS_PATH)

    for c in commits:
        if c["sha"] == sha:
            return json.dumps(c, indent=2)

    return f"No commit found with sha={sha}"

def compute_latency_stats(service: str, start: str = None, end: str = None) -> str:
    """
    Compute latency statistics (mean, p50, p95, max) for a service's logged
    request/query durations over a time window. Use this instead of raw
    search_logs when asked about performance trends, slowness, or degradation
    over time -- grepping for WARN/ERROR won't surface a gradual latency
    creep that never crosses an error threshold.

    Args:
        service: Service name, e.g. "search-service".
        start: Optional ISO-8601 timestamp lower bound.
        end: Optional ISO-8601 timestamp upper bound.

    Returns:
        JSON summary with sample count and latency stats in milliseconds,
        plus first/last timestamp in the sample so trends can be reasoned
        about across multiple calls (e.g. compare early-window vs late-window).
    """

    pattern = re.compile(r"in (\d+)ms")
    samples = []

    for line in _load_lines():
        ts = line[:24]
        if f" {service:<18} " not in line:
            continue
        if not _in_range(ts, start, end):
            continue
        m = pattern.search(line)
        if m:
            samples.append((ts, int(m.group(1))))

    if not samples:
        return json.dumps({"service": service, "count": 0, "note": "no timed samples found in range"})

    values = [v for _, v in samples]
    values_sorted = sorted(values)
    p95_idx = int(len(values_sorted) * 0.95)

    result = {
        "service": service,
        "count": len(values),
        "first_timestamp": samples[0][0],
        "last_timestamp": samples[-1][0],
        "mean_ms": round(statistics.mean(values), 1),
        "p50_ms": values_sorted[len(values_sorted) // 2],
        "p95_ms": values_sorted[min(p95_idx, len(values_sorted) - 1)],
        "max_ms": max(values),
    }

    return json.dumps(result, indent=2)