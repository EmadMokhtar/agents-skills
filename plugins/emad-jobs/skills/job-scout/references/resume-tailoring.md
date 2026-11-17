# Resume tailoring

Tailoring makes a copy of the person's base resume that leads with the evidence that
matters for one role. It changes **emphasis and wording**, never facts.

## The anti-invention rule

Every claim in a tailored resume must already be true in the base resume, or stated by the
person in this conversation. You may reorder, shorten, rename to the posting's words, and
choose what to lead with. You may not add:

- an employer, a title, a date, a degree or a certification;
- a skill, tool or language the base resume does not show;
- a number: a metric, a team size, years of experience, a percentage;
- a responsibility the person did not have ("led" when the resume says "worked on").

| Allowed | Not allowed |
| --- | --- |
| Base: "Built Kafka pipelines processing 2M events/hour." Tailored: "Built event pipelines on Kafka that process 2 million events per hour." | Tailored: "Led a team of 6 building Kafka pipelines processing 2M events/hour." (team and "led" are invented) |
| Base lists Go, Python, PostgreSQL. Tailored skills line leads with Go for a Go role. | Adding Kubernetes because the posting asks for it. |
| Moving the agent-tooling project to the top of the summary. | "5+ years of LLM experience" when the resume shows 3. |

When the posting asks for something the resume does not show, **do not add it**. Tell the
person: "The role asks for Kubernetes. Your resume does not mention it. If you have used it,
tell me how, and add it to your base resume first; I will not add it on my own." Put the gap
in the role's watch-outs.

`tailor_resume.py` also refuses any number that does not appear in the base resume. Do not
work around it: ask the person.

## Workflow

1. Read the base resume (`resume.base_docx`) and the posting.
2. Choose 3 to 6 edits, only in `resume.editable_sections` (default: summary, skills, key
   bullets). Lead with `resume.lead_evidence` where it fits the role.
3. Write the edits file (below) into the folder, for example `resumes/acme.edits.json`.
4. Run:

   ```bash
   python3 <skill dir>/scripts/tailor_resume.py --dir <folder> \
     --edits resumes/acme.edits.json \
     --out "resumes/Acme - Staff Engineer.docx" --job-id acme-staff-engineer
   ```

   The file name comes from `resume.file_name`. `--job-id` records the path in `jobs.json`.
5. Read what it prints. Fix every refusal: an unmatched edit (fix the `match` text), a new
   number (remove it), a page count that differs from the base (shorten the text).
6. Tell the person the file names and which parts changed.

## Edits JSON

```json
[
  {"match": "Backend engineer with", "kind": "plain",
   "text": "Backend engineer with 9 years of Go and Python, building agent tooling."},
  {"match": "Languages:", "kind": "lb", "label": "Languages: ", "body": "Go, Python, SQL"}
]
```

- `match` is the start of the paragraph's text. Use enough words to be unique.
- `plain` replaces the whole paragraph (a summary, a plain bullet).
- `lb` is a line with a bold lead-in: `label` is the bold part with its colon, `body` the
  rest. Use it for skills lines and bold-label bullets.
- Each edit changes exactly one paragraph. An edit whose `match` starts no paragraph, or
  more than one (for example "Led the"), stops the script, and nothing is written. Add
  words until the match is unique.
- Relative `--edits` and `--base` paths are read from the job search folder. The script
  refuses to write over the base resume, or over the resume of a role that is not `new`.

The script saves the edits next to the resume (`<name>.edits.json`), so the copy can be
rebuilt on a new base later.

## Lessons the script already handles

- **Edit at the XML level.** python-docx's `paragraph.runs` skips text inside hyperlinks.
  Editing through it leaves the old hyperlinked text next to the new text: a contact line or
  a project link line ends up doubled. The script edits every `<w:t>` element in order and
  keeps `<w:tab>` elements, so right-aligned dates survive.
- **PDF through a temporary folder.** LibreOffice can fail **silently** when it overwrites a
  PDF in a synced or mounted folder: it exits 0 and leaves the old PDF. The script renders
  into a temporary folder, copies the bytes over, reads them back, and checks the text with
  `pdftotext` when it is installed.
- **Page count.** The tailored PDF must have the same page count as the base (or
  `resume.page_count`). A longer resume means the edits were too long.
- **Metadata.** The copy keeps the base file's author and title. Comments, keywords and
  category are cleared, because they can hold notes about the target role. The PDF's
  Producer and Creator fields (the tool names) are blanked.

## Frozen resumes and housekeeping

- A resume for an **applied** or **in-process** role is frozen: the employer has that
  version. Never tailor it again, and never overwrite it. `--job-id` refuses roles that are
  not `new`.
- `sync_resumes.py` (preview first, then `--apply`) archives resumes of rejected and
  archived roles into `resumes/_archive/` (never deletes or overwrites; a name already in
  the archive gets a `-2` suffix), and copies **corrected dates only** from the base into
  copies for `new` roles. A line changes only when its words, without the dates, are the
  same as one base line: employer lines, education, certifications. It never touches
  summaries, skills or bullets, even a bullet that contains a date.
- When the base resume changes **shape** (sections moved, paragraphs added), resync cannot
  help. Re-run `tailor_resume.py` for each live role with its saved `.edits.json` against
  the new base, and fix any edit that no longer matches.
