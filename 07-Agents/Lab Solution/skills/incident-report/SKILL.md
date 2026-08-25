---
name: incident-report
description: Generate an executive-level incident report as a PDF, including a summary, root cause, impact, and suggested remedial steps. Use when the user asks for a report, write-up, summary, or postmortem of an incident -- for example, "generate an executive-level report of the incident with suggested remedial steps."
---

# Incident Report
Executive reports are for people who weren't in the log files and won't
read raw evidence. Base the report on findings already established in
this conversation -- don't re-investigate from scratch unless nothing
relevant has been discussed yet.

Structure the report as:

1. **Executive Summary** -- two or three sentences: what broke, for how
   long, and the business impact.
2. **Timeline** -- key timestamped events (deploy, commit, first error,
   resolution if known).
3. **Root Cause** -- one clear sentence naming the cause, followed by the
   supporting evidence.
4. **Impact** -- affected service(s), duration, and any quantifiable
   effect (error counts, latency numbers) you can cite.
5. **Recommended Remedial Steps** -- concrete, prioritized actions to
   prevent recurrence. Not "monitor more closely" -- name the specific
   guardrail, test, or process change.

Keep it to one page. Avoid raw log lines and jargon a director wouldn't
recognize.

Once you've drafted the content, run render_report.py with a single JSON
argument containing the five fields above (title, executive_summary,
timeline, root_cause, impact, remedial_steps). Tell the user the report
is ready and include a markdown link (/reports/<filename>) in your response.