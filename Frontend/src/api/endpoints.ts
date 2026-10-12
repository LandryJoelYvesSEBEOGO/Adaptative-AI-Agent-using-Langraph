import { ApiError } from "./errors";
import { api, apiUrl, fetchWithRefresh, unwrap, unwrapVoid } from "./client";
import { toApiError } from "./errors";
import type { DocumentInfo, FeedbackType, User, UserRole } from "./types";

// ---- Authentification -----------------------------------------------------------------

async function authResult(
  call: Promise<{
    data?: { success: boolean; user?: User | null; error?: string | null };
    error?: unknown;
    response: Response;
  }>,
): Promise<User> {
  const body = await unwrap(call);
  if (!body.success || !body.user) throw new ApiError(body.error ?? "Authentification impossible", 401);
  return body.user;
}

export const login = (email: string, password: string) =>
  authResult(api.POST("/api/v1/auth/login", { body: { email, password } }));

export const register = (email: string, password: string, name: string) =>
  authResult(api.POST("/api/v1/auth/register", { body: { email, password, name } }));

export const logout = () => unwrap(api.POST("/api/v1/auth/logout"));

/** Utilisateur de la session courante, ou `null` si personne n'est connecté. */
export async function fetchSession(): Promise<User | null> {
  const { data, response, error } = await api.GET("/api/v1/auth/me");
  if (response.status === 401) return null;
  if (!response.ok || !data) throw new ApiError("Impossible de vérifier la session", response.status);
  void error;
  return data;
}

// ---- Conversations --------------------------------------------------------------------

export const listConversations = () => unwrap(api.GET("/api/v1/chat/conversations"));

export const listMessages = (conversationId: string) =>
  unwrap(
    api.GET("/api/v1/chat/conversations/{conversation_id}/messages", {
      params: { path: { conversation_id: conversationId } },
    }),
  );

export const sendFeedback = (messageId: string, feedbackType: FeedbackType) =>
  unwrap(
    api.POST("/api/v1/chat/feedback", {
      body: { message_id: messageId, feedback_type: feedbackType },
    }),
  );

// ---- Administration -------------------------------------------------------------------

export const getMetricsOverview = () => unwrap(api.GET("/api/v1/admin/metrics/overview"));

export const getRequestsChart = (days = 7) =>
  unwrap(api.GET("/api/v1/admin/metrics/requests", { params: { query: { days } } }));

export const getRecentRequests = (limit = 10) =>
  unwrap(api.GET("/api/v1/admin/metrics/recent", { params: { query: { limit } } }));

export const getRequestDetails = (limit = 50) =>
  unwrap(api.GET("/api/v1/admin/requests", { params: { query: { limit } } }));

export const getLatencyComponents = () => unwrap(api.GET("/api/v1/admin/metrics/latency/components"));

export const getLatencyTrend = (days = 7) =>
  unwrap(api.GET("/api/v1/admin/metrics/latency/trend", { params: { query: { days } } }));

export const getErrorDistribution = () => unwrap(api.GET("/api/v1/admin/metrics/errors"));

export const getSystemStatus = () => unwrap(api.GET("/api/v1/admin/system/status"));

// ---- Documents --------------------------------------------------------------------------

export const listDocuments = () => unwrap(api.GET("/api/v1/documents"));

export interface UploadMetadata {
  company?: string;
  fiscalYear?: number;
  docType?: string;
}

/** Téléverse un PDF (multipart) ; l'indexation se poursuit côté serveur (voir le statut). */
export async function uploadDocument(file: File, metadata: UploadMetadata = {}): Promise<DocumentInfo> {
  const form = new FormData();
  form.append("file", file);
  if (metadata.company) form.append("company", metadata.company);
  if (metadata.fiscalYear) form.append("fiscal_year", String(metadata.fiscalYear));
  if (metadata.docType) form.append("doc_type", metadata.docType);

  const response = await fetchWithRefresh(
    new Request(apiUrl("/api/v1/documents"), { method: "POST", body: form, credentials: "include" }),
  );
  const body: unknown = await response.json().catch(() => undefined);
  if (!response.ok) throw toApiError(response, body);
  return body as DocumentInfo;
}

export const reindexDocument = (id: string) =>
  unwrap(api.POST("/api/v1/documents/{document_id}/reindex", { params: { path: { document_id: id } } }));

export const deleteDocument = (id: string) =>
  unwrapVoid(api.DELETE("/api/v1/documents/{document_id}", { params: { path: { document_id: id } } }));

// ---- Utilisateurs (administration) ------------------------------------------------------

export const listUsers = () => unwrap(api.GET("/api/v1/admin/users"));

export const updateUserRole = (id: string, role: UserRole) =>
  unwrap(
    api.PATCH("/api/v1/admin/users/{user_id}", {
      params: { path: { user_id: id } },
      body: { role },
    }),
  );

export const deleteUser = (id: string) =>
  unwrapVoid(api.DELETE("/api/v1/admin/users/{user_id}", { params: { path: { user_id: id } } }));
