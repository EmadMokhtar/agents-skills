#!/usr/bin/env python3
"""Make a tailored copy of the base resume (.docx) from an edits file, and render a PDF.

The agent writes the role-specific wording into an edits JSON file. This script copies the
base resume, applies the edits in place (keeping the original styling), and saves the copy.
It never writes content of its own.

Edits JSON: a list of objects, each one of
  {"match": "<start of the paragraph>", "kind": "plain", "text": "<new full text>"}
  {"match": "<start of the paragraph>", "kind": "lb",
   "label": "<bold lead-in, with its colon>", "body": "<rest of the line>"}
"match" is compared with the start of each paragraph's text. Each edit changes one paragraph.

Safety checks (the script refuses and writes nothing):
- an edit that matches no paragraph;
- a number in the new text that does not appear anywhere in the base resume. A new number
  is almost always an invented metric. Ask the user, and add it to the base resume first.

Edits work at the XML level: hyperlinked text and tab stops are kept, so a contact line or a
dated employer line is never doubled. The PDF is rendered by LibreOffice into a temporary
folder and then copied, because LibreOffice can fail silently when it overwrites a PDF in a
synced or mounted folder. The copy is read back, and its page count must match the base.

Usage:
  python3 tailor_resume.py --dir ~/job-search --edits edits.json \\
      --out "resumes/Acme - Staff Engineer.docx" --job-id acme-staff-engineer \\
      [--base base.docx] [--pages 2] [--no-pdf]
The base resume defaults to resume.base_docx in profile.yaml. With --job-id, the role's
`resume` field in jobs.json is set to the new file. Only roles with status 'new' can get a
tailored resume: for an applied role the employer already has the version that was sent.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jobfiles import FolderError, load_tracker, resolve_in, save_tracker, today_iso, write_text
from profile_yaml import ProfileError, get, load

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
MAC_SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"


class TailorError(ValueError):
    """The edits were refused. Nothing was written."""


def need_docx():
    try:
        import docx  # noqa: F401
    except ImportError:
        raise TailorError(
            "python-docx is not installed. Ask the user to install it, for example: "
            "python3 -m pip install python-docx"
        ) from None
    from docx import Document

    return Document


# --- paragraph helpers (XML level) ------------------------------------------------------------
#
# python-docx's paragraph.runs returns only runs that are direct children of the paragraph.
# Word puts hyperlinked text inside <w:hyperlink>, so those runs are invisible to .runs. Edit
# such a paragraph through .runs and the old hyperlinked text stays next to the new text.
# These helpers walk every <w:t> in document order instead, and leave <w:tab> alone.


def paragraphs(doc) -> list:
    """Every paragraph in the body, including paragraphs inside tables."""
    return list(doc.element.body.iter(W + "p"))


def texts(p_el) -> list:
    return p_el.findall(".//" + W + "t")


def para_text(p_el) -> str:
    out = []
    for node in p_el.iter():
        if node.tag == W + "t":
            out.append(node.text or "")
        elif node.tag == W + "tab" and node.getparent().tag == W + "r":
            out.append("\t")
    return "".join(out)


def _run(t_el):
    r = t_el.getparent()
    return r if r is not None and r.tag == W + "r" else None


def _is_bold(t_el) -> bool:
    r = _run(t_el)
    rpr = r.find(W + "rPr") if r is not None else None
    b = rpr.find(W + "b") if rpr is not None else None
    return b is not None and b.get(W + "val") not in ("0", "false")


def _set(t_el, text: str) -> None:
    t_el.text = text
    if text != text.strip():
        t_el.set(XML_SPACE, "preserve")


def _set_bold(t_el, on: bool) -> None:
    from lxml import etree

    r = _run(t_el)
    if r is None:
        return
    rpr = r.find(W + "rPr")
    if rpr is None:
        rpr = etree.Element(W + "rPr")
        r.insert(0, rpr)
    b = rpr.find(W + "b")
    if on and b is None:
        etree.SubElement(rpr, W + "b")
    elif not on and b is not None:
        rpr.remove(b)


def set_plain(p_el, text: str) -> bool:
    """Replace the whole paragraph text, keeping the first run's formatting."""
    ts = texts(p_el)
    if not ts:
        return False
    _set(ts[0], text)
    for t in ts[1:]:
        _set(t, "")
    return True


