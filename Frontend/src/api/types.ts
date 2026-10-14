import type { components } from "./schema";

type Schemas = components["schemas"];

export type User = Schemas["UserResponse"];
export type UserRole = User["role"];
export type Citation = Schemas["Citation"];
export type Conversation = Schemas["ConversationOut"];
export type Message = Schemas["MessageOut"];
export type FeedbackType = Schemas["FeedbackRequest"]["feedback_type"];
export type DocumentInfo = Schemas["DocumentOut"];
export type AdminUser = Schemas["AdminUser"];
export type MetricOverview = Schemas["MetricOverview"];
export type RequestDataPoint = Schemas["RequestDataPoint"];
export type RequestDetail = Schemas["RequestDetail"];
export type RecentRequest = Schemas["RecentRequest"];
export type ErrorDistribution = Schemas["ErrorDistribution"];
export type LatencyComponentStat = Schemas["LatencyComponentStat"];
export type LatencyTrendPoint = Schemas["LatencyTrendPoint"];
export type SystemStatus = Schemas["SystemStatus"];

/** Événements du flux SSE `POST /api/v1/chat/query/stream` (hors schéma OpenAPI). */
export type StreamEvent =
  | { type: "meta"; conversationId: string }
  | { type: "chunk"; text: string }
  | { type: "done"; citations: Citation[]; messageId: string | null; conversationId: string }
  | { type: "error"; message: string };
