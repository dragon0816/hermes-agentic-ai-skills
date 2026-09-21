---
name: outlook-email-workflows
description: Use when searching Leo's Outlook mail via COM.
version: 1.0.0
author: Hermes Agent
license: UNLICENSED
platforms: [windows]
metadata:
  hermes:
    tags: [Email, Outlook, COM, Search, Attachments, Reporting]
---

# Outlook email workflows

Use this when Leo asks about his company mailbox and Gmail/IMAP connectors are not the active source. The reliable local path is Outlook COM from Python.

## Procedure

1. **Scope the query before scanning.** Resolve the date window, topic keywords, people, folders, and side effects. Default to read-only. Common defaults:
   - “today” = local calendar day from `datetime.now().date()`.
   - “最近三個禮拜” = 21 days.
   - “上禮拜六日” = the last Saturday/Sunday relative to today.
   - Scan `Inbox`, `Sent Items`, `Deleted Items`, `Drafts`, and Inbox subfolders when the user is checking whether they missed something.

2. **Use Outlook COM with bounded scans.** Sort newest first and stop once messages are older than the cutoff; this prevents long mailbox walks.

```python
import pythoncom, win32com.client
from datetime import datetime, timedelta
pythoncom.CoInitialize()
outlook = win32com.client.Dispatch('Outlook.Application').GetNamespace('MAPI')
folder = outlook.GetDefaultFolder(6)  # Inbox; 5 Sent, 3 Deleted, 16 Drafts
items = folder.Items
items.Sort('[ReceivedTime]', True)
```

3. **Match by subject, sender, recipients, and the first body window.** For business topics, search both English and Chinese aliases and normalize noisy prefixes (`RE:`, `FW:`, `*EXT*`). For people, include display names and email handles. Keep the search file under `%LOCALAPPDATA%/Temp/` as JSON so follow-up questions can reuse the same evidence.

4. **Group into threads before summarizing.** Normalize known subject families and group repeated replies; report the latest state, not every duplicate reply. Include the date range searched and the number of matches.

5. **For “today’s email” summaries, separate action from reference.** Prioritize: customer blockers, direct asks, technical follow-ups, approvals, weekly reports, then automated/noise. Mention unread status and attachments only when they affect action. Equipment/demo-loan approval notices are normally noise and should be skipped or filed unless they block customer action.

6. **For direct-mail alerts, include intent and content.** A bare subject is not enough; include a short `用意：` line inferred from the first meaningful body lines plus a compact `內容：` preview, capped so Telegram stays readable. This avoids a follow-up just to ask what the sender said.

7. **Calendar is not email, but Leo expects it in daily briefings.** For daily reports and questions about missed meeting notices, query Outlook Calendar for today’s events first, then mail; include meeting time, title, organizer, attendees, location/Teams, and preparation context. Do not rely on meeting invitation emails because they may be in Deleted or already accepted.

8. **For attachment requests, save files into a dated folder and verify by listing the folder.** Preserve sender grouping when requested.

```python
att.SaveAsFile(str(destination_path))
```

Return the final folder path and saved filenames. Keep a `saved_attachments_log.json` with source sender, subject, date, and saved file paths.

## Pitfalls

- Do not treat keyword hits as importance; business terms in signatures and long quoted threads create false positives. Score direct sender/subject/body hits higher than quoted text, then summarize by thread.
- Do not rely on unread-only search; Leo often asks whether something was missed, and relevant messages may already be read or in Deleted/Sent/Drafts.
- Do not scan every Outlook store recursively without a cutoff and per-folder cap; COM mailbox traversal can hang on non-mail folders and large stores.
- Skip or ignore folders whose `Items.Sort('[ReceivedTime]')` and `Items.Sort('[SentOn]')` both fail; Calendar/Contacts/Tasks are not mail evidence for email triage.
- Never send, delete, archive, or mark messages read unless Leo explicitly approves that exact mutation.

## Reporting style

Reply in Traditional Chinese. Keep the answer as a decision brief:

- `搜尋範圍` and match count.
- `需要優先處理` with bullets for each thread.
- `目前狀態 / 下一步` for each item.
- `沒有找到` items explicitly when the user named people or topics and they were absent.
