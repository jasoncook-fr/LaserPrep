
import project_processing
import pypdfium2 as pdfium


def create_file(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test", encoding="utf-8")
    return path

def read_student_report(folder, language="FR"):
    path = (
        folder
        / "reports"
        / f"{folder.name}.base_report_{language}.pdf"
    )

    document = pdfium.PdfDocument(str(path))
    pages = []
    for page in document:
        textpage = page.get_textpage()
        pages.append(textpage.get_text_range())
    return "\n".join(pages)

def run_cleanup(folder, preserve=None):
    info_messages = []
    warning_messages = []

    project_processing.cleanup_warning_outputs(
        folder,
        preserve_pdf_stems=preserve,
        print_info=info_messages.append,
        print_warning=warning_messages.append,
    )

    return info_messages, warning_messages


def test_cleanup_removes_root_bad_color_preview(tmp_path):
    folder = tmp_path / "COOK"
    preview = create_file(folder / "drawing_bad_colors.svg")

    run_cleanup(folder)

    assert not preview.exists()


def test_cleanup_removes_report_bad_color_preview(tmp_path):
    folder = tmp_path / "COOK"
    preview = create_file(
        folder / "reports" / "drawing_bad_colors.svg"
    )

    run_cleanup(folder)

    assert not preview.exists()


def test_cleanup_removes_geometry_overlap_warnings(tmp_path):
    folder = tmp_path / "COOK"

    root_warning = create_file(
        folder / "Geometry_Overlap_Warning - drawing.svg"
    )
    report_warning = create_file(
        folder / "reports" / "Geometry_Overlap_Warning - drawing.svg"
    )

    run_cleanup(folder)

    assert not root_warning.exists()
    assert not report_warning.exists()


def test_cleanup_preserves_cached_bad_color_preview(tmp_path):
    folder = tmp_path / "COOK"
    preview = create_file(
        folder / "reports" / "drawing_bad_colors.svg"
    )

    run_cleanup(folder, preserve={"drawing"})

    assert preview.exists()


def test_cleanup_preserves_cached_geometry_warning(tmp_path):
    folder = tmp_path / "COOK"
    warning = create_file(
        folder / "reports" / "Geometry_Overlap_Warning - drawing.svg"
    )

    run_cleanup(folder, preserve={"drawing"})

    assert warning.exists()


def test_cleanup_removes_unrelated_stale_outputs(tmp_path):
    folder = tmp_path / "COOK"

    stale_preview = create_file(
        folder / "reports" / "old_bad_colors.svg"
    )
    stale_warning = create_file(
        folder / "Geometry_Overlap_Warning - old.svg"
    )

    run_cleanup(folder, preserve={"drawing"})

    assert not stale_preview.exists()
    assert not stale_warning.exists()


def test_cleanup_creates_reports_directory(tmp_path):
    folder = tmp_path / "COOK"

    run_cleanup(folder)

    assert (folder / "reports").is_dir()


def test_cleanup_reports_removed_files(tmp_path):
    folder = tmp_path / "COOK"
    preview = create_file(folder / "drawing_bad_colors.svg")

    info_messages, warning_messages = run_cleanup(folder)

    assert any(str(preview) in message for message in info_messages)
    assert warning_messages == []

def test_process_project_without_pdfs_returns_no_output(tmp_path):
    warnings = []
    errors = []
    successes = []
    infos = []

    result = project_processing.process_project(
        tmp_path,
        print_error=errors.append,
        print_warning=warnings.append,
        print_success=successes.append,
        print_info=infos.append,
    )

    assert result == "no_output"
    assert warnings == [f"No PDF files found in {tmp_path}"]
    assert errors == []
    assert successes == []

def test_process_project_skips_complete_unchanged_cache(
    tmp_path, monkeypatch
):
    folder = tmp_path / "COOK"
    folder.mkdir()

    pdf = folder / "drawing.pdf"
    pdf.write_bytes(b"test PDF content")

    reports = folder / "reports"
    reports.mkdir()

    create_file(reports / "COOK.base_report_FR.pdf")
    create_file(reports / "COOK.base_report_EN.pdf")

    (reports / "COOK.extensive_report.txt").write_text(
        "Extensive report",
        encoding="utf-8",
    )
    (folder / "COOK.svg").write_text(
        "SVG",
        encoding="utf-8",
    )

    pdf_digest = project_processing.pdf_hash(pdf)

    monkeypatch.setattr(
        project_processing,
        "load_processing_records",
        lambda folder: {
            "drawing.pdf": {
                "hash": pdf_digest,
                "status": "PASS",
                "entry": {},
            }
        },
    )

    def unexpected_cleanup(*args, **kwargs):
        raise AssertionError("Cleanup should not run for a skipped project")

    monkeypatch.setattr(
        project_processing,
        "cleanup_warning_outputs",
        unexpected_cleanup,
    )

    messages = []

    result = project_processing.process_project(
        folder,
        print_error=messages.append,
        print_warning=messages.append,
        print_success=messages.append,
        print_info=messages.append,
    )

    assert result == "skipped"
    assert messages == []

def prepare_rejection_test(monkeypatch):
    class FakeDebugManager:
        def __init__(self, *args, **kwargs):
            pass

        def start_run(self, *args, **kwargs):
            pass

        def finish(self, *args, **kwargs):
            pass

        def save_text(self, *args, **kwargs):
            pass

        def save_svg(self, *args, **kwargs):
            pass

    monkeypatch.setattr(
        project_processing,
        "DebugManager",
        FakeDebugManager,
    )

    monkeypatch.setattr(
        project_processing.diag,
        "begin",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        project_processing.diag,
        "end",
        lambda *args, **kwargs: None,
    )


def run_rejection_test(folder):
    errors = []
    warnings = []
    successes = []
    infos = []

    result = project_processing.process_project(
        folder,
        use_state=False,
        print_error=errors.append,
        print_warning=warnings.append,
        print_success=successes.append,
        print_info=infos.append,
    )

    return result, errors, warnings, successes, infos

def test_process_project_rejects_unreadable_pdf(
    tmp_path, monkeypatch
):
    folder = tmp_path / "COOK"
    pdf = create_file(folder / "drawing.pdf")

    prepare_rejection_test(monkeypatch)

    def fake_open(*args, **kwargs):
        raise RuntimeError("Invalid PDF")

    monkeypatch.setattr(project_processing.fitz, "open", fake_open)

    result, errors, warnings, successes, infos = (
        run_rejection_test(folder)
    )

    report = read_student_report(folder)

    assert result == "completed"
    assert any("Could not read drawing.pdf" in msg for msg in errors)
    assert "NON ACCEPTÉ" in report
    assert not (folder / "COOK.svg").exists()


def test_process_project_rejects_multipage_pdf(
    tmp_path, monkeypatch
):
    folder = tmp_path / "COOK"
    create_file(folder / "drawing.pdf")

    prepare_rejection_test(monkeypatch)

    class FakeDocument:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __len__(self):
            return 2

    monkeypatch.setattr(
        project_processing.fitz,
        "open",
        lambda *args, **kwargs: FakeDocument(),
    )

    result, errors, warnings, successes, infos = (
        run_rejection_test(folder)
    )

    report = read_student_report(folder)

    assert result == "completed"
    assert any("multiple pages (2)" in msg for msg in errors)
    assert "NON ACCEPTÉ" in report
    assert not (folder / "COOK.svg").exists()


def test_process_project_rejects_excessive_pdf_complexity(
    tmp_path, monkeypatch
):
    folder = tmp_path / "COOK"
    create_file(folder / "drawing.pdf")

    prepare_rejection_test(monkeypatch)

    class FakeDocument:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __len__(self):
            return 1

        def __getitem__(self, index):
            return object()

    monkeypatch.setattr(
        project_processing.fitz,
        "open",
        lambda *args, **kwargs: FakeDocument(),
    )

    monkeypatch.setattr(
        project_processing,
        "analyse_pdf_complexity",
        lambda page: type(
            "FakeComplexity",
            (),
            {
                "should_abort": True,
                "point_count": 25001,
            },
        )(),
    )

    monkeypatch.setattr(
        project_processing,
        "analyse_pdf_content",
        lambda page: type(
            "FakeContent",
            (),
            {"is_non_vector": False},
        )(),
    )

    result, errors, warnings, successes, infos = (
        run_rejection_test(folder)
    )

    report = read_student_report(folder)

    assert result == "completed"
    assert any("25,001 vector points" in msg for msg in errors)
    assert "NON ACCEPTÉ" in report
    assert not (folder / "COOK.svg").exists()


def test_process_project_rejects_raster_only_pdf(
    tmp_path, monkeypatch
):
    folder = tmp_path / "COOK"
    create_file(folder / "drawing.pdf")

    prepare_rejection_test(monkeypatch)

    class FakeDocument:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __len__(self):
            return 1

        def __getitem__(self, index):
            return object()

    monkeypatch.setattr(
        project_processing.fitz,
        "open",
        lambda *args, **kwargs: FakeDocument(),
    )

    monkeypatch.setattr(
        project_processing,
        "analyse_pdf_complexity",
        lambda page: type(
            "FakeComplexity",
            (),
            {
                "should_abort": False,
                "point_count": 100,
                "rating": "LOW",
            },
        )(),
    )

    monkeypatch.setattr(
        project_processing,
        "analyse_pdf_content",
        lambda page: type(
            "FakeContent",
            (),
            {"is_non_vector": True},
        )(),
    )

    result, errors, warnings, successes, infos = (
        run_rejection_test(folder)
    )

    report = read_student_report(folder)

    assert result == "completed"
    assert any("no usable vector artwork" in msg for msg in errors)
    assert "NON ACCEPTÉ" in report
    assert not (folder / "COOK.svg").exists()