def set_label_body(p_el, label: str, body: str) -> bool:
    """A bold lead-in and a plain rest, keeping hyperlinks and formatting."""
    ts = texts(p_el)
    if not ts:
        return False
    bold_i = next((i for i, t in enumerate(ts) if _is_bold(t)), None)
    if bold_i is None:
        bold_i = 0
        _set_bold(ts[0], True)
    plain_i = next((i for i in range(bold_i + 1, len(ts)) if not _is_bold(ts[i])), None)
    if plain_i is None:
        if bold_i + 1 < len(ts):
            plain_i = bold_i + 1
            _set_bold(ts[plain_i], False)
        else:
            _set(ts[bold_i], label + body)
            return True
    _set(ts[bold_i], label)
    _set(ts[plain_i], body)
    for i, t in enumerate(ts):
        if i not in (bold_i, plain_i):
            _set(t, "")
    return True


def replace_span(p_el, old: str, new: str) -> bool:
    """Replace one piece of text that may be split over several runs, touching only those runs.

    Word splits text at random points ("Jan 202" + "0 — Present"), so a date is rarely in
    one <w:t>. Tabs are not inside <w:t>, so they are never touched.
    """
    ts = texts(p_el)
    joined = "".join(t.text or "" for t in ts)
    at = joined.find(old)
    if not ts or at == -1:
        return False
    end, pos, first = at + len(old), 0, True
    for t in ts:
        cur = t.text or ""
        lo, hi = pos, pos + len(cur)
        pos = hi
        if hi <= at or lo >= end:
            continue
        before = cur[: max(0, at - lo)]
        after = cur[max(0, end - lo) :] if hi > end else ""
        _set(t, before + (new if first else "") + after)
        first = False
    return True


# --- edits ------------------------------------------------------------------------------------


def _numbers(text: str) -> set[str]:
    return set(NUMBER_RE.findall(text))


def check_edits(edits: list) -> None:
    for n, e in enumerate(edits):
        kind = e.get("kind") if isinstance(e, dict) else None
        ok = kind == "plain" and "text" in e or kind == "lb" and "label" in e and "body" in e
        if not ok or not e.get("match"):
            raise TailorError(
                f"edit {n}: needs match plus kind 'plain' (text) or 'lb' (label, body)"
            )


def new_numbers(edits: list, base_text: str) -> list[str]:
    """Numbers in the edits that do not appear anywhere in the base resume."""
    known = _numbers(base_text)
    known |= {re.sub(r"[.,]", "", k) for k in known}
    found = []
    for e in edits:
        text = e.get("text", "") + e.get("label", "") + e.get("body", "")
        for num in sorted(_numbers(text)):
            if num not in known and re.sub(r"[.,]", "", num) not in known:
                found.append(num)
    return found


def apply_edits(doc, edits: list) -> None:
    """Apply each edit to the one paragraph that starts with its match.

    Raise TailorError, before changing anything, when a match starts no paragraph, starts
    more than one (a short match would edit the wrong line), or two edits hit one paragraph.
    """
    texts_by_p = [(p, para_text(p).strip()) for p in paragraphs(doc)]
    targets, unmatched, ambiguous = [], [], []
    for e in edits:
        hits = [p for p, text in texts_by_p if text and text.startswith(e["match"])]
        if not hits:
            unmatched.append(e["match"])
        elif len(hits) > 1:
            ambiguous.append(e["match"])
        else:
            targets.append(hits[0])
    if unmatched:
        raise TailorError("no paragraph starts with: " + " | ".join(unmatched))
    if ambiguous:
        raise TailorError(
            "these matches start more than one paragraph; use more words: " + " | ".join(ambiguous)
        )
    if len({id(t) for t in targets}) != len(targets):
        raise TailorError("two edits change the same paragraph; merge them into one")
    for p, e in zip(targets, edits):  # noqa: B905 (same length; zip(strict=) needs 3.10)
        if e["kind"] == "plain":
            set_plain(p, e["text"])
        else:
            set_label_body(p, e["label"], e["body"])


def scrub_docx(path: Path, base: Path) -> None:
    """Keep the base file's author and title; clear fields that can carry notes."""
    document = need_docx()
    b = document(str(base)).core_properties
    d = document(str(path))
    c = d.core_properties
    c.author = b.author or ""
    c.last_modified_by = b.last_modified_by or b.author or ""
    c.title = b.title or ""
    c.subject = b.subject or ""
    c.comments = ""
    c.keywords = ""
    c.category = ""
    c.content_status = ""
    d.save(str(path))


# --- PDF --------------------------------------------------------------------------------------


