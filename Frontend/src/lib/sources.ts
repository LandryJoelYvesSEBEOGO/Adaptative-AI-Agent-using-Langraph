import { API_ORIGIN } from "@/api/client";
import type { Citation } from "@/api/types";

/** Métadonnées typées d'une citation (le schéma OpenAPI les expose en dictionnaire libre). */
export interface CitationMeta {
  page: number | null;
  section: string | null;
  company: string | null;
  fiscalYear: number | null;
  docType: string | null;
  documentId: string | null;
  isWeb: boolean;
}

export function citationMeta(citation: Citation): CitationMeta {
  const meta = (citation.metadata ?? {}) as Record<string, unknown>;
  const text = (key: string) => (typeof meta[key] === "string" && meta[key] ? (meta[key] as string) : null);
  const number = (key: string) => (typeof meta[key] === "number" ? (meta[key] as number) : null);
  return {
    page: number("page"),
    section: text("section"),
    company: text("company"),
    fiscalYear: number("fiscal_year"),
    docType: text("doc_type"),
    documentId: text("document_id"),
    isWeb: meta.is_web === true,
  };
}

/** Libellé court d'une source : « 3M · 2018 · 10-K · p. 60 ». */
export function citationLabel(citation: Citation): string {
  const meta = citationMeta(citation);
  if (meta.isWeb) return citation.source;
  const parts = [meta.company, meta.fiscalYear, meta.docType].filter((part) => part !== null && part !== "");
  const label = parts.length > 0 ? parts.join(" · ") : citation.source;
  return meta.page ? `${label} · p. ${meta.page}` : label;
}

/** URL du PDF source (aperçu et ouverture dans un nouvel onglet), ou `null` pour une source web. */
export function documentUrl(citation: Citation): string | null {
  const { documentId, isWeb } = citationMeta(citation);
  if (isWeb) return citation.source.startsWith("http") ? citation.source : null;
  return documentId ? `${API_ORIGIN}/api/v1/documents/${documentId}/file` : null;
}

export function byNumber(citations: Citation[] | null | undefined): Map<number, Citation> {
  return new Map((citations ?? []).map((citation) => [citation.id, citation]));
}
