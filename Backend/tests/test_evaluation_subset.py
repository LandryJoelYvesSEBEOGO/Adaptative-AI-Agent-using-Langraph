from pathlib import Path

from evaluation.dataset import load_dataset
from evaluation.subset import build_subset

SAMPLE = Path(__file__).parent / "fixtures" / "financebench_sample.jsonl"


def test_subset_copies_only_needed_pdfs(tmp_path):
    pdfs = tmp_path / "all"
    pdfs.mkdir()
    for name in (
        "3M_2018_10K.pdf",
        "ADOBE_2022_10K.pdf",
        "AMCOR_2020_10K.pdf",
        "UNUSED_2019_10K.pdf",
    ):
        (pdfs / name).write_bytes(b"%PDF-1.4")

    report = build_subset(SAMPLE, pdfs, limit=2, out_dir=tmp_path / "out", seed=3)
    chosen = load_dataset(tmp_path / "out" / "questions.jsonl")
    assert len(chosen) == 2 and report["questions"] == 2
    copied = {p.name for p in (tmp_path / "out" / "pdfs").iterdir()}
    assert copied == set(report["pdfs"]) and "UNUSED_2019_10K.pdf" not in copied
    assert report["missing_pdfs"] == []


def test_subset_reports_missing_pdfs(tmp_path):
    (tmp_path / "pdfs").mkdir()
    report = build_subset(SAMPLE, tmp_path / "pdfs", limit=3, out_dir=tmp_path / "out")
    assert len(report["missing_pdfs"]) == 3