def scrub_pdf(path: Path) -> None:
    """Blank the tool names (Producer, Creator) in a PDF, keeping the byte length the same.

    The same length keeps the byte offsets in the PDF's cross-reference table valid.
    """
    data = bytearray(Path(path).read_bytes())
    for key in (b"/Producer", b"/Creator"):
        i = 0
        while (i := data.find(key, i)) != -1:
            j = i + len(key)
            while j < len(data) and data[j : j + 1] in (b" ", b"\r", b"\n"):
                j += 1
            if data[j : j + 1] == b"(":
                end, escaped = j + 1, False
                while end < len(data):
                    ch = data[end : end + 1]
                    if escaped:
                        escaped = False
                    elif ch == b"\\":
                        escaped = True
                    elif ch == b")":
                        break
                    end += 1
                data[j + 1 : end] = b" " * (end - j - 1)
            elif data[j : j + 1] == b"<":
                end = data.find(b">", j)
                if end != -1:
                    data[j + 1 : end] = b"0" * (end - j - 1)
            i = j
    for tag in (b"pdf:Producer", b"xmp:CreatorTool"):
        start_tag, end_tag = b"<" + tag + b">", b"</" + tag + b">"
        i = 0
        while (i := data.find(start_tag, i)) != -1:
            s = i + len(start_tag)
            e = data.find(end_tag, s)
            if e == -1:
                break
            data[s:e] = b" " * (e - s)
            i = e
    Path(path).write_bytes(bytes(data))


def pdf_pages(path: Path) -> int:
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        r = subprocess.run([pdfinfo, str(path)], capture_output=True, text=True)
        m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
        if m:
            return int(m.group(1))
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", Path(path).read_bytes()))


def pdf_text(path: Path) -> str | None:
    """The PDF's text through pdftotext, or None when pdftotext is not installed."""
    tool = shutil.which("pdftotext")
    if not tool:
        return None
    r = subprocess.run([tool, str(path), "-"], capture_output=True)
    return r.stdout.decode("utf-8", "ignore") if r.returncode == 0 else ""


def find_soffice() -> str | None:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    return MAC_SOFFICE if Path(MAC_SOFFICE).exists() else None


