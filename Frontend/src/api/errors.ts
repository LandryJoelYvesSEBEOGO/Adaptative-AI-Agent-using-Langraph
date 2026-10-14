/** Erreur d'appel API, avec un message affichable à l'utilisateur. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isUnauthorized() {
    return this.status === 401;
  }

  get isForbidden() {
    return this.status === 403;
  }

  get isNotFound() {
    return this.status === 404;
  }

  get isServerError() {
    return this.status !== undefined && this.status >= 500;
  }
}

const DEFAULT_MESSAGES: Record<number, string> = {
  400: "Requête invalide.",
  401: "Session expirée. Veuillez vous reconnecter.",
  403: "Vous n'avez pas accès à cette ressource.",
  404: "Ressource introuvable.",
  409: "Cette opération est en conflit avec l'état actuel.",
  413: "Fichier trop volumineux.",
  415: "Format de fichier non pris en charge.",
  422: "Données invalides.",
  429: "Trop de requêtes. Réessayez dans un instant.",
};

/** Extrait un message lisible du corps d'erreur FastAPI (`detail`) ou de notre handler 500 (`error`). */
export function messageFromBody(body: unknown): string | undefined {
  if (!body || typeof body !== "object") return undefined;
  const { detail, error } = body as { detail?: unknown; error?: unknown };
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (typeof first?.msg === "string") return first.msg;
  }
  return typeof error === "string" ? error : undefined;
}

export function toApiError(response: Response, body: unknown): ApiError {
  const fallback =
    response.status >= 500
      ? "Erreur du serveur. Veuillez réessayer."
      : (DEFAULT_MESSAGES[response.status] ?? `Erreur ${response.status}`);
  return new ApiError(messageFromBody(body) ?? fallback, response.status);
}

/** Message affichable pour n'importe quelle erreur capturée. */
export function errorMessage(error: unknown, fallback = "Une erreur est survenue."): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "Impossible de joindre le serveur. Vérifiez votre connexion.";
  return error instanceof Error && error.message ? error.message : fallback;
}
