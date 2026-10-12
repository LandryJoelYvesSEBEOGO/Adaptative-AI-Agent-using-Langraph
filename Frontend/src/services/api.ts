/**
 * Client API pour le système RAG
 * 
 * Utilise le client HTTP amélioré avec gestion du timeout, des erreurs et des tokens
 */

import { apiRequest, TokenManager } from './apiClient';
import { ApiError } from './apiError';

// ============================================================================
// INTERFACES
// ============================================================================

export interface LoginResponse {
  success: boolean;
  token?: string;
  user?: {
    id: string;
    email: string;
    name: string;
    role: string;
  };
  error?: string;
}

export interface ChatQueryResponse {
  response: string;
  citations: Array<{
    id: number;
    source: string;
    excerpt: string;
    metadata?: Record<string, any>;
  }>;
  conversation_id: string;
  latency?: number;
  success: boolean;
  error?: string;
}

export interface Conversation {
  id: string;
  title?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageDTO {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Array<{
    id: number;
    source: string;
    excerpt: string;
    metadata?: Record<string, any>;
  }>;
  created_at: string;
}

export interface MetricOverview {
  total_requests: number;
  requests_today: number;
  success_rate: number;
  average_latency: number;
  error_count: number;
}

export interface RequestDataPoint {
  date: string;
  requests: number;
  success: number;
  errors: number;
}

export interface RequestDetail {
  id: string;
  timestamp: string;
  user: string;
  question: string;
  status: string;
  latency: number;
  docs_count: number;
  quality: number;
}

export interface LatencyComponentStat {
  name: string;
  avg: number;
  p95: number;
  p99: number;
}

export interface LatencyTrendPoint {
  date: string;
  endToEnd: number;
  retrieval: number;
  generation: number;
}

export interface RecentRequest {
  id: string;
  timestamp: string;
  user: string;
  question: string;
  status: string;
  latency: number;
}

export interface ErrorDistribution {
  timeout: number;
  llm_error: number;
  retrieval: number;
  web_search: number;
  other: number;
}

export interface SystemStatus {
  rag_pipeline: string;
  vector_db: string;
  llm_status: string;
  uptime_percentage: number;
}

// ============================================================================
// CLASSE API CLIENT
// ============================================================================

class ApiClient {
  /**
   * Définit le token d'authentification
   */
  setToken(token: string | null): void {
    if (token) {
      TokenManager.setTokens(token);
    } else {
      TokenManager.clearTokens();
    }
  }

  /**
   * Récupère le token actuel
   */
  getToken(): string | null {
    return TokenManager.getAccessToken();
  }

  // ============================================================================
  // AUTHENTIFICATION
  // ============================================================================