def run_soffice(soffice: str, docx_path: Path, outdir: Path) -> None:
    profile = Path(outdir) / "lo-profile"
    subprocess.run(
        [
            soffice,
            "--headless",
            f"-env:UserInstallation={profile.as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(outdir),
            str(docx_path),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )


def render_pdf(docx_path: Path) -> Path | None:
    """Render docx_path to a PDF beside it. Return the PDF path, or None without LibreOffice.

    Render into a temporary folder, then copy the bytes over the destination and read them
    back. Raises TailorError when LibreOffice produced nothing or the copy did not land.
    """
    soffice = find_soffice()
    if soffice is None:
        return None
    target = docx_path.with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as tmp:
        run_soffice(soffice, docx_path, Path(tmp))
        produced = Path(tmp) / (docx_path.stem + ".pdf")
        if not produced.exists():
            raise TailorError(f"PDF FAILED: LibreOffice produced no PDF for {docx_path.name}")
        scrub_pdf(produced)
        fresh = produced.read_bytes()
        with open(target, "wb") as out:
            out.write(fresh)
    if target.read_bytes() != fresh:
        raise TailorError(f"PDF STALE: {target.name} on disk is not the PDF just rendered")
    for lock in (docx_path, target):
        (lock.parent / f".~lock.{lock.name}#").unlink(missing_ok=True)
    return target


def expected_pages(base: Path, pages: int | None) -> int | None:
    if pages:
        return pages
    base_pdf = base.with_suffix(".pdf")
    if base_pdf.exists():
        return pdf_pages(base_pdf)
    soffice = find_soffice()
    if soffice is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / base.name
        shutil.copy(base, copy)
        run_soffice(soffice, copy, Path(tmp))
        produced = copy.with_suffix(".pdf")
        return pdf_pages(produced) if produced.exists() else None


def check_pdf(pdf: Path, must_contain: list[str], pages: int | None) -> list[str]:
    """Problems with a rendered PDF, as report lines. An empty list means it is good."""
    problems = []
    if pages is not None and pdf_pages(pdf) != pages:
        problems.append(f"PAGE COUNT  {pdf.name}: {pdf_pages(pdf)} pages, the base has {pages}")
    text = pdf_text(pdf)
    if text is None:
        print("note: pdftotext is not installed, so the PDF text was not read back")
        return problems
    flat = " ".join(text.split())
    for line in must_contain:
        for piece in re.split(r"\t+", line):
            piece = " ".join(piece.split())[:60]
            if len(piece) >= 4 and piece not in flat:
                problems.append(f"PDF STALE   {pdf.name}: missing {piece!r}")
                break
    return problems


# --- command line -----------------------------------------------------------------------------


def _in_folder(root: Path, value: str) -> Path:
    """A path the user gave: absolute as it is, otherwise relative to the job search folder."""
    path = Path(os.path.expanduser(value))
    return path if path.is_absolute() else root / path


def _base_from_profile(root: Path) -> Path:
    profile = load(root / "profile.yaml")
    base = get(profile, "resume.base_docx")
    if not base:
        raise TailorError("profile.yaml has no resume.base_docx; pass --base")
    path = Path(os.path.expanduser(base))
    return path if path.is_absolute() else root / path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dir", default=".", help="the job search folder (default: current folder)")
    p.add_argument("--base", help="the base resume .docx (default: resume.base_docx)")
    p.add_argument("--out", required=True, help="the tailored .docx, inside the folder")
    p.add_argument("--edits", required=True, help="the edits JSON file")
    p.add_argument("--pages", type=int, help="expected page count (default: the base's)")
    p.add_argument("--no-pdf", action="store_true", help="write the .docx only")
    p.add_argument("--job-id", help="record the resume on this role in jobs.json")
    args = p.parse_args(argv)
    try:
        document = need_docx()
        root = resolve_in(Path(args.dir), ".")
        out = resolve_in(root, args.out)
        if out.suffix.lower() != ".docx":
            raise TailorError("--out must end in .docx")
        base = _in_folder(root, args.base) if args.base else _base_from_profile(root)
        if not base.is_file():
            raise TailorError(f"base resume not found: {base}")
        if out == base.resolve():
            raise TailorError("--out is the base resume; write the tailored copy to a new file")
        if (root / "jobs.json").exists():
            for other in load_tracker(root)["jobs"]:
                sent = other.get("resume")
                try:
                    sent_path = resolve_in(root, sent) if sent else None
                except FolderError:
                    sent_path = None  # a resume stored outside the folder cannot be --out
                if sent_path == out and other.get("status") != "new":
                    raise TailorError(
                        f"{out.name} is the resume of {other.get('id')} (status "
                        f"{other.get('status')!r}); it is frozen. Choose another file name"
                    )
        edits = json.loads(_in_folder(root, args.edits).read_text(encoding="utf-8"))
        if not isinstance(edits, list):
            raise TailorError("the edits file must hold a JSON list")
        check_edits(edits)
        tracker = role = None
        if args.job_id:
            tracker = load_tracker(root)
            role = next((j for j in tracker["jobs"] if j.get("id") == args.job_id), None)
            if role is None:
                raise TailorError(f"no role with id {args.job_id!r} in jobs.json")
            if role.get("status") != "new":
                raise TailorError(
                    f"{args.job_id} has status {role.get('status')!r}; only 'new' roles get a "
                    "tailored resume. An applied role keeps the resume that was sent"
                )

        base_text = "\n".join(para_text(x) for x in paragraphs(document(str(base))))
        invented = new_numbers(edits, base_text)
        if invented:
            raise TailorError(
                "these numbers are not in the base resume: "
                + ", ".join(invented)
                + ". Remove them, or ask the user to add the fact to the base resume first"
            )
        doc = document(str(base))
        apply_edits(doc, edits)

        out.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out))
        scrub_docx(out, base)
        write_text(out.with_suffix(".edits.json"), json.dumps(edits, indent=2, ensure_ascii=False))
        print(f"applied {len(edits)} edit(s) -> {out.relative_to(root)}")
        if role is not None:
            role["resume"] = out.relative_to(root).as_posix()
            save_tracker(root, tracker, today_iso())
            print(f"recorded the resume on {args.job_id} in jobs.json")

        if args.no_pdf:
            return 0
        pdf = render_pdf(out)
        if pdf is None:
            print("PDF skipped: LibreOffice (soffice) is not installed. The .docx is ready.")
            return 0
        changed = [e.get("text") or e["label"] + e["body"] for e in edits]
        problems = check_pdf(pdf, changed, expected_pages(base, args.pages))
        for problem in problems:
            print(problem)
        print(f"pdf -> {pdf.relative_to(root)}" if not problems else "PDF has problems; see above")
        return 1 if problems else 0
    except (TailorError, FolderError, ProfileError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
