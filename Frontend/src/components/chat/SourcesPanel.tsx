import { ExternalLink } from "lucide-react";
import { lazy, Suspense } from "react";

import type { Citation } from "@/api/types";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { citationLabel, citationMeta, documentUrl } from "@/lib/sources";

// react-pdf (pdf.js) est volumineux : chargé uniquement à l'ouverture d'une source
const PdfPreview = lazy(() => import("./PdfPreview"));

interface SourcesPanelProps {
  citations: Citation[];
  /** Numéro de la citation sélectionnée ; `null` = panneau fermé. */
  selected: number | null;
  onSelect: (number: number) => void;
  onClose: () => void;
}

const SourcesPanel = ({ citations, selected, onSelect, onClose }: SourcesPanelProps) => {
  const current = citations.find((citation) => citation.id === selected);
  const meta = current ? citationMeta(current) : null;
  const url = current ? documentUrl(current) : null;

  return (
    <Sheet open={selected !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto" aria-describedby="sources-description">
        <SheetHeader>
          <SheetTitle>Sources</SheetTitle>
          <SheetDescription id="sources-description">
            Passages sur lesquels s'appuie la réponse.
          </SheetDescription>
        </SheetHeader>

        <ul className="mt-4 flex flex-wrap gap-2" aria-label="Liste des sources">
          {citations.map((citation) => (
            <li key={citation.id}>
              <button
                type="button"
                onClick={() => onSelect(citation.id)}
                aria-pressed={citation.id === selected}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs transition-colors",
                  citation.id === selected
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                [{citation.id}] {citationLabel(citation)}
              </button>
            </li>
          ))}
        </ul>

        {current && meta && (
          <div className="mt-6 space-y-4" data-testid="source-detail">
            <div>
              <p className="font-medium">{current.source}</p>
              {meta.section && <p className="text-sm text-muted-foreground">{meta.section}</p>}
            </div>
            <blockquote className="border-l-2 border-primary/50 pl-3 text-sm text-muted-foreground whitespace-pre-wrap">
              {current.excerpt}
            </blockquote>

            {url && !meta.isWeb && meta.page ? (
              <div className="overflow-hidden rounded-lg border border-border bg-muted/30 p-2">
                <Suspense fallback={<p className="text-sm text-muted-foreground">Chargement de l'aperçu…</p>}>
                  <PdfPreview url={url} page={meta.page} width={480} />
                </Suspense>
              </div>
            ) : null}

            {url && (
              <a
                href={meta.isWeb || !meta.page ? url : `${url}#page=${meta.page}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
              >
                <ExternalLink className="h-4 w-4" />
                {meta.isWeb ? "Ouvrir la page web" : `Ouvrir le PDF${meta.page ? ` à la page ${meta.page}` : ""}`}
              </a>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};

export default SourcesPanel;
