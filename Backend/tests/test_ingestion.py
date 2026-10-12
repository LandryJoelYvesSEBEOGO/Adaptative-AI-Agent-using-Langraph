"""L3.2 : métadonnées, découpage par sections et tableaux conservés."""

import pytest

from src.ingestion.chunking import Page, chunk_pages
from src.ingestion.metadata import DocumentMetadata, parse_filename


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("3M_2018_10K.pdf", ("3M", 2018, None, "10-K")),
        ("AMERICANEXPRESS_2022_10K.pdf", ("AMERICANEXPRESS", 2022, None, "10-K")),
        ("3M_2023Q2_10Q.pdf", ("3M", 2023, 2, "10-Q")),
        ("ADOBE_2017_8K.pdf", ("ADOBE", 2017, None, "8-K")),
        ("Best_Buy_2019_10K.pdf", ("Best_Buy", 2019, None, "10-K")),
    ],
)
def test_parse_filename(filename, expected):
    meta = parse_filename(filename)
    assert (meta.company, meta.fiscal_year, meta.quarter, meta.doc_type) == expected


def test_parse_filename_unknown_convention():
    assert parse_filename("rapport final.pdf") == DocumentMetadata()


TABLE = """| Item | 2018 | 2017 |
|---|---|---|
| Net sales | 32,765 | 31,657 |
| Operating income | 7,207 | 7,692 |"""

PAGE_1 = f"""# Item 7. Management's Discussion

## Results of Operations

Net sales increased in 2018. Operating income decreased due to restructuring.

{TABLE}
"""

PAGE_2 = """## Liquidity

The Company generated strong operating cash flow. Capital expenditures were 1,577 million.

# Item 8. Financial Statements

Consolidated statements follow."""


def test_sections_pages_and_tables():
    chunks = chunk_pages([Page(10, PAGE_1), Page(11, PAGE_2)])
    sections = [c.section for c in chunks]
    assert "Item 7. Management's Discussion > Results of Operations" in sections
    assert "Item 7. Management's Discussion > Liquidity" in sections
    assert "Item 8. Financial Statements" in sections

    table_chunks = [c for c in chunks if c.kind == "table"]
    assert len(table_chunks) == 1
    assert table_chunks[0].content == TABLE  # le tableau est intact
    assert table_chunks[0].page_start == 10

    liquidity = next(c for c in chunks if c.section.endswith("Liquidity"))
    assert liquidity.page_start == 11 and "1,577" in liquidity.content
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_large_table_is_split_by_rows_with_repeated_header():
    rows = "\n".join(f"| Line {i} | {i * 10} | {i * 7} |" for i in range(200))
    big = "| Item | 2018 | 2017 |\n|---|---|---|\n" + rows
    chunks = chunk_pages([Page(1, "# Notes\n\n" + big)], max_chars=1000)
    tables = [c for c in chunks if c.kind == "table"]
    assert len(tables) > 1
    for chunk in tables:
        assert len(chunk.content) <= 1000
        assert chunk.content.startswith("| Item | 2018 | 2017 |\n|---|---|---|")
        assert all(line.startswith("|") for line in chunk.content.splitlines())
    rebuilt = [line for c in tables for line in c.content.splitlines()[2:]]
    assert rebuilt == rows.splitlines()  # aucune ligne perdue ni dupliquée


def test_long_text_is_split_below_max_size():
    text = " ".join(f"Sentence number {i} talks about revenue." for i in range(300))
    chunks = chunk_pages([Page(1, f"# Risk Factors\n\n{text}")], max_chars=800)
    assert len(chunks) > 5
    assert all(len(c.content) <= 800 for c in chunks)
    assert all(c.section == "Risk Factors" for c in chunks)


def test_embedding_text_carries_context():
    chunk = chunk_pages([Page(3, "# Item 1A. Risk Factors\n\nSupply chain risk.")])[0]
    meta = parse_filename("3M_2018_10K.pdf")
    text = chunk.embedding_text(meta)
    assert text.startswith("[3M 2018 10-K — Item 1A. Risk Factors]")
    assert "Supply chain risk." in text
    assert chunk.embedding_text(DocumentMetadata()).startswith("[Item 1A. Risk Factors]")


def test_empty_document():
    assert chunk_pages([]) == []
    assert chunk_pages([Page(1, "  \n\n")]) == []


def test_pypdf_fallback_extracts_text(tmp_path):
    reportlab = pytest.importorskip("reportlab.pdfgen.canvas")
    from src.ingestion.parsing import parse_pdf

    path = tmp_path / "ACME_2020_10K.pdf"
    canvas = reportlab.Canvas(str(path))
    canvas.drawString(72, 720, "Total revenue was 123 million.")
    canvas.showPage()
    canvas.save()
    pages = parse_pdf(path, parser="pypdf")
    assert pages and "123 million" in pages[0].markdown and pages[0].number == 1
