/** Schéma de lien interne pour les renvois de sources : `[1]` devient `[[1]](cite:1)`. */
export const CITE_PROTOCOL = "cite:";

const FENCE = /(```[\s\S]*?```|`[^`\n]*`)/g;
// [1] ou [1, 3] ; pas un lien markdown existant ([x](url)) ni une référence ([1]: url)
const MARKER = /\[(\d+(?:\s*,\s*\d+)*)\](?!\(|:)/g;

/**
 * Transforme les marqueurs de citation du modèle en liens `cite:N` rendus ensuite en badges.
 * Le code (en ligne ou en bloc) n'est pas modifié.
 */
export function linkCitations(markdown: string): string {
  return markdown
    .split(FENCE)
    .map((part, index) =>
      index % 2 === 1
        ? part
        : part.replace(MARKER, (_match, numbers: string) =>
            numbers
              .split(",")
              .map((n) => n.trim())
              .map((n) => `[\\[${n}\\]](${CITE_PROTOCOL}${n})`)
              .join(""),
          ),
    )
    .join("");
}

/** Extrait le numéro d'un lien `cite:N`, ou `null`. */
export function citationNumber(href: string | undefined): number | null {
  if (!href?.startsWith(CITE_PROTOCOL)) return null;
  const value = Number(href.slice(CITE_PROTOCOL.length));
  return Number.isInteger(value) && value > 0 ? value : null;
}
