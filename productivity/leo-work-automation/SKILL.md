---
name: leo-work-automation
description: Use when configuring Leo's work automation agents/routines.
version: 1.0.0
author: Hermes Agent
license: UNLICENSED
platforms: [windows]
metadata:
  hermes:
    tags: [Productivity, Hermes, Bots, Cron, R&S, Email, Reporting]
---

# Leo Work Automation

Configure Leo's R&S automation as a small set of specialist profiles plus scheduled routines. Do not multiply long-running agents when a cron routine or on-demand profile is enough.

## Target profile map

Use these profile roles unless Leo changes the roster:

| Profile id | Role |
|---|---|
| `emailagent` | Mail watcher, thread history, daily triage, draft-only replies |
| `reportagent` | R&S ops reports: workflow 10/11, chipset readiness, sales-to-chipset, AE/Non-signaling reports, Confluence draft updates |
| `sapagent` | Ticket/HR snapshot agent: C4C, RS Jira, Jira support distribution, Apollo availability categories only |
| `instrumentagent` | Coding agent: on-demand Jira-assigned development across Leo's repos and DUT-control scripts |

If a profile id cannot be renamed because the desktop/gateway has it open, keep the id and change its `SOUL.md` plus `profile describe` text instead. Bot titles can be adjusted later in the UI; the stable id is what CLI and cron commands target.

## Procedure

1. **Inspect before changing.**
   ```bash
   hermes profile list
   hermes -p emailagent cron list
   hermes -p reportagent cron list
   hermes -p sapagent cron list
   hermes -p instrumentagent cron list
   ```
   Verify which jobs already exist before creating replacements.

2. **Set profile descriptions.**
   Use `hermes profile describe <profile> --text '<role>'`. Descriptions are visible to Bot Mode and routing surfaces.

3. **Update SOUL.md for the role.**
   Use the file tool to replace the relevant profile's `SOUL.md`. Keep standing rules in the profile soul: Traditional Chinese, concise Telegram style, read-only/draft-first behavior, and explicit blockers.

4. **Create routines inside the target profile, not the active profile.**
   The `cronjob_manage` tool writes to the active profile's cron store. For Bot/profile-specific routines, use the CLI with `-p`:
   ```bash
   hermes -p emailagent cron create "every 15m" "<self-contained prompt>" --name mail-direct-watch --deliver telegram --skill email-inbox-triage --skill himalaya --continuity
   hermes -p emailagent cron create "30 9 * * *" "<self-contained prompt>" --name daily-mail-triage --deliver telegram --skill email-inbox-triage --skill himalaya
   hermes -p reportagent cron create "30 16 * * 5" "<self-contained prompt>" --name friday-reports --deliver telegram --skill rs-workflow-jobs
   hermes -p sapagent cron create "weekdays at 8:45am" "<self-contained prompt>" --name ticket-hr-snapshot --deliver telegram --skill rs-workflow-jobs
   hermes -p sapagent cron create "every monday 8:30am" "<self-contained prompt>" --name jira-effort-distribution --deliver telegram --skill rs-workflow-jobs
   ```
   Every cron prompt must be self-contained because cron runs in a fresh session.

5. **Verify placement.**
   Re-run `hermes -p <profile> cron list` for each target profile and confirm the job appears in the intended profile. Also check the default profile so duplicate jobs are not left behind.

6. **Only remove old jobs after replacements exist.**
   Remove or pause default-profile jobs only after the target-profile job is listed and enabled. Prefer pause during migration if missing coverage would be costly.

## Recommended routines

- **Mail Watcher, long-running-by-cron:** every 10–15 minutes; use a script-only watchdog when possible. Establish a baseline first so old mail does not spam Leo, then deliver only new direct-to-Leo mail; keep stdout empty when there is nothing new. Skip equipment/demo-loan approval noise unless it blocks customer action.
- **Daily Mail Triage:** daily 09:30; start with today’s calendar events and meeting changes, then previous-24h mail. Include Cc-to-Leo, stale customer threads, owner, blocker, recommendation.
- **R&S Ops Reporter:** Friday 16:30; Host Bridge workflow 10/11, chipset readiness, sales-to-chipset, AE weekly, Non-signaling.
- **Ticket/HR Snapshot:** weekday morning; C4C, RS Jira, Apollo availability summarized only as available / leave / uncertain.
- **Coding Agent:** no recurring monitor. Start on demand from Leo or a selected Jira ticket; inspect repo state, use worktrees when practical, build/test before done.

## Pitfalls

- **Do not use `cronjob_manage` when the job must belong to a non-default Bot/profile.** It creates jobs in the current active profile, so the Bots pane will not show the routine under the intended agent.
- **Do not delete working default-profile jobs before verifying the replacement in the target profile.** A failed migration otherwise creates a silent reporting gap.
- **Do not treat profile display names and profile ids as interchangeable.** CLI routines target the stable id; UI titles can change later.
- **Do not expose Apollo HR details beyond scheduling usefulness.** Attendance data is sensitive; summarize only support availability categories.
- **Do not make the coding agent long-lived.** Code work is high-side-effect and repo-specific; run it only for explicit Jira/user tasks and stop before destructive operations.
