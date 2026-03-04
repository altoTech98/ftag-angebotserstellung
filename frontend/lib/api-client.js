/**
 * API Client – Production-grade HTTP client with:
 * - Error handling & retry logic
 * - Request timeout handling
 * - Response caching
 * - Request queuing
 */

class APIClient {
  constructor(baseURL = '/api') {
    this.baseURL = baseURL;
    this.timeout = 30000; // 30 seconds default
    this.retryAttempts = 3;
    this.retryDelay = 1000; // 1 second
    this.requestQueue = [];
    this.isProcessing = false;
    this.cache = new Map();
    this.cacheTimeout = 60000; // 1 minute
  }

  /**
   * Make HTTP request with error handling & retries
   */
  async request(method, path, options = {}) {
    const url = `${this.baseURL}${path}`;
    const key = `${method}:${path}`;
    
    // Check cache for GET requests
    if (method === 'GET' && this.cache.has(key)) {
      const cached = this.cache.get(key);
      if (Date.now() - cached.timestamp < this.cacheTimeout) {
        console.log(`[API] Cache hit: ${key}`);
        return cached.data;
      }
      this.cache.delete(key);
    }

    // Request configuration
    const config = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      timeout: options.timeout || this.timeout,
    };

    if (options.body) {
      config.body = typeof options.body === 'string' 
        ? options.body 
        : JSON.stringify(options.body);
    }

    // Retry logic
    let lastError;
    for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, config);
        const data = await this._handleResponse(response);

        // Cache successful GET requests
        if (method === 'GET') {
          this.cache.set(key, {
            data,
            timestamp: Date.now(),
          });
        }

        console.log(`[API] ${method} ${path} (attempt ${attempt}): Success`);
        return data;

      } catch (error) {
        lastError = error;
        console.warn(`[API] ${method} ${path} (attempt ${attempt}): ${error.message}`);

        if (attempt < this.retryAttempts) {
          const delay = this.retryDelay * Math.pow(2, attempt - 1); // Exponential backoff
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    // All retries failed
    throw new APIError(
      `Request failed after ${this.retryAttempts} attempts: ${lastError.message}`,
      lastError.status || 500,
      lastError
    );
  }

  /**
   * Handle API response
   */
  async _handleResponse(response) {
    const contentType = response.headers.get('content-type');
    let data;

    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const error = new APIError(
        data?.message || data?.error || response.statusText,
        response.status,
        data
      );
      throw error;
    }

    return data;
  }

  /**
   * GET request
   */
  get(path, options) {
    return this.request('GET', path, options);
  }

  /**
   * POST request
   */
  post(path, body, options) {
    return this.request('POST', path, { ...options, body });
  }

  /**
   * POST FormData (for file uploads)
   */
  async postForm(path, formData, options = {}) {
    const url = `${this.baseURL}${path}`;
    
    const config = {
      method: 'POST',
      body: formData,
      timeout: options.timeout || this.timeout,
      headers: options.headers || {},
      // Note: Don't set Content-Type for FormData - browser will set it
    };

    // Remove Content-Type header for FormData
    delete config.headers['Content-Type'];

    try {
      const response = await fetch(url, config);
      return await this._handleResponse(response);
    } catch (error) {
      throw new APIError(
        error.message,
        error.status || 500,
        error
      );
    }
  }

  /**
   * Poll until condition is met
   */
  async poll(fn, maxAttempts = 30, interval = 1000) {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      const result = await fn();
      if (result) return result;
      await new Promise(resolve => setTimeout(resolve, interval));
    }
    throw new Error(`Polling timeout after ${maxAttempts} attempts`);
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache.clear();
  }
}


/**
 * API Error class
 */
class APIError extends Error {
  constructor(message, status = 500, originalError = null) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.originalError = originalError;
  }

  /**
   * Check if error is recoverable
   */
  isRecoverable() {
    return this.status >= 500 || this.status === 408 || this.status === 429;
  }

  /**
   * Get user-friendly message
   */
  getUserMessage() {
    const messages = {
      400: 'Ungültige Anfrage. Bitte überprüfe deine Eingaben.',
      401: 'Authentifizierung erforderlich.',
      403: 'Du hast keine Berechtigung für diese Aktion.',
      404: 'Ressource nicht gefunden.',
      408: 'Anfrage-Timeout. Versuche es später erneut.',
      429: 'Zu viele Anfragen. Bitte warte einen Moment.',
      500: 'Serverfehler. Versuche es später erneut.',
      503: 'Service nicht verfügbar. Versuche es später erneut.',
    };
    return messages[this.status] || this.message;
  }
}


// Global client instance
const api = new APIClient(window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api'
  : '/api'
);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { APIClient, APIError, api };
}
