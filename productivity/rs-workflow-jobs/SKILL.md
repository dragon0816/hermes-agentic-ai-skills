---
name: rs-workflow-jobs
description: Run the R&S workflow jobs (chipset coverage, sales-to-chipset, Jira weekly report, C4C tickets, team tickets) through the local Host Bridge, and report the result to Leo on Telegram.
version: 1.0.0
author: Leo Chi
license: UNLICENSED
platforms: [windows]
metadata:
  hermes:
    tags: [Productivity, Reporting, Jira, GitLab, Excel, Outlook]
---

# R&S workflow jobs

The Host Bridge (`n8n_workflow_system`) already owns the hard parts: Outlook and
Excel COM, the Jira and GitLab clients, and the chipset rules. It exposes them as
jobs over HTTP. **Call those jobs. Do not reimplement any of it** — that code has
a test suite and a decisions log behind it, and its failure modes are already
known.

## Running a job

```bash
python <skill>/scripts/bridge_job.py list
python <skill>/scripts/bridge_job.py run <job> --params '{"dryRun":true}' --notify
```

`--notify` posts the outcome to Telegram, with any chart or document the job
produced attached. Use it for anything scheduled, and for anything Leo asked for
and is not watching the terminal for.

`--params` is JSON matching that job's schema. `list` prints every job's schema
with which fields are required, so read it rather than guessing field names.

## The jobs that matter

| Job | What it answers |
|---|---|
| `chipset_readiness` | Current chipset coverage, and what appeared since the last scan |
| `sales_to_chipset` | Which chipsets in the sales pipeline still need development assigned (workflow 10) |
| `jira_weekly_report` | The AE weekly report (workflow 11) from Jira |
| `github_weekly_report` | GitHub Projects replacement for workflow 11 while Jira Cloud is unavailable; accepts `startTime`/`endTime`, uses GitHub comment timestamps, and falls back from empty GitHub Assignee to `SDE Assignee` |
| `jira_weekly_email` | The same report rendered as an Outlook draft, with its chart |
| `c4c_tickets_by_creator` | C4C tickets per team member and their status |
| `jira_team_tickets` | RS Jira tickets opened by the team and their status |

## Rules

**Dry-run first when a job writes.** `sales_to_chipset`, `jira_weekly_report` and
`c4c_tickets_by_creator` write to Excel workbooks Leo's team depends on. Every one
of them takes `dryRun`. On a scheduled run, dry-run first, check the verdict, and
only then run for real — unless Leo has said otherwise for that job.

**Chipset_requirement manual inserts must preserve vendor colors.** When promoting
CMP180/temp rows into `Chipset_requirement`, color column A by `Chipset Vendor`:
reuse the existing color for that vendor; if the vendor has no established color,
assign a light color not already used by another vendor. Verify by reading the
vendor/color map back before reporting success.

**Drafts are not sent.** The bridge is configured `email.allowSend: false`, so
`jira_weekly_email` files an unsent Outlook draft. That is deliberate. Report that
the draft is waiting and where; never try to work around it.

**Read `verdict.ok` before summarising.** `true` passed, `false` means the job ran
fine but the outcome fails its own check, `null` means the job has no pass/fail
(a scan, a report). `false` and a crashed job are different things and Leo needs
them worded differently: "did not pass" versus "broke".

**A job that fails is the headline.** Lead the report with it, say whether it will
retry on the next schedule or needs Leo, and give the error verbatim rather than
paraphrased.

## Reporting format

Markdown. Charts and diagrams the job produced go in as images — the script
already pulls them back and attaches them. Do not describe a chart in prose when
the chart itself is available.

Where a source could not be reached, name it and say why, then report everything
else. A partial report that is honest about its gaps beats a complete-looking one
that is guessing.
