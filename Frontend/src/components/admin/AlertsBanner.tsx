import { BellRing } from "lucide-react";

import type { SystemStatus } from "@/api/types";

/** Alertes actives (taux d'erreur, latence) : seuils dépassés sur la fenêtre récente. */
const AlertsBanner = ({ alerts }: { alerts?: SystemStatus["alerts"] }) => {
  if (!alerts || alerts.length === 0) return null;
  return (
    <div role="alert" className="rounded-lg border border-destructive/40 bg-destructive/10 p-4">
      <div className="mb-2 flex items-center gap-2 font-medium text-destructive">
        <BellRing className="h-4 w-4" />
        {alerts.length === 1 ? "1 alerte active" : `${alerts.length} alertes actives`}
      </div>
      <ul className="space-y-1 text-sm text-destructive">
        {alerts.map((alert) => (
          <li key={alert.kind}>{alert.message}</li>
        ))}
      </ul>
    </div>
  );
};

export default AlertsBanner;
