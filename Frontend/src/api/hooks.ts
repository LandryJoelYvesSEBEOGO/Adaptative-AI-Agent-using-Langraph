import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as endpoints from "./endpoints";
import type { FeedbackType, Message } from "./types";

export const queryKeys = {
  conversations: ["conversations"] as const,
  messages: (conversationId: string) => ["messages", conversationId] as const,
  admin: {
    overview: ["admin", "overview"] as const,
    requestsChart: (days: number) => ["admin", "requests-chart", days] as const,
    recent: (limit: number) => ["admin", "recent", limit] as const,
    requests: (limit: number) => ["admin", "requests", limit] as const,
    latencyComponents: ["admin", "latency-components"] as const,
    latencyTrend: (days: number) => ["admin", "latency-trend", days] as const,
    errors: ["admin", "errors"] as const,
    status: ["admin", "status"] as const,
  },
};

// ---- Conversations ----------------------------------------------------------------------

export const useConversations = () =>
  useQuery({ queryKey: queryKeys.conversations, queryFn: endpoints.listConversations });

/** Messages d'une conversation (désactivé tant qu'aucune conversation n'est sélectionnée). */
export const useMessages = (conversationId: string | undefined) =>
  useQuery({
    queryKey: queryKeys.messages(conversationId ?? ""),
    queryFn: () => endpoints.listMessages(conversationId as string),
    enabled: Boolean(conversationId),
  });

/** Enregistre l'avis ; l'état affiché est mis à jour tout de suite, puis restauré en cas d'échec. */
export function useFeedback(conversationId: string | undefined) {
  const queryClient = useQueryClient();
  const key = queryKeys.messages(conversationId ?? "");
  return useMutation({
    mutationFn: ({ messageId, type }: { messageId: string; type: FeedbackType }) =>
      endpoints.sendFeedback(messageId, type),
    onMutate: async ({ messageId, type }) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<Message[]>(key);
      queryClient.setQueryData<Message[]>(key, (messages) =>
        messages?.map((m) => (m.id === messageId ? { ...m, feedback: type } : m)),
      );
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(key, context.previous);
    },
  });
}

// ---- Administration ---------------------------------------------------------------------

const REFRESH_MS = 30_000;

export const useMetricsOverview = () =>
  useQuery({
    queryKey: queryKeys.admin.overview,
    queryFn: endpoints.getMetricsOverview,
    refetchInterval: REFRESH_MS,
  });

export const useRequestsChart = (days = 7) =>
  useQuery({
    queryKey: queryKeys.admin.requestsChart(days),
    queryFn: () => endpoints.getRequestsChart(days),
    refetchInterval: REFRESH_MS,
  });

export const useRecentRequests = (limit = 10) =>
  useQuery({
    queryKey: queryKeys.admin.recent(limit),
    queryFn: () => endpoints.getRecentRequests(limit),
    refetchInterval: REFRESH_MS,
  });

export const useRequestDetails = (limit = 50) =>
  useQuery({
    queryKey: queryKeys.admin.requests(limit),
    queryFn: () => endpoints.getRequestDetails(limit),
  });

export const useLatencyComponents = () =>
  useQuery({ queryKey: queryKeys.admin.latencyComponents, queryFn: endpoints.getLatencyComponents });

export const useLatencyTrend = (days = 7) =>
  useQuery({
    queryKey: queryKeys.admin.latencyTrend(days),
    queryFn: () => endpoints.getLatencyTrend(days),
  });

export const useErrorDistribution = () =>
  useQuery({ queryKey: queryKeys.admin.errors, queryFn: endpoints.getErrorDistribution });

export const useSystemStatus = () =>
  useQuery({
    queryKey: queryKeys.admin.status,
    queryFn: endpoints.getSystemStatus,
    refetchInterval: REFRESH_MS,
  });