  /**
   * Connexion d'un utilisateur
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    try {
      const response = await apiRequest<LoginResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
        skipAuth: true, // Login ne nécessite pas d'auth
        timeout: 10000, // 10 secondes pour le login
      });

      // Sauvegarder le token si la connexion réussit
      if (response.success && response.token) {
        this.setToken(response.token);
      }

      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        error instanceof Error ? error.message : 'Erreur lors de la connexion'
      );
    }
  }

  /**
   * Inscription d'un nouvel utilisateur
   */
  async register(
    email: string,
    password: string,
    name: string,
    role: 'admin' | 'user' = 'user'
  ): Promise<LoginResponse> {
    try {
      const response = await apiRequest<LoginResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          password,
          name: name.trim(),
          role,
        }),
        skipAuth: true, // Register ne nécessite pas d'auth
        timeout: 10000,
      });

      // Sauvegarder le token si l'inscription réussit
      if (response.success && response.token) {
        this.setToken(response.token);
      }

      return response;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        error instanceof Error ? error.message : 'Erreur lors de l\'inscription'
      );
    }
  }

  /**
   * Déconnexion
   */
  async logout(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await apiRequest<{ success: boolean; message: string }>(
        '/auth/logout',
        {
          method: 'POST',
          timeout: 5000,
        }
      );
      return response;
    } catch (error) {
      // Ignorer les erreurs de logout, nettoyer quand même
      throw error;
    } finally {
      // Toujours nettoyer le token
      this.setToken(null);
    }
  }

  // ============================================================================
  // CHAT
  // ============================================================================

  /**
   * Crée une nouvelle conversation
   */
  async createConversation(title?: string): Promise<Conversation> {
    return apiRequest<Conversation>('/chat/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  }

  /**
   * Liste les conversations de l'utilisateur
   */
  async listConversations(): Promise<Conversation[]> {
    return apiRequest<Conversation[]>('/chat/conversations', {
      method: 'GET',
    });
  }

  /**
   * Liste les messages d'une conversation
   */
  async listMessages(conversationId: string): Promise<MessageDTO[]> {
    return apiRequest<MessageDTO[]>(`/chat/conversations/${conversationId}/messages`, {
      method: 'GET',
    });
  }

  /**
   * Requête RAG en mode normal (non-streaming)
   */
  async queryRAG(
    question: string,
    conversationId?: string,
    options?: { timeout?: number }
  ): Promise<ChatQueryResponse> {
    return apiRequest<ChatQueryResponse>('/chat/query', {
      method: 'POST',
      body: JSON.stringify({
        question,
        conversation_id: conversationId,
      }),
      timeout: options?.timeout || 60000, // 60 secondes par défaut pour RAG
    });
  }

  /**
   * Requête RAG en mode streaming (Server-Sent Events)
   */
  async queryRAGStream(
    question: string,
    conversationId: string | undefined,
    onChunk: (chunk: string) => void,
    options?: { timeout?: number; onError?: (error: Error) => void; onCitations?: (citations: ChatQueryResponse["citations"]) => void }
  ): Promise<void> {
    const token = this.getToken();
    const url = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'}/chat/query/stream`;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Créer un contrôleur d'abandon pour le timeout
    const controller = new AbortController();
    const timeout = options?.timeout || 120000; // 2 minutes pour le streaming
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          question,
          conversation_id: conversationId,
        }),
        signal: controller.signal,
        credentials: 'include',
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage;
        } catch {
          // Ignorer
        }
        throw new ApiError(errorMessage, response.status, response.statusText);
      }

      // Vérifier que c'est bien du streaming SSE
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('event-stream') && !contentType.includes('text/')) {
        throw new ApiError('Réponse inattendue: le serveur ne renvoie pas de streaming');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new ApiError('Impossible de lire le flux de réponse');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Garder la dernière ligne incomplète dans le buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            
            if (data === '[DONE]') {
              return;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.chunk) {
                onChunk(parsed.chunk);
              }
              if (parsed.citations && options?.onCitations) {
                options.onCitations(parsed.citations);
              }
            } catch (e) {
              // Ignorer les erreurs de parsing pour les chunks individuels
              if (options?.onError && e instanceof Error) {
                options.onError(e);
              }
            }
          }
        }
      }

      // Traiter le buffer restant
      if (buffer.trim()) {
        if (buffer.startsWith('data: ')) {
          const data = buffer.slice(6).trim();
          if (data !== '[DONE]') {
            try {
              const parsed = JSON.parse(data);
              if (parsed.chunk) {
                onChunk(parsed.chunk);
              }
              if (parsed.citations && options?.onCitations) {
                options.onCitations(parsed.citations);
              }
            } catch (e) {
              // Ignorer
            }
          }
        }
      }
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof ApiError) {
        throw error;
      }

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new ApiError('La requête de streaming a expiré.', 408);
        }
        throw new ApiError(`Erreur de streaming: ${error.message}`);
      }

      throw new ApiError('Erreur inattendue lors du streaming');
    }
  }

  /**
   * Soumettre un feedback (thumbs up/down)
   */
  async submitFeedback(
    messageId: string,
    feedbackType: 'thumbs_up' | 'thumbs_down',
    comment?: string
  ): Promise<{ success: boolean; message: string; message_id: string; feedback_type: string }> {
    return apiRequest('/chat/feedback', {
      method: 'POST',
      body: JSON.stringify({
        message_id: messageId,
        feedback_type: feedbackType,
        comment,
      }),
      timeout: 10000,
    });
  }

  // ============================================================================
  // ADMIN
  // ============================================================================

  /**
   * Récupère la vue d'ensemble des métriques
   */
  async getMetricsOverview(): Promise<MetricOverview> {
    return apiRequest<MetricOverview>('/admin/metrics/overview', {
      timeout: 10000,
    });
  }

  /**
   * Récupère les données pour le graphique des requêtes
   */
  async getMetricsRequests(days: number = 7): Promise<RequestDataPoint[]> {
    return apiRequest<RequestDataPoint[]>(`/admin/metrics/requests?days=${days}`, {
      timeout: 10000,
    });
  }

  /**
   * Récupère les requêtes récentes
   */
  async getRecentRequests(limit: number = 10): Promise<RecentRequest[]> {
    return apiRequest<RecentRequest[]>(`/admin/metrics/recent?limit=${limit}`, {
      timeout: 10000,
    });
  }

  /**
   * Récupère les requêtes détaillées (admin)
   */
  async getAdminRequests(limit: number = 50): Promise<RequestDetail[]> {
    return apiRequest<RequestDetail[]>(`/admin/requests?limit=${limit}`, {
      timeout: 10000,
    });
  }

  /**
   * Récupère les stats de latence par composant
   */
  async getLatencyComponents(): Promise<LatencyComponentStat[]> {
    return apiRequest<LatencyComponentStat[]>('/admin/metrics/latency/components', {
      timeout: 10000,
    });
  }

  /**
   * Récupère les tendances de latence
   */
  async getLatencyTrend(days: number = 7): Promise<LatencyTrendPoint[]> {
    return apiRequest<LatencyTrendPoint[]>(`/admin/metrics/latency/trend?days=${days}`, {
      timeout: 10000,
    });
  }

  /**
   * Récupère la répartition des erreurs
   */
  async getErrorDistribution(): Promise<ErrorDistribution> {
    return apiRequest<ErrorDistribution>('/admin/metrics/errors', {
      timeout: 10000,
    });
  }

  /**
   * Récupère le statut du système
   */
  async getSystemStatus(): Promise<SystemStatus> {
    return apiRequest<SystemStatus>('/admin/system/status', {
      timeout: 10000,
    });
  }
}

// ============================================================================
// EXPORT
// ============================================================================

export const apiClient = new ApiClient();

// Export des types pour utilisation externe
export type {
  LoginResponse,
  ChatQueryResponse,
  Conversation,
  MessageDTO,
  MetricOverview,
  RequestDataPoint,
  RequestDetail,
  LatencyComponentStat,
  LatencyTrendPoint,
  RecentRequest,
  ErrorDistribution,
  SystemStatus,
};

// Export de l'erreur API pour gestion d'erreurs
export { ApiError } from './apiError';
