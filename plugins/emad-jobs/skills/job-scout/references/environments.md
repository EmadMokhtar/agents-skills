# Where you are running

The skill keeps its state in files: the profile, the tracker, the log and the resumes.
Those files must still be there at the next run. If they are not, the next run starts from
nothing and reports the same roles again. Whether they stay depends on where the agent
runs, so check it before the first command of a session.

## The check

1. Find out which folder is the job search folder. If you do not know, ask.
2. Run `python3 <skill dir>/scripts/check_folder.py --dir <folder>`. Add `--network`
   before a search run. It reports whether the folder exists and can be written to, which
   job search files are there, which tools the scripts can use, and (with `--network`)
   whether the job board APIs answer from here.
3. Pick the mode from the table below.

If you cannot run commands at all, you are in chat-only mode.

## Pick the mode

| What you see | Mode |
| --- | --- |
| You run on the person's own computer: a coding agent (Claude Code, Codex, Cursor, GitHub Copilot and similar), or a desktop app with a folder the person connected. The check passes. | **Folder mode** |
| You run code in a sandbox, a temporary computer that a chat app gives you (Claude.ai, ChatGPT, a desktop chat with no connected folder). The person's folder does not exist here, or their files reached you as uploads. | **Upload mode** |
| You cannot run code. | **Chat-only mode** |

**If the person's files reached you as uploads or attachments, use upload mode**, even when
`check_folder.py` says the folder can be written to. A sandbox can be written to, and it is
still removed later.

When you are not sure, ask: "Is `<folder>` a folder on your computer that I can open, or
will you upload the files?"

## Folder mode

SKILL.md works as written. What the check tells you:

- `MISSING profile.yaml`: run intake ([intake.md](intake.md)).
- A new search: `check_folder.py --dir <folder> --init` creates the folder, its subfolders
  and the files from the templates. It never overwrites a file and never creates
  `profile.yaml`: intake writes it.
- `FAIL can write here`: the folder is read-only for you. Ask the person to give you write
  access, or use upload mode. Never write the files somewhere else instead: the person
  would not find them.
- `BLOCKED` for a job board host: see "When the job board APIs are blocked" below.

## Upload mode

The sandbox is removed after the conversation, with every file in it. So the person's own
copy is the real one, and every turn that changes a file ends by handing it back.

1. **Ask for the files.** For a run: `profile.yaml`, `jobs.json`, `search-config.json` and
   `job-search.md`, plus the base resume (.docx) if they want tailored resumes. The easiest
   way is the whole job search folder as one .zip file. For a new search, ask for nothing:
   create the folder with `check_folder.py --init`, then run intake.
2. **Make one working folder** in the sandbox and put the files there. Unpack a .zip with
   `python3 -m zipfile -e <file>.zip <folder>`. Run
   `check_folder.py --dir <folder> --network`.
3. **Check the copy is current.** If `meta.last_updated` in `jobs.json` is older than the
   last entry in `job-search.md`, the person may have uploaded an old tracker. Ask before
   you run.
4. **Run as usual**, with the scripts on the working folder.
5. **Hand back every changed file**, by name, at the end of the turn. Do this also when a
   run fails halfway, so the person's files match the report. Usually: `jobs.json`,
   `job-search.md`, `search-config.json`, `vendor-report.md`, the new files in `resumes/`
   and `outreach/`, and `profile.yaml` after intake or a change. Offer the whole folder as
   one .zip: `python3 -m zipfile -c job-search.zip <folder>/`.
6. **Say what the person must do:** "Download these files and replace your copies. Until
   you do, your folder does not know about today's run, and the next run will report the
   same roles again."

Never write "saved", "updated your tracker" or "added to your folder" in upload mode. Write
"here is the updated tracker".

Also in upload mode:

- **Backups.** `backups/` in the sandbox is removed too. Tell the person to keep their old
  `jobs.json` until they have checked the new one.
- **The kanban board** runs on the person's computer. They open `kanban.html` in Chrome or
  Edge and pick their own `jobs.json`. What they change there is in their copy, which they
  upload next time.
- **Unattended runs do not work.** A scheduled chat task has no folder to read. Say so, and
  suggest folder mode: a coding agent or a desktop app with a connected folder.

## When the job board APIs are blocked

A sandbox often lets only some hosts through. When `check_folder.py --network` shows a host
as `BLOCKED`, `poll_boards.py` cannot read the boards on that host.

- Never report "no new roles" when the boards were not read. That would be false.
- If you have a web fetch or browsing tool, open the same API URLs with it
  ([sources.md](sources.md)): the `search.priority_companies` first, then as many registry
  boards as is reasonable. Write each posting you find to `candidates.json` as a list of
  objects with `source` (`ashby`, `greenhouse`, `lever`, or the aggregator), `token`,
  `company`, `title`, `location`, `url`, `published` and `lead` (`true` for an aggregator
  result). Then continue from the dedup step.
- In the report, under **Searched**, name the blocked hosts and the boards you read another
  way.
- With no web tool either, say that the search could not run, and stop. A job link the
  person pastes can still be checked if you can open it.

## Chat-only mode

Without code you cannot run the scripts, and the scripts are what keep the tracker safe
(the ownership rules, the dedup, the backups). Do not edit `jobs.json` by hand in the chat.
You can still:

- run intake as a conversation, and give `profile.yaml` as text for the person to save;
- check one job link against their criteria, if you can open web pages;
- draft referral requests and human review requests ([outreach.md](outreach.md)).

Say that search runs and the tracker need an agent that can run code, and suggest folder
mode.
