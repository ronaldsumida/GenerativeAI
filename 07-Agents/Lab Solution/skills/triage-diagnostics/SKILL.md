---
name: triage-diagnostics
description: Diagnose incidents on the e-commerce platform by correlating log entries, deploys, and commits, and by computing latency trends. Use whenever the user asks what caused a problem, why something broke, or whether a service has been getting slower.
---

# Triage & Diagnostics
Services: api-gateway, auth-service, checkout-service, inventory-service,
payments-client (wraps a third-party payments-api), search-service.

## Method

1. Don't stop at the first error line you find. Check whether a deploy or
   commit around that time could be the root cause, using `get_deploys`
   and `get_commit`.
2. For questions about performance, slowness, or trends over time, prefer
   `compute_latency_stats` over raw `search_logs` -- a gradual degradation
   may never produce an ERROR or WARN line you could grep for.
3. Cite specific timestamps, service names, and (when relevant) commit
   SHAs in your findings so an engineer could verify your reasoning.
4. If the evidence doesn't clearly point to a single root cause, say so
   and state your confidence rather than guessing.

Keep chat answers concise and skimmable -- short paragraphs or a short
bulleted list, not long prose.

See `references/incident-patterns.md` for the failure signatures known to
recur on this platform.