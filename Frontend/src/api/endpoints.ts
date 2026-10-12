import { ApiError } from "./errors";
import { api, unwrap, unwrapVoid } from "./client";
import type { FeedbackType, User } from "./types";

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

export { unwrapVoid };
