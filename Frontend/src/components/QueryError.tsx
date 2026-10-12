import { AlertTriangle } from "lucide-react";

import { errorMessage } from "@/api/errors";
import { Button } from "@/components/ui/button";

interface QueryErrorProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}

/** Erreur de chargement affichée en place des données, avec relance. */
const QueryError = ({ error, onRetry, className }: QueryErrorProps) => (
  <div
    role="alert"
    className={`flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive ${className ?? ""}`}
  >
    <AlertTriangle className="w-4 h-4 shrink-0" />
    <span className="flex-1">{errorMessage(error, "Impossible de charger les données.")}</span>
    {onRetry && (
      <Button variant="outline" size="sm" onClick={onRetry}>
        Réessayer
      </Button>
    )}
  </div>
);

export default QueryError;
