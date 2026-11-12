"""Tests for the job-scout resume scripts: XML-level edits, the anti-invention guard, PDF checks,
and the archive + resync housekeeping. LibreOffice is never started: rendering is replaced."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from job_scout import job, load, read_jobs, write_jobs

tailor = load("tailor_resume")
sync = load("sync_resumes")

NOT_ROOT = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root can write to read-only files"
)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def add_hyperlink(paragraph, text: str) -> None:
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), "rId99")
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    link.append(run)
    paragraph._p.append(link)


def make_resume(path: Path, date: str = "Jan 2020") -> Path:
    doc = Document()
    doc.core_properties.author = "Alex Example"
    doc.core_properties.comments = "draft for Acme"
    doc.core_properties.keywords = "acme"
    doc.add_paragraph("Alex Example")
    contact = doc.add_paragraph("alex@example.com | ")
    add_hyperlink(contact, "github.com/alex-example")
    doc.add_paragraph("Backend engineer with 9 years of Go and Python.")
    skills = doc.add_paragraph()
    skills.add_run("Languages: ").bold = True
    skills.add_run("Go, Python, SQL")
    employer = doc.add_paragraph()
    employer.add_run("Acme, Lisbon")
    employer.add_run().add_tab()
    employer.add_run(date[:-1])
    employer.add_run(date[-1] + " — Present")
    doc.add_paragraph("Built a billing pipeline that handles 2 million events per day.")
    doc.save(path)
    return path


def texts(path: Path) -> list[str]:
    doc = Document(path)
    return [tailor.para_text(p) for p in doc.element.body.iter(W + "p")]


def write_edits(folder: Path, edits: list[dict]) -> Path:
    path = folder / "edits.json"
    path.write_text(json.dumps(edits), encoding="utf-8")
    return path


def tailor_run(folder: Path, edits: list[dict], *extra: str) -> int:
    make_resume(folder / "base.docx")
    return tailor.main(
        [
            "--dir",
            str(folder),
            "--base",
            str(folder / "base.docx"),
            "--out",
            "resumes/Acme - Staff Engineer.docx",
            "--edits",
            str(write_edits(folder, edits)),
            *extra,
        ]
    )


OUT = Path("resumes/Acme - Staff Engineer.docx")


# --- tailor_resume --------------------------------------------------------------------------


def test_a_plain_edit_replaces_hyperlinked_text_instead_of_doubling_it(tmp_path):
    edits = [{"match": "alex@example.com", "kind": "plain", "text": "alex@example.com"}]
    assert tailor_run(tmp_path, edits, "--no-pdf") == 0
    assert texts(tmp_path / OUT)[1] == "alex@example.com"


def test_a_label_edit_keeps_the_bold_lead_in(tmp_path):
    edits = [{"match": "Languages:", "kind": "lb", "label": "Languages: ", "body": "Python, Go"}]
    assert tailor_run(tmp_path, edits, "--no-pdf") == 0
    doc = Document(tmp_path / OUT)
    runs = [r for r in doc.paragraphs[3].runs if r.text]
    assert [(r.text, bool(r.bold)) for r in runs] == [("Languages: ", True), ("Python, Go", False)]


def test_an_unmatched_edit_writes_nothing(tmp_path, capsys):
    edits = [{"match": "No such paragraph", "kind": "plain", "text": "x"}]
    assert tailor_run(tmp_path, edits, "--no-pdf") == 1
    assert not (tmp_path / OUT).exists()
    assert "No such paragraph" in capsys.readouterr().err


def test_a_number_that_is_not_in_the_base_resume_is_refused(tmp_path, capsys):
    edits = [
        {
            "match": "Built a billing pipeline",
            "kind": "plain",
            "text": "Built a billing pipeline that handles 5 million events per day.",
        }
    ]
    assert tailor_run(tmp_path, edits, "--no-pdf") == 1
    assert not (tmp_path / OUT).exists()
    assert "5" in capsys.readouterr().err


def test_numbers_from_the_base_resume_are_allowed(tmp_path):
    edits = [
        {
            "match": "Built a billing pipeline",
            "kind": "plain",
            "text": "Handled 2 million billing events per day in Go.",
        }
    ]
    assert tailor_run(tmp_path, edits, "--no-pdf") == 0
    assert texts(tmp_path / OUT)[5] == "Handled 2 million billing events per day in Go."


def test_the_output_must_be_inside_the_folder(tmp_path):
    make_resume(tmp_path / "base.docx")
    edits = write_edits(tmp_path, [])
    code = tailor.main(
        [
            "--dir",
            str(tmp_path / "sub"),
            "--base",
            str(tmp_path / "base.docx"),
            "--out",
            str(tmp_path / "out.docx"),
            "--edits",
            str(edits),
            "--no-pdf",
        ]
    )
    assert code == 1
    assert not (tmp_path / "out.docx").exists()


def test_metadata_is_scrubbed_and_the_edits_are_kept_for_a_rebuild(tmp_path):
    edits = [{"match": "Backend engineer", "kind": "plain", "text": "Go and Python engineer."}]
    assert tailor_run(tmp_path, edits, "--no-pdf") == 0
    props = Document(tmp_path / OUT).core_properties
    assert props.author == "Alex Example"
    assert props.comments == "" and props.keywords == ""
    saved = json.loads((tmp_path / OUT).with_suffix(".edits.json").read_text())
    assert saved == edits


def fake_pdf(pages: int, producer: bytes = b"(LibreOffice 25.2)") -> bytes:
    body = b"".join(b"%d 0 obj << /Type /Page >> endobj\n" % n for n in range(pages))
    return b"%PDF-1.7\n" + body + b"<< /Type /Pages >>\n<< /Producer " + producer + b" >>\n"


def test_scrub_pdf_blanks_the_producer_and_keeps_the_length(tmp_path):
    pdf = tmp_path / "a.pdf"
    data = fake_pdf(2) + b"<pdf:Producer>LibreOffice</pdf:Producer>"
    pdf.write_bytes(data)
    tailor.scrub_pdf(pdf)
    after = pdf.read_bytes()
    assert len(after) == len(data)
    assert b"LibreOffice" not in after


def test_pdf_pages_counts_page_objects_only(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(fake_pdf(3))
    assert tailor.pdf_pages(pdf) == 3


@pytest.fixture
def fake_soffice(monkeypatch):
    """Pretend LibreOffice is installed and renders a PDF with the given number of pages."""
    state = {"pages": 2, "calls": 0}

    def run(soffice, docx_path, outdir):
        state["calls"] += 1
        (Path(outdir) / (Path(docx_path).stem + ".pdf")).write_bytes(fake_pdf(state["pages"]))

    monkeypatch.setattr(tailor, "find_soffice", lambda: "soffice")
    monkeypatch.setattr(tailor, "run_soffice", run)
    monkeypatch.setattr(tailor, "pdf_text", lambda path: None)
    return state


def test_the_pdf_is_rendered_in_a_temp_folder_then_copied(tmp_path, fake_soffice):
    edits = [{"match": "Backend engineer", "kind": "plain", "text": "Go and Python engineer."}]
    assert tailor_run(tmp_path, edits, "--pages", "2") == 0
    pdf = (tmp_path / OUT).with_suffix(".pdf")
    assert tailor.pdf_pages(pdf) == 2
    assert b"LibreOffice" not in pdf.read_bytes()


def test_a_page_count_that_differs_from_the_base_fails(tmp_path, fake_soffice, capsys):
    fake_soffice["pages"] = 3
    edits = [{"match": "Backend engineer", "kind": "plain", "text": "Go and Python engineer."}]
    assert tailor_run(tmp_path, edits, "--pages", "2") == 1
    assert "PAGE COUNT" in capsys.readouterr().out


def test_without_libreoffice_the_docx_is_still_written(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tailor, "find_soffice", lambda: None)
    edits = [{"match": "Backend engineer", "kind": "plain", "text": "Go and Python engineer."}]
    assert tailor_run(tmp_path, edits) == 0
    assert (tmp_path / OUT).exists()
    assert "LibreOffice" in capsys.readouterr().out


# --- sync_resumes ---------------------------------------------------------------------------


def housekeeping_folder(tmp_path: Path, statuses: dict[str, str]) -> Path:
    """A job search folder with a corrected base resume and one tailored copy per role."""
    make_resume(tmp_path / "base.docx", date="Feb 2020")
    (tmp_path / "profile.yaml").write_text("resume:\n  base_docx: base.docx\n", encoding="utf-8")
    jobs = []
    for name, status in statuses.items():
        resume = tmp_path / "resumes" / f"{name}.docx"
        resume.parent.mkdir(exist_ok=True)
        make_resume(resume, date="Jan 2020")
        doc = Document(resume)
        doc.paragraphs[2].runs[0].text = f"Tailored summary for {name}."
        doc.save(resume)
        resume.with_suffix(".pdf").write_bytes(fake_pdf(2))
        jobs.append(job(id=name, status=status, resume=f"resumes/{name}.docx"))
    write_jobs(tmp_path, jobs)
    return tmp_path


def test_preview_changes_nothing(tmp_path, capsys):
    folder = housekeeping_folder(tmp_path, {"gone": "rejected", "live": "new"})
    before = (folder / "jobs.json").read_text()
    assert sync.main(["--dir", str(folder), "--no-pdf"]) == 0
    assert (folder / "resumes" / "gone.docx").exists()
    assert "Jan 2020" in texts(folder / "resumes" / "live.docx")[4]
    assert (folder / "jobs.json").read_text() == before
    out = capsys.readouterr().out
    assert "Would move 1" in out and "Would resync 1" in out


def test_apply_archives_dead_roles_and_repoints_the_tracker(tmp_path):
    folder = housekeeping_folder(tmp_path, {"gone": "rejected"})
    assert sync.main(["--dir", str(folder), "--apply", "--no-pdf"]) == 0
    assert not (folder / "resumes" / "gone.docx").exists()
    assert (folder / "resumes" / "_archive" / "gone.docx").exists()
    assert (folder / "resumes" / "_archive" / "gone.pdf").exists()
    assert read_jobs(folder)[0]["resume"] == "resumes/_archive/gone.docx"
    assert list((folder / "backups").glob("jobs.backup-*.json"))


def test_apply_resyncs_dates_and_keeps_tailoring_and_tabs(tmp_path):
    folder = housekeeping_folder(tmp_path, {"live": "new"})
    assert sync.main(["--dir", str(folder), "--apply", "--no-pdf"]) == 0
    lines = texts(folder / "resumes" / "live.docx")
    assert lines[4] == "Acme, Lisbon\tFeb 2020 — Present"
    assert lines[2] == "Tailored summary for live."
    employer = list(Document(folder / "resumes" / "live.docx").element.body.iter(W + "p"))[4]
    assert len(employer.findall(".//" + W + "tab")) == 1


def test_resumes_for_applied_roles_are_frozen(tmp_path, capsys):
    folder = housekeeping_folder(tmp_path, {"sent": "applied"})
    assert sync.main(["--dir", str(folder), "--apply", "--no-pdf"]) == 0
    assert "Jan 2020" in texts(folder / "resumes" / "sent.docx")[4]
    assert "ALREADY APPLIED" in capsys.readouterr().out


def test_a_missing_resume_for_a_live_role_fails(tmp_path, capsys):
    folder = housekeeping_folder(tmp_path, {"live": "new"})
    (folder / "resumes" / "live.docx").unlink()
    assert sync.main(["--dir", str(folder), "--no-pdf"]) == 1
    assert "MISSING" in capsys.readouterr().out


def test_job_id_records_the_resume_path_in_the_tracker(tmp_path):
    write_jobs(tmp_path, [job()])
    edits = [{"match": "Backend engineer", "kind": "plain", "text": "Go and Python engineer."}]
    assert tailor_run(tmp_path, edits, "--no-pdf", "--job-id", "acme-staff-engineer") == 0
    assert read_jobs(tmp_path)[0]["resume"] == "resumes/Acme - Staff Engineer.docx"


def test_a_resume_for_an_applied_role_is_never_replaced(tmp_path, capsys):
    write_jobs(tmp_path, [job(status="applied", resume="resumes/sent.docx")])
    edits = [{"match": "Backend engineer", "kind": "plain", "text": "Go and Python engineer."}]
    assert tailor_run(tmp_path, edits, "--no-pdf", "--job-id", "acme-staff-engineer") == 1
    assert not (tmp_path / OUT).exists()
    assert read_jobs(tmp_path)[0]["resume"] == "resumes/sent.docx"
    assert "applied" in capsys.readouterr().err


# --- review fixes -----------------------------------------------------------------------------


def add_paragraph(path: Path, text: str) -> None:
    doc = Document(path)
    doc.add_paragraph(text)
    doc.save(path)


def test_resync_never_rewrites_a_tailored_line_that_has_a_date(tmp_path):
    folder = housekeeping_folder(tmp_path, {"live": "new"})
    add_paragraph(
        folder / "base.docx", "Promoted to senior engineer in March 2022 after the launch."
    )
    tailored = folder / "resumes" / "live.docx"
    add_paragraph(tailored, "Promoted to senior engineer in March 2022 after leading agents.")
    assert sync.main(["--dir", str(folder), "--apply", "--no-pdf"]) == 0
    lines = texts(tailored)
    assert lines[-1] == "Promoted to senior engineer in March 2022 after leading agents."
    assert lines[4] == "Acme, Lisbon\tFeb 2020 — Present"


def test_resumes_for_in_process_roles_are_frozen(tmp_path, capsys):
    folder = housekeeping_folder(tmp_path, {"talking": "in_process"})
    assert sync.main(["--dir", str(folder), "--apply", "--no-pdf"]) == 0
    assert "Jan 2020" in texts(folder / "resumes" / "talking.docx")[4]
    assert "ALREADY APPLIED" in capsys.readouterr().out


def test_archiving_never_overwrites_an_archived_file(tmp_path):
    folder = housekeeping_folder(tmp_path, {"gone": "rejected"})
    archive = folder / "resumes" / "_archive"
    archive.mkdir()
    (archive / "gone.docx").write_bytes(b"older archived copy")
    assert sync.main(["--dir", str(folder), "--apply", "--no-pdf"]) == 0
    assert (archive / "gone.docx").read_bytes() == b"older archived copy"
    moved = read_jobs(folder)[0]["resume"]
    assert moved != "resumes/_archive/gone.docx"
    assert (folder / moved).exists() and (folder / moved).with_suffix(".pdf").exists()


def test_tailoring_refuses_to_overwrite_the_base_resume(tmp_path):
    make_resume(tmp_path / "base.docx")
    before = (tmp_path / "base.docx").read_bytes()
    edits = write_edits(tmp_path, [{"match": "Backend", "kind": "plain", "text": "Go engineer."}])
    code = tailor.main(
        [
            "--dir",
            str(tmp_path),
            "--base",
            "base.docx",
            "--out",
            "base.docx",
            "--edits",
            str(edits),
            "--no-pdf",
        ]
    )
    assert code == 1
    assert (tmp_path / "base.docx").read_bytes() == before


def test_tailoring_refuses_to_overwrite_a_sent_resume(tmp_path):
    write_jobs(tmp_path, [job(status="applied", resume=OUT.as_posix())])
    (tmp_path / "resumes").mkdir()
    (tmp_path / OUT).write_bytes(b"the version that was sent")
    edits = [{"match": "Backend engineer", "kind": "plain", "text": "Go and Python engineer."}]
    assert tailor_run(tmp_path, edits, "--no-pdf") == 1
    assert (tmp_path / OUT).read_bytes() == b"the version that was sent"


def test_a_match_that_starts_two_paragraphs_is_refused(tmp_path, capsys):
    edits = [{"match": "B", "kind": "plain", "text": "Changed."}]
    assert tailor_run(tmp_path, edits, "--no-pdf") == 1
    assert not (tmp_path / OUT).exists()
    assert "more than one paragraph" in capsys.readouterr().err


def test_relative_base_and_edits_are_read_from_the_folder(tmp_path, monkeypatch):
    folder = tmp_path / "search"
    folder.mkdir()
    make_resume(folder / "base.docx")
    write_edits(folder, [{"match": "Backend", "kind": "plain", "text": "Go engineer."}])
    monkeypatch.chdir(tmp_path)
    code = tailor.main(
        [
            "--dir",
            str(folder),
            "--base",
            "base.docx",
            "--out",
            OUT.as_posix(),
            "--edits",
            "edits.json",
            "--no-pdf",
        ]
    )
    assert code == 0
    assert texts(folder / OUT)[2] == "Go engineer."


# --- read-only folders and files ------------------------------------------------------------


@NOT_ROOT
def test_tailoring_into_a_read_only_folder_gives_a_clean_error(tmp_path, capsys):
    (tmp_path / "resumes").mkdir()
    (tmp_path / "resumes").chmod(0o555)
    edits = [{"match": "alex@example.com", "kind": "plain", "text": "alex@example.com"}]
    try:
        assert tailor_run(tmp_path, edits, "--no-pdf") == 1
    finally:
        (tmp_path / "resumes").chmod(0o755)
    assert capsys.readouterr().err.startswith("error: cannot write")


@NOT_ROOT
def test_a_resume_that_cannot_be_archived_is_reported_and_stays_tracked(tmp_path, capsys):
    folder = housekeeping_folder(tmp_path, {"gone": "rejected"})
    (folder / "resumes").chmod(0o555)
    try:
        assert sync.main(["--dir", str(folder), "--apply", "--no-pdf"]) == 1
    finally:
        (folder / "resumes").chmod(0o755)
    out = capsys.readouterr().out
    assert "CANNOT ARCHIVE" in out and "permission denied" in out
    assert (folder / "resumes" / "gone.docx").exists()
    assert read_jobs(folder)[0]["resume"] == "resumes/gone.docx"


@NOT_ROOT
def test_a_read_only_resume_is_reported_instead_of_resynced(tmp_path, capsys):
    folder = housekeeping_folder(tmp_path, {"live": "new"})
    (folder / "resumes" / "live.docx").chmod(0o444)
    assert sync.main(["--dir", str(folder), "--apply", "--no-pdf"]) == 1
    out = capsys.readouterr().out
    assert "CANNOT RESYNC" in out and "permission denied" in out


def _employer_line(path: Path, date: str) -> Path:
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Acme Corp").bold = True
    p.add_run(f" | {date} - Present")
    doc.save(path)
    return path


def test_resync_changes_only_the_date_and_keeps_the_bold_run(tmp_path):
    tailored = _employer_line(tmp_path / "tailored.docx", "Jan 2020")
    changes, problems = sync.resync(tailored, ["Acme Corp | Mar 2020 - Present"], apply=True)
    assert problems == []
    assert len(changes) == 1
    runs = [(r.text, bool(r.bold)) for r in Document(tailored).paragraphs[0].runs]
    assert runs == [("Acme Corp", True), (" | Mar 2020 - Present", False)]


def test_tailoring_checks_against_the_page_count_in_the_profile(tmp_path):
    assert tailor.page_target(tmp_path, None) is None
    (tmp_path / "profile.yaml").write_text("resume:\n  page_count: 2\n", encoding="utf-8")
    assert tailor.page_target(tmp_path, None) == 2
    assert tailor.page_target(tmp_path, 3) == 3


def test_the_base_page_count_is_rendered_once_and_cached(tmp_path, monkeypatch):
    base = make_resume(tmp_path / "base.docx")
    (tmp_path / "tmp").mkdir()
    monkeypatch.setattr(tailor.tempfile, "tempdir", str(tmp_path / "tmp"))
    renders = []

    def fake_soffice(soffice, docx_path, outdir):
        renders.append(docx_path.name)
        docx_path.with_suffix(".pdf").write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(tailor, "find_soffice", lambda: "soffice")
    monkeypatch.setattr(tailor, "run_soffice", fake_soffice)
    monkeypatch.setattr(tailor, "pdf_pages", lambda path: 2)
    assert tailor.expected_pages(base, None) == 2
    assert tailor.expected_pages(base, None) == 2
    assert renders == ["base.docx"]
    make_resume(base, date="Mar 2020")  # a changed base is rendered again
    assert tailor.expected_pages(base, None) == 2
    assert len(renders) == 2
