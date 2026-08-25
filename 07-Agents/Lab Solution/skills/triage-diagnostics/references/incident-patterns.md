# Known incident patterns
- **Null-reference after deploy** -- a checkout or API error spikes
  shortly after a deploy. Check get_deploys for anything in the
  preceding hour and get_commit on the associated SHA.
- **Memory leak / restart** -- a service unexpectedly restarts with no
  single ERROR line explaining why. Look for a slow climb in latency or
  a repeating WARN pattern in the hours before the restart, then trace
  it back to the deploy that introduced it.
- **Third-party rate limiting** -- a wrapper service (e.g.
  payments-client) starts failing even though nothing on our side
  changed. Check timestamps against known third-party outage or rate
  limit windows, and recommend a mitigation such as backoff/retry or a
  circuit breaker.
- **Gradual latency creep** -- search_logs shows nothing wrong, but
  compute_latency_stats reveals p95/p50 climbing steadily over days.
  Look for a schema migration or config change near the start of the
  climb.