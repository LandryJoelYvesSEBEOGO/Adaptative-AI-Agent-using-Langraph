import type { Citation } from "@/api/types";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import { citationLabel, citationMeta } from "@/lib/sources";

interface CitationBadgeProps {
  number: number;
  citation: Citation | undefined;
  onOpen: (number: number) => void;
}

/** Renvoi [n] : aperçu de la source au survol, panneau des sources au clic. */
const CitationBadge = ({ number, citation, onOpen }: CitationBadgeProps) => {
  const badge = "mx-0.5 align-super text-[0.7em] font-semibold leading-none";
  if (!citation) {
    // numéro cité par le modèle mais absent des sources : affiché sans interaction
    return <sup className={`${badge} text-muted-foreground`}>[{number}]</sup>;
  }
  const meta = citationMeta(citation);
  return (
    <HoverCard openDelay={150} closeDelay={80}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          onClick={() => onOpen(number)}
          aria-label={`Source ${number} : ${citationLabel(citation)}`}
          className={`${badge} rounded bg-primary/10 px-1 py-0.5 text-primary hover:bg-primary/20 focus-visible:outline-2 focus-visible:outline-primary`}
        >
          [{number}]
        </button>
      </HoverCardTrigger>
      <HoverCardContent className="w-80 text-sm" side="top">
        <p className="font-medium">{citationLabel(citation)}</p>
        {meta.section && <p className="mt-0.5 text-xs text-muted-foreground">{meta.section}</p>}
        <p className="mt-2 line-clamp-4 text-xs text-muted-foreground">{citation.excerpt}</p>
        <p className="mt-2 text-xs text-primary">Cliquer pour voir la page du document</p>
      </HoverCardContent>
    </HoverCard>
  );
};

export default CitationBadge;
