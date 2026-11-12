# Reaching people

A portal application is often rejected before a person reads it. Reaching a person changes
that. This file covers three ways to do it: finding the hiring manager or recruiter, asking
for a referral, and asking for a human review after an automated rejection.

The rule from SKILL.md holds for all of them: **prepare, never send.** The person reads every
draft, changes it, and sends it themselves.

## Finding the hiring manager or recruiter

Use the `hiring-contact-finder` skill. It ships in the same plugin (`emad-jobs`). It finds the
people behind a posting from public, professional sources (not LinkedIn), picks the best
professional channel, and drafts a short note. If it is not available to you, say so, and
write "contact search skipped: hiring-contact-finder is not installed" in the report.

### When

`outreach.find_contacts` in `profile.yaml` decides:

| Value | Interactive run | Unattended run |
| --- | --- | --- |
| `ask` (default) | End the report by offering it for the reported roles, by name. Run it only for the roles the person picks. | Do not search. Add one line: "Contact search: available for <roles>. Ask me to run it." |
| `auto` | Run it for the reported roles, highest score first, at most `outreach.max_per_run` (default 3). | The same. |
| `never` | Only when the person asks. | Never. |

Whatever the setting, also offer it when:

- a reported role's vendor is **flagged** in the vendor report ([channels.md](channels.md));
- the person asks "who is hiring for this?" or "who should I write to?".

Run it only for roles verified live today. A contact search for a closed role wastes the
person's one chance with that contact.

### What to give it

- The posting URL.
- The person's background: the base resume (`resume.base_docx`), or `resume.lead_evidence`.
- `location.home_base` and `location.work_authorization`, exactly as the profile states
  them. Empty means "unknown": pass it as unknown, never as a guess.

Give it nothing more personal than that.

### What to keep

1. Save its report and drafts in `outreach/<company> - <role>.md` inside the job search
   folder.
2. Run `tracker.py record --id <id> --outreach "outreach/<company> - <role>.md"`.
3. In the run report, add one line to the role: `- Contact: <name>, <role> via <channel> —
   outreach/<file>.md`, or `- Contact: no one found yet (outreach/<file>.md)`.

Never write `hiring_manager`: it is the person's field. They copy the name there once they
decide to write to that person.

hiring-contact-finder's own privacy rules apply in full: public professional information
only, professional channels only, and a guessed email address is always marked unverified.

## Asking for a referral

A referral changes the channel from `portal` to `referral`. It is the strongest answer to a
flagged vendor.

- **When:** before applying, or right after applying through the portal. Especially at a
  company whose vendor is flagged.
- **Who:** one engineer on or near the team, not a recruiter. Find them through the
  company's engineering blog, conference talks, open-source commits, or a shared
  connection. One person, not five.
- **The first paragraph is the whole message.** It names one specific thing the engineer
  made (a blog post, a talk, a library, a commit) and one concrete sentence on what the
  person took from it. If the paragraph could go to anyone at the company, it will be
  ignored: rewrite it or do not send it.
- **One paragraph of evidence, with numbers.** Take the numbers from the base resume only.
  The anti-invention rule in [resume-tailoring.md](resume-tailoring.md) applies to messages
  too.
- **Offer the smaller ask.** A referral puts the engineer's name on the person. "Or a
  20-minute call first" lets them say yes without that risk.
- Keep it under 200 words.
- **Never attach the resume unasked.** If they agree, the person sends the tailored PDF from
  `resumes/` and the exact job link.
- **One follow-up at most,** about a week later, one line. Then stop.

```text
Subject: Question about [team] at [company]

Hi [name],

I came across [the specific thing they made] and [one concrete sentence about what you
took from it: a design choice, a trade-off, something you disagreed with]. That is what got
me reading about [team or product].

I am a [current title] working on [area]. The closest thing I have built to [the company's
problem] is [one result from your resume, with its number].

[Company] has [role] open, and it lines up with that work. I would rather come in through
someone who knows the team than through the portal. Would you be open to a referral, or to
a 20-minute call first?

[your name]
```

When the engineer agrees, run `tracker.py record --id <id> --channel referral`.

## After a fast rejection with no human: ask for a human review

Some rejections come from software alone: they arrive within a few days of applying, from a
no-reply address, with no interview and no named person. When the employer processes the
person's data in the EU or EEA, the GDPR (General Data Protection Regulation, the EU data
protection law) applies. A UK employer falls under the UK GDPR, which has the same rules.

- **Article 22** gives a right not to be subject to a decision based only on automated
  processing that significantly affects the person. Where such a decision is allowed, the
  person can ask for a human to look at it (Article 22(3)).
- **Article 15(1)(h)** gives a right to know whether automated decision-making was used, and
  to get meaningful information about the logic behind it.
- The company must answer within one month (Article 12(3)). It can extend this by two more
  months if it says why.

Offer this as an option, never as a duty. Say that it is not legal advice. Draft it; the
person sends it.

- **Send to:** the recruiting or privacy contact on the rejection email. If there is only a
  no-reply address, the data protection officer (DPO) contact in the company's privacy
  policy.
- **Tone:** short and neutral. It is a request for information, not a complaint and not an
  appeal. If the answer is "a person reviewed it", the person still learns something about
  that company's process.
- A complaint to the national data protection authority is the person's decision. Do not
  suggest it as a next step unless they ask.

```text
Subject: Request for information: automated decision-making, [role] application

Hello,

I applied for [role] on [date] and received a rejection on [date]. Could you confirm
whether this decision was made using automated processing? If so, under Article 22 of the
GDPR I request a human review of the decision, and under Article 15 information about the
main factors behind it.

Thank you,
[your name]
```

If a named person answers, run `tracker.py record --id <id> --human-contact yes`.
