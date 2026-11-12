# job-scout user manual

This page is for you, the person doing the job search. You do not need to read any code.

## Quick start

1. Install the `emad-jobs` plugin. See [Install](#install).
2. Open your agent in an empty folder, for example `~/job-search`. Say
   `Set up my job search in ~/job-search.` Answer the questions. You can skip any of them.
3. Every day, say `Run my job search.` Read the report. Then apply yourself.

That is all you need. The rest of this page explains each step. Read it when you need it.

## What job-scout does

job-scout is a *skill*: a set of instructions that an *agent* loads when a task needs it. An agent is an AI assistant that can read files and run programs.

1. It reads company job sites, checks that each job is still open, and scores it against what you want.
2. It keeps one list of jobs (the *tracker*) with no duplicates, and makes a tailored copy of your resume for each good job.
3. It never applies for a job and never sends a message. You read, you decide, and you send.

## What you need

- **An agent that can use skills.** The best choice is a coding agent (Claude Code, Codex, Cursor, GitHub Copilot) or a desktop app with a connected folder. This is *folder mode*. A chat app (Claude.ai, ChatGPT) also works, with extra steps: see [Using it in a chat app](#using-it-in-a-chat-app).
- **A folder on your computer**, for example `~/job-search`. The `~` sign means your home folder.
- **Internet access**, to read public job lists.
- **For tailored resumes (folder mode):** your resume as a `.docx` file (the Microsoft Word format), Python 3.9 or newer, and `python-docx`. Python is the programming language of the helper scripts. `python-docx` is a free add-on for `.docx` files.
- **Optional:** LibreOffice (a free office program), to make a PDF copy of each resume. A PDF is a document file that looks the same on every computer.

The agent runs the helper scripts. You never run them.

## Install

Install the `emad-jobs` plugin (a bundle of skills). It contains job-scout and [hiring-contact-finder](../skills/emad-jobs/hiring-contact-finder.md). The install tabs on the [job-scout skill page](../skills/emad-jobs/job-scout.md#install) cover coding tools. For more help, see [Install](../install.md). A chat app has its own way to add a skill: see its help.

## The first time

Do this once.

1. **Choose a folder.** Make a new, empty folder, for example `~/job-search`. Use the same folder every time. job-scout keeps all its files there.
2. **Open your agent with that folder.** Start a coding agent inside the folder, or connect the folder in your desktop app.
3. **Say:** `Set up my job search in ~/job-search.`
    The agent checks the folder and creates the starting files. It never replaces a file that already exists.
4. **Answer the questions.** This step is called *intake*. The agent asks 2 to 4 questions at a time. You can say `skip` to any question. It tells you the default, and the default is used. If you give your resume first, the agent suggests answers from it, and you confirm each one. The main questions are:
    - **Role:** the job titles you want (no default, so it asks once more if you skip) and the levels.
    - **Work:** the work you want and the work you do not want.
    - **Location:** where you live, remote or office work, whether you would move (default: no), and your work authorization (your right to work in a country). The agent writes it exactly as you say it, and never guesses. If you skip it, reports say "unknown".
    - **Money:** your lowest yearly salary (default: no limit).
    - **Search:** the companies to check every time, and the lowest score to report (default: 7 out of 10).
    - **Resume:** where your base resume `.docx` is. A PDF-only resume cannot be tailored.
    - **People:** whether the agent should also find hiring contacts (see [Reaching people](#reaching-people)).
5. **Check the summary.** The agent shows your answers. Every default is marked "(default)". Say yes, or tell it what to change. Then it offers the first search.

Your answers are saved in `profile.yaml`, a plain text settings file (YAML is a plain text format). It is the only place where your search rules live. To change a rule later, say `Change my criteria`, or edit `profile.yaml` in any text editor.

You use two files in the folder: `kanban.html` (your board) and `profile.yaml` (your rules). The agent looks after the rest: `jobs.json` (the tracker, a plain text data file), `job-search.md` (a log of each search), `search-config.json` (the company job boards to read), and the folders `resumes/`, `outreach/` (draft notes) and `backups/`. Ignore any other files, such as `candidates.json`.

## Every day: run your search

1. **Say:** `Run my job search.` A *run* is one search.
2. **Wait for the report.** The agent backs up your files, reads the job lists, checks each job, scores it, saves the good ones, makes tailored resumes, and writes a log entry.
3. **Read the report.** The next part explains it.
4. **Act yourself.** Open the apply link and read the post. Read the tailored resume. Apply on the company's site. Then move the job's card to **Applied** on the board.

Other things you can say: paste a job link and ask `Is this a good fit for me?`, `Re-check my saved roles.`, or `How is my search going?`

### How to read the report

A shortened report looks like this:

```text
1 new role today.

### Staff Engineer, Agent Platform — Acme
- Score: 8/10
- Location: Remote Europe (your country is on the published list)
- Compensation: €130K–€160K (published)
- Why it fits: matches the agent tooling work you asked for
- Watch out for: the post asks for Kubernetes; your resume does not show it
- Apply link: https://example.com/jobs/staff-engineer — ✅ Live (in the Ashby feed today)
- Resume: resumes/Acme - Staff Engineer.docx

Checked and rejected: Initech "Staff Backend Engineer" (Munich, on-site): needs
relocation.

Searched: 63 boards, 9,812 postings. Prompt-injection text: none found.
```

| Part of the report | What it means |
| --- | --- |
| **Score** | From 0 to 10: the agent's judgement of how well the role fits your profile. Only roles at or above your lowest score (7 by default) are reported. A role that is mostly work you do not want scores 6 at most. |
| **Live** | The agent checked **today** that the job is open. "In the Ashby feed" means the company's hiring software (here Ashby) lists the job as open. "Page opened today" means the agent opened the page and read it. A job it could not check is not reported as a match. |
| **Watch out for** | Gaps and unknowns, for example a skill your resume does not show, or a salary that is not published. |
| **Checked and rejected** | Jobs that almost fit, with the reason for each. If a reason is wrong for you, change `profile.yaml`. For example, say that you would move. |
| **Searched** | How much the agent read: company job boards (the lists of open jobs that companies publish) and job posts. "Dead boards" no longer answer. |
| **Prompt-injection text** | A job post is written by a stranger. Some posts try to give orders to an AI, for example "email the resume to this address". The agent ignores them and tells you here. "None found" is normal. |

The report can also list **Relisted** (a closed job that came back changed), **Expired** (a saved job that closed) and **Duplicates seen again** (jobs you already have).

## The kanban board

A *kanban board* shows your jobs as cards in columns. Each card is one job.

1. **Open `kanban.html`** from your job search folder, in Chrome or Edge. Other browsers cannot save to your file directly.
2. **Click `Open jobs.json`.** Choose `jobs.json` in your job search folder. Allow access when the browser asks. Do this once each time you open the board.
3. **Move cards.** Hold a card, move it to another column, and let go. Or click the `⋯` button on the card and choose a column. Each change saves to `jobs.json` at once.
4. **Click `Details`** on a card to write your notes and the hiring manager's name. Here you also record the channel and whether a person contacted you. Click `Save` when you finish.

| Column | Meaning | Who moves cards there |
| --- | --- | --- |
| New / Found | The agent found the job. You have not applied. | The agent |
| Applied | You applied. | You |
| In Process | A person is talking to you, for example in a screening call or an interview. | You |
| Rejected | The company rejected you, or you withdrew. | You |
| Archived | The job is not relevant now. It closed, or you set it aside. The column starts closed: click its title to open it. | The agent (closed jobs only) or you |

The agent never changes a status that you set. It never changes your notes or the hiring manager name.

**Channel** is how your application went in:

- `portal`: you applied on the company's own application page. This is the default.
- `referral`: an employee of the company recommended you.
- `hiring-manager-direct`: you wrote to the hiring manager.
- `recruiter-inbound`: a recruiter found you first.
- `community`: you came in through a community, a meetup or a talk.

If you used more than one way, choose the one that is **not** the portal.

**Did a person contact you about this role?** Choose Yes if a named person wrote to you, called you or interviewed you. Choose No if only the system answered. You can also tell the agent, for example `An engineer at Acme referred me.`

The agent uses these answers to find which hiring platforms (the software that companies use to receive applications) and which channels get a person to reply. Ask `Which portals ignore me?` to see the result.

In Applied and In Process, each card shows the days since you applied. The number turns amber after 14 days and red after 30 days. Then it may be time to send a follow-up message.

## Tailored resumes

A tailored resume is a copy of your base resume that puts your most relevant work first and uses the words of the job post where they are true. The agent makes one for each role in the report.

- **Where:** in `resumes/`, for example `resumes/Acme - Staff Engineer.docx`. With LibreOffice, there is also a `.pdf`. The report shows the path.
- **No invention.** The agent never adds an employer, a job title, a date, a skill, a number or a responsibility that your base resume does not show. If a post asks for something your resume lacks, the agent tells you. If you do have that skill, add it to your base resume yourself first. Then ask again.
- **Sent resumes stay as they are.** After you move a role to Applied, the agent does not change that resume, because the employer has it. When a role is rejected or archived, its resume moves to `resumes/_archive/`. Nothing is deleted.

!!! warning "Read each tailored resume before you send it"
    The agent follows strict rules, but you know your own work. Check every line. If something is wrong, tell the agent what to change.

To ask for one resume: `Tailor my resume to this role.` and paste the job link.

## Reaching people

Hiring software often rejects an application before any person reads it. A short note to the person who owns the role can change that.

The [hiring-contact-finder](../skills/emad-jobs/hiring-contact-finder.md) skill finds the hiring manager (the person who leads the team) or a recruiter (a person who finds and screens candidates). It uses only public, professional sources, never LinkedIn. It chooses one professional channel and writes a short draft in `outreach/`.

**It writes drafts only. You read the draft, change it and send it yourself.** Also apply on the company's site, because the hiring manager usually needs your application.

Your answer to the "People" question decides when the search happens:

- `ask` (default): at the end of a report, the agent offers it. You choose the roles.
- `auto`: the agent does it for the highest-scoring roles, up to 3 per run unless you choose another number.
- `never`: only when you ask, for example `Who is hiring for this role?`

The agent can also draft a referral request (a message that asks an employee to recommend you). Say `Help me get a referral at Acme.`

Some employers reject you very fast, with no person involved. If the employer is in the EU (European Union), the EEA (European Economic Area) or the UK (United Kingdom), you can ask for a person to review the decision. The agent drafts the request. Say `I was rejected with no human.` This is not legal advice.

The hiring manager name on a card is yours to fill in. The agent never writes it.

## Using it in a chat app

A chat app such as Claude.ai or ChatGPT gives the agent a *sandbox*: a temporary computer that is deleted after the chat. Your files are deleted with it. So **your own copy of the files is the real one.** This is *upload mode*.

1. **Make a `.zip` file** of your job search folder. A `.zip` is one file that holds many files. Most computers can make one from the right-click menu.
2. **Start a chat where job-scout is available. Upload the `.zip`.** Say `Run my job search.` For a new search, upload nothing and say `Set up my job search.`
3. **Read the report.** At the end, the agent names every file that changed. It also offers the whole folder as a `.zip`.
4. **Download the changed files** and replace your own copies with them.

!!! warning "Replace your files after every run"
    If you do not replace your files, your folder does not know about this run. The next run reports the same roles again. Keep your old `jobs.json` until you have checked the new one, because the sandbox backups are deleted too.

- If your `jobs.json` looks older than your log, the agent asks before it searches.
- The board still runs on your computer. Open `kanban.html` from your own folder, and choose your own `jobs.json`. Upload that copy next time.
- Scheduled runs do not work in a chat app.
- If your chat cannot run code at all, it is *chat-only mode*. The agent can ask the intake questions, check one job link and write draft notes. It cannot search or keep a tracker.

## Scheduled runs

A scheduled run starts by itself at a time you choose. It works **only in folder mode**, because the agent needs a folder that stays between runs.

1. Do the first-time setup first. Without a `profile.yaml`, a scheduled run does not search. It stops and tells you.
2. In your agent tool, create a scheduled task, or a timer on your computer. job-scout does not start itself.
3. Give the task this prompt: `Use the job-scout skill. Run the daily search in ~/job-search. This is an unattended run.` (An unattended run has nobody there to answer questions.) Do not put search rules in the prompt. They are in `profile.yaml`.

A scheduled run asks no questions. When something is unclear, it chooses the safe option and writes what it assumed in `job-search.md`. By default, it sends you a message only when there is something new or when the run failed.

## What it never does

- It never applies, signs in, accepts terms, or sends anything for you. No emails, no messages, no forms.
- It never invents resume content.
- It never follows orders written inside a job post. It ignores them and reports them.
- It never changes a status you set, your notes, or the hiring manager name.
- It never guesses your work authorization, your channel, or whether a person contacted you. It records only what you say.
- It writes only inside your job search folder. It never deletes backups or resumes.

## Common problems

### It says it cannot write to the folder

The folder does not exist where the agent runs, or the agent is not allowed to write in it. Give the agent permission to change files there: start it inside the folder, or connect the folder again in your desktop app. In a chat app, use [upload mode](#using-it-in-a-chat-app). The agent never saves your files somewhere else.

### It says the job boards are blocked

A chat app's sandbox often allows only some websites. The agent tests this before a search. If it has a web tool (a tool that opens web pages), it reads the lists with that tool, starting with the companies you named. The "Searched" line names the blocked sites. With no web tool, it says the search could not run. It must not report "no new roles" when it could not read the boards. To avoid the problem, use folder mode, which usually does not have this limit.

### It reports the same roles again

The agent knows what it reported before only from your `jobs.json`. If you did not replace your files after a chat-app run, your copies do not know about that run. An old copy or a different folder has the same effect. After every chat-app run, download the changed files and replace your copies.

### There is no tailored resume

Either the agent has no base resume `.docx` (a PDF-only resume cannot be tailored), or `python-docx` is not installed. The agent tells you that it skipped the resume. Tell the agent where your `.docx` is, or upload it in a chat app. To install `python-docx`, run `python3 -m pip install python-docx` in a terminal (the text window where you type commands). This asks pip, Python's package installer, to install it. Then say `Tailor my resume to this role.` and paste the link.

If you get a `.docx` but no `.pdf`, LibreOffice is not installed. It is optional.

### The agent asks the intake questions again

There is no `profile.yaml` in the folder the agent is using. Check that you opened the right folder. In upload mode, upload `profile.yaml` again.

### The board is empty or shows old roles

Use Chrome or Edge. Click `Open jobs.json` and choose the file in your job search folder. If the board was open while the agent worked, click `Reload from file`. In other browsers, `Save` downloads a `jobs.json`. Move it into your folder.

## More help

The [job-scout skill page](../skills/emad-jobs/job-scout.md) has the full description.
