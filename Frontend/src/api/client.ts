import createClient from "openapi-fetch";

import { toApiError } from "./errors";
import type { paths } from "./schema";

/** Origine de l'API. Vide = même origine (proxy Vite en dev, nginx en production). */
export const API_ORIGIN: string = import.meta.env.VITE_API_URL ?? "";

/** Événement émis quand la session ne peut plus être renouvelée. */
export const AUTH_EXPIRED_EVENT = "auth:expired";

/** URL absolue d'une route de l'API (relative à la page quand l'origine est vide). */
export const apiUrl = (path: string): string => new URL(`${API_ORIGIN}${path}`, window.location.origin).toString();

const REFRESH_PATH = "/api/v1/auth/refresh";
const AUTH_PATHS = ["/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh"];
// Sondage de session au chargement : un échec de renouvellement n'est pas une « expiration »
const QUIET_PATHS = ["/api/v1/auth/me"];

let refreshing: Promise<boolean> | null = null;

/** Renouvelle la session (une seule requête à la fois, partagée par les appels concurrents). */
function refreshSession(): Promise<boolean> {
  refreshing ??= fetch(apiUrl(REFRESH_PATH), { method: "POST", credentials: "include" })
    .then((response) => response.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

/**
 * `fetch` avec renouvellement transparent : sur 401 (hors routes d'authentification), la session
 * est renouvelée via le cookie de refresh puis la requête est rejouée une fois.
 */
export async function fetchWithRefresh(request: Request): Promise<Response> {
  const retry = request.clone();
  const response = await fetch(request);
  const { pathname } = new URL(request.url, window.location.origin);
  if (response.status !== 401 || AUTH_PATHS.includes(pathname)) return response;

  if (await refreshSession()) return fetch(retry);
  if (!QUIET_PATHS.includes(pathname)) window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  return response;
}

/** Client typé par le schéma OpenAPI du backend (`npm run api:generate`). */
export const api = createClient<paths>({
  baseUrl: API_ORIGIN,
  credentials: "include",
  fetch: fetchWithRefresh,
});

type Result<T> = { data?: T; error?: unknown; response: Response };

/** Retourne les données ou lève une `ApiError` lisible. */
export async function unwrap<T>(call: Promise<Result<T>>): Promise<T> {
  const { data, error, response } = await call;
  if (!response.ok || error !== undefined) throw toApiError(response, error);
  return data as T;
}

/** Variante pour les réponses sans corps (204). */
export async function unwrapVoid(call: Promise<Result<unknown>>): Promise<void> {
  const { error, response } = await call;
  if (!response.ok || error !== undefined) throw toApiError(response, error);
}
