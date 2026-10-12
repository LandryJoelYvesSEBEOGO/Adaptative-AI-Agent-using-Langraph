/**
 * Client HTTP amélioré pour les appels API
 * 
 * Gestion du timeout, des erreurs, des tokens JWT et du refresh automatique
 */

import { API_BASE_URL, API_TIMEOUT, STORAGE_KEYS } from './config';
import { ApiError } from './apiError';

/**
 * Options pour les requêtes API
 */
export interface ApiRequestOptions extends RequestInit {
  timeout?: number;
  skipAuth?: boolean; // Pour les endpoints publics (login, register)
  skipErrorHandling?: boolean; // Pour gérer les erreurs manuellement
}

/**
 * Gestion des tokens
 */
export class TokenManager {
  /**
   * Récupère le token d'accès depuis le localStorage
   */
  static getAccessToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  }

  /**
   * Récupère le refresh token depuis le localStorage
   */
  static getRefreshToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
  }

  /**
   * Sauvegarde les tokens dans le localStorage
   */
  static setTokens(accessToken: string, refreshToken?: string): void {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    if (refreshToken) {
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    }
  }

  /**
   * Supprime les tokens du localStorage
   */
  static clearTokens(): void {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
  }

  /**
   * Rafraîchit le token d'accès (pour usage futur)
   * Note: Le backend actuel ne supporte pas encore le refresh token
   */
  static async refreshAccessToken(): Promise<string | null> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      return null;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        this.clearTokens();
        return null;
      }

      const data = await response.json();
      this.setTokens(data.access_token, data.refresh_token);
      return data.access_token;
    } catch (error) {
      this.clearTokens();
      return null;
    }
  }
}

/**
 * Effectue une requête HTTP avec gestion du timeout, des erreurs et des tokens JWT
 */
export async function apiRequest<T>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const { 
    timeout = API_TIMEOUT, 
    skipAuth = false, 
    skipErrorHandling = false,
    ...fetchOptions 
  } = options;

  // Créer un contrôleur d'abandon pour le timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    // Construire l'URL complète
    const url = endpoint.startsWith('http') 
      ? endpoint 
      : `${API_BASE_URL}${endpoint}`;

    // Préparer les headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(fetchOptions.headers as Record<string, string> | undefined),
    };

    // Ajouter le token d'authentification si nécessaire
    if (!skipAuth) {
      const token = TokenManager.getAccessToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    // Effectuer la requête
    let response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers,
      credentials: 'include', // Pour CORS avec credentials
    });

    clearTimeout(timeoutId);

    // Si 401 (Unauthorized), essayer de rafraîchir le token
    if (response.status === 401 && !skipAuth) {
      const newToken = await TokenManager.refreshAccessToken();
      if (newToken) {
        // Réessayer la requête avec le nouveau token
        headers['Authorization'] = `Bearer ${newToken}`;
        
        // Recréer le contrôleur pour la nouvelle requête
        const retryController = new AbortController();
        const retryTimeoutId = setTimeout(() => retryController.abort(), timeout);
        
        try {
          response = await fetch(url, {
            ...fetchOptions,
            signal: retryController.signal,
            headers,
            credentials: 'include',
          });
          clearTimeout(retryTimeoutId);
        } catch (retryError) {
          clearTimeout(retryTimeoutId);
          throw retryError;
        }
      } else {
        // Si le refresh échoue, nettoyer et rediriger vers login
        TokenManager.clearTokens();
        if (typeof window !== 'undefined' && !skipErrorHandling) {
          // Déclencher un événement personnalisé pour que l'app puisse réagir
          window.dispatchEvent(new CustomEvent('auth:expired'));
        }
        if (!skipErrorHandling) {
          throw new ApiError('Session expirée. Veuillez vous reconnecter.', 401);
        }
      }
    }

    // Si la réponse n'est pas OK, lever une erreur
    if (!response.ok) {
      let errorData: unknown;
      let errorMessage = `Erreur API: ${response.statusText}`;
      
      try {
        const contentType = response.headers.get('content-type');
        if (contentType?.includes('application/json')) {
          errorData = await response.json();
        } else {
          const text = await response.text();
          errorData = text || null;
        }
      } catch (parseError) {
        errorData = null;
      }

      // Extraire le message d'erreur de manière plus détaillée
      if (errorData) {
        if (typeof errorData === 'object' && errorData !== null) {
          const data = errorData as Record<string, any>;
          // Prioriser les champs dans cet ordre
          errorMessage = data.detail || 
                        data.message || 
                        data.error || 
                        data.msg ||
                        (Array.isArray(data.errors) ? data.errors.join(', ') : null) ||
                        errorMessage;
        } else if (typeof errorData === 'string') {
          errorMessage = errorData || errorMessage;
        }
      }

      // Messages spécifiques selon le code de statut
      if (response.status === 400) {
        errorMessage = errorMessage.includes('Erreur API') 
          ? 'Requête invalide. Vérifiez les données envoyées.' 
          : errorMessage;
      } else if (response.status === 404) {
        errorMessage = 'La ressource demandée n\'a pas été trouvée.';
      } else if (response.status === 403) {
        errorMessage = 'Vous n\'avez pas les permissions nécessaires pour cette action.';
      } else if (response.status === 500) {
        errorMessage = 'Une erreur serveur s\'est produite. Veuillez réessayer plus tard.';
      } else if (response.status === 502 || response.status === 503) {
        errorMessage = 'Le serveur est temporairement indisponible. Veuillez réessayer plus tard.';
      }

      throw new ApiError(
        errorMessage,
        response.status,
        response.statusText,
        errorData
      );
    }

    // Gérer différents types de contenu
    const contentType = response.headers.get('content-type') || '';

    // Si la réponse est un blob (PDF, images, etc.), retourner directement
    if (
      contentType.includes('application/pdf') ||
      contentType.includes('application/octet-stream') ||
      contentType.includes('image/')
    ) {
      return (await response.blob()) as T;
    }

    // Si c'est du texte brut (comme pour le streaming SSE)
    if (contentType.includes('text/event-stream') || contentType.includes('text/plain')) {
      return (await response.text()) as T;
    }

    // Sinon, parser en JSON
    try {
      return await response.json();
    } catch (jsonError) {
      // Si le parsing JSON échoue, retourner le texte
      const text = await response.text();
      return text as unknown as T;
    }
  } catch (error) {
    clearTimeout(timeoutId);

    // Si c'est déjà une ApiError, la propager
    if (error instanceof ApiError) {
      throw error;
    }

    // Gérer les erreurs de réseau et timeout
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new ApiError(
          'La requête a expiré. Veuillez réessayer.',
          408
        );
      }

      // Erreur de connexion réseau
      if (error.message.includes('fetch') || error.message.includes('network')) {
        const baseURLWithoutPath = API_BASE_URL.replace('/api/v1', '');
        throw new ApiError(
          `Connexion au backend impossible.\n` +
          `Backend: ${baseURLWithoutPath}\n` +
          `Vérifiez que le serveur est démarré (python run_api.py)`,
          0, // 0 indique une erreur réseau
          'Network Error'
        );
      }

      throw new ApiError(`Erreur réseau: ${error.message}`);
    }

    throw new ApiError('Une erreur inattendue s\'est produite');
  }
}

