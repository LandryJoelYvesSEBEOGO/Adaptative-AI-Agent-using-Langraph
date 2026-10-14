"""Découpage en chunks par sections, avec tableaux conservés entiers.

L'entrée est du Markdown paginé (produit par Docling : titres `#`, tableaux `| … |`).
Règles :
- un titre de niveau 1-2 ferme le chunk courant (une section = un ou plusieurs chunks) ;
- un tableau n'est jamais coupé au milieu d'une ligne : il forme son propre chunk, et s'il
  dépasse la taille maximale il est scindé par lignes avec répétition de l'en-tête ;
- le texte est regroupé par paragraphes jusqu'à `max_chars`.
"""

import re
from dataclasses import dataclass, field

from src.ingestion.metadata import DocumentMetadata

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass
class Page:
    number: int
    markdown: str


@dataclass
class Chunk:
    ordinal: int
    content: str
    section: str
    page_start: int
    page_end: int
    kind: str = "text"  # "text" | "table"

    def embedding_text(self, meta: DocumentMetadata) -> str:
        """Texte indexé : le contenu précédé de son contexte (société, exercice, section)."""
        parts = [meta.company, str(meta.fiscal_year) if meta.fiscal_year else None, meta.doc_type]
        header = " ".join(p for p in parts if p)
        context = " — ".join(p for p in (header, self.section) if p)
        return f"[{context}]\n{self.content}" if context else self.content


@dataclass
class _Block:
    kind: str  # "heading" | "table" | "text"
    text: str
    page: int
    level: int = 0


def _blocks(pages: list[Page]) -> list[_Block]:
    blocks: list[_Block] = []
    for page in pages:
        paragraph: list[str] = []
        table: list[str] = []

        def flush_paragraph(page_number=page.number, paragraph=paragraph):
            if paragraph:
                blocks.append(_Block("text", "\n".join(paragraph).strip(), page_number))
                paragraph.clear()

        def flush_table(page_number=page.number, table=table):
            if table:
                blocks.append(_Block("table", "\n".join(table), page_number))
                table.clear()

        for line in page.markdown.splitlines():
            heading = _HEADING.match(line)
            if line.lstrip().startswith("|"):
                flush_paragraph()
                table.append(line.rstrip())
            elif heading:
                flush_paragraph()
                flush_table()
                blocks.append(
                    _Block("heading", heading.group(2), page.number, level=len(heading.group(1)))
                )
            elif not line.strip():
                flush_paragraph()
                flush_table()
            else:
                flush_table()
                paragraph.append(line.rstrip())
        flush_paragraph()
        flush_table()
    return [b for b in blocks if b.text]


def _split_text(text: str, max_chars: int) -> list[str]:
    """Scinde un paragraphe trop long aux fins de phrase, sinon à la limite."""
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        while len(sentence) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        if current and len(current) + 1 + len(sentence) > max_chars:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def _split_table(table: str, max_chars: int) -> list[str]:
    if len(table) <= max_chars:
        return [table]
    rows = table.splitlines()
    header = (
        rows[:2] if len(rows) > 2 and set(rows[1].replace("|", "").strip()) <= set("-: ") else []
    )
    body = rows[len(header) :]
    parts, current = [], list(header)
    for row in body:
        candidate = "\n".join([*current, row])
        if len(candidate) > max_chars and len(current) > len(header):
            parts.append("\n".join(current))
            current = [*header, row]
        else:
            current.append(row)
    if len(current) > len(header):
        parts.append("\n".join(current))
    return parts


@dataclass
class _Builder:
    max_chars: int
    chunks: list[Chunk] = field(default_factory=list)
    texts: list[_Block] = field(default_factory=list)
    section: str = ""

    def _emit(self, content: str, page_start: int, page_end: int, kind: str):
        self.chunks.append(
            Chunk(len(self.chunks), content.strip(), self.section, page_start, page_end, kind)
        )

    def flush_text(self):
        if self.texts:
            content = "\n\n".join(b.text for b in self.texts)
            self._emit(content, self.texts[0].page, self.texts[-1].page, "text")
            self.texts = []

    def add_text(self, block: _Block):
        for piece in _split_text(block.text, self.max_chars):
            size = sum(len(b.text) for b in self.texts) + 2 * len(self.texts)
            if self.texts and size + len(piece) > self.max_chars:
                self.flush_text()
            self.texts.append(_Block("text", piece, block.page))

    def add_table(self, block: _Block):
        self.flush_text()
        for part in _split_table(block.text, self.max_chars):
            self._emit(part, block.page, block.page, "table")


def chunk_pages(pages: list[Page], max_chars: int = 3000, min_chars: int = 400) -> list[Chunk]:
    """Découpe un document paginé en chunks. `min_chars` évite les mini-sections isolées :
    un titre de niveau ≥ 3 ne ferme le chunk courant que s'il est déjà assez long."""
    builder = _Builder(max_chars=max_chars)
    stack: list[tuple[int, str]] = []
    for block in _blocks(pages):
        if block.kind == "heading":
            current_len = sum(len(b.text) for b in builder.texts)
            if block.level <= 2 or current_len >= min_chars:
                builder.flush_text()
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.text))
            builder.section = " > ".join(title for _, title in stack)
        elif block.kind == "table":
            builder.add_table(block)
        else:
            builder.add_text(block)
    builder.flush_text()
    return builder.chunks
