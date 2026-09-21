---
name: business-cards
description: Read a business card photo Leo sends on Telegram, extract company, name, department, title and phone into a local store, and render a company grouping chart on request.
version: 1.0.0
author: Leo Chi
license: UNLICENSED
platforms: [windows]
metadata:
  hermes:
    tags: [Productivity, Contacts, OCR, Vision, Charts]
    related_skills: [rs-workflow-jobs]
---

# Business cards

Leo photographs cards and sends them on Telegram. Read the card, store what it
says, and be able to draw the company later.

## Reading a card

Look at the image and produce exactly this JSON — no prose, no code fence:

```json
{"name": "", "company": "", "department": "", "title": "", "phone": "",
 "mobile": "", "email": "", "address": "", "website": "", "notes": "",
 "uncertain": []}
```

- **Local-language form in `name` / `company`**, romanised form in `notes`. A card
  showing both 陳建宏 and Chien-Hung Chen stores 陳建宏 and notes the other; do not
  concatenate them into one field.
- **`phone` is the desk number, `mobile` is the cellphone.** Keep extensions
  (`#312`). A card with one number only: judge from the label, and if there is no
  label, put it in `phone` and list `phone` in `uncertain`.
- **`uncertain` is the point of this format.** A blurred digit, glare across the
  title, a department you inferred rather than read — name the field. A wrong phone
  number presented as fact costs Leo a call to nobody; a flagged one costs him a
  glance. Never guess silently to make the JSON look complete.
- **Omit a field rather than invent it.**

## Storing it

Write the JSON to a UTF-8 file and pass the path. Do **not** put Chinese in the
`--json` argument: on Windows it goes through the console code page and arrives
mangled.

```bash
python <skill>/scripts/cards.py add --json-file card.json
```

The reply tells you whether this person was already on file and what changed:

```json
{"stored": true, "name": "...", "previous": {"title": "經理", ...}, "changed": ["title"]}
```

**Every scan is kept.** A re-scan does not overwrite; it adds a row. That is
deliberate — a person moving from one company to another is exactly the kind of
thing Leo wants to be able to look up later. When `changed` is non-empty, say so
in your reply: "上次是研發部經理, 現在是協理" is the useful sentence.

## Reporting back after a scan

Short. What you read, and anything you were unsure of:

- Confirm company / name / department / title / the numbers in one block.
- If `uncertain` is non-empty, ask about exactly those fields and nothing else.
- If the person was already on file with different details, lead with the change.

## Drawing the company

```bash
python <skill>/scripts/cards.py chart --company "鴻鼎" --out C:/path/org.png
```

Then send it: `hermes send -t telegram "MEDIA:C:/path/org.png"`, or attach it to
your reply if the run already delivers to Telegram.

**Say what the chart is, every time.** It groups by department and sorts by title
seniority. Business cards carry no reporting lines, so it is *not* a reporting
chart — 王 sitting above 李 means "more senior title", not "李's manager". A tree
that looks like an org chart will be read as one unless you say otherwise.

People with an `uncertain` field are drawn with an orange border and a ⚠ mark, so
the chart shows its own weak spots.

## Looking things up

```bash
python <skill>/scripts/cards.py list --company "鴻鼎"      # newest row per person
python <skill>/scripts/cards.py list --all-history         # every scan ever
python <skill>/scripts/cards.py history --name "陳建宏"     # one person over time
```

The store is SQLite at `%LOCALAPPDATA%\hermes\business-cards\cards.db`. It is
contact data Leo collected in person — do not send it anywhere, and do not include
whole dumps of it in a reply. Answer the question that was asked.
