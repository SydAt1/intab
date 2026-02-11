/**
 * Auth module for handling client-side authentication
 */
const Auth = {
    // API Endpoints
    endpoints: {
        login: '/login',
        register: '/register',
        me: '/me'
    },

    /**
     * Set authentication data after successful login
     * @param {string} token - Access token
     * @param {string} sessionId - Session ID
     * @param {object} user - User object
     */
    setAuth: (token, sessionId, user) => {
        localStorage.setItem('access_token', token);
        localStorage.setItem('session_id', sessionId);
        if (user) {
            localStorage.setItem('user_data', JSON.stringify(user));
        }
    },

    /**
     * Clear all authentication data
     */
    clearAuth: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('session_id');
        localStorage.removeItem('user_data');
    },

    /**
     * Check if user is authenticated locally
     * @returns {boolean} True if token exists
     */
    isAuthenticated: () => {
        return !!localStorage.getItem('access_token');
    },

    /**
     * Get the current access token
     * @returns {string|null} Access token or null
     */
    getToken: () => {
        return localStorage.getItem('access_token');
    },

    /**
     * Get stored user data
     * @returns {object|null} User data object or null
     */
    getUser: () => {
        const userData = localStorage.getItem('user_data');
        try {
            return userData ? JSON.parse(userData) : null;
        } catch (e) {
            return null;
        }
    },

    /**
     * Verify authentication with the server
     * Redirects to login if invalid
     * @param {boolean} redirectIfInvalid - Whether to redirect to login if auth fails
     * @returns {Promise<object|null>} User data if valid, null otherwise
     */
    checkLogin: async (redirectIfInvalid = true) => {
        const token = Auth.getToken();

        if (!token) {
            if (redirectIfInvalid) {
                // Store current URL to redirect back after login
                sessionStorage.setItem('redirect_after_login', window.location.pathname);
                window.location.href = '/login.html';
            }
            return null;
        }

        try {
            const response = await fetch(Auth.endpoints.me, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    Auth.clearAuth();
                    if (redirectIfInvalid) {
                        sessionStorage.setItem('redirect_after_login', window.location.pathname);
                        window.location.href = '/login.html';
                    }
                }
                return null;
            }

            const user = await response.json();
            // Update stored user data
            localStorage.setItem('user_data', JSON.stringify(user));
            return user;

        } catch (error) {
            console.error('Auth check failed:', error);
            // Don't clear auth on network error, but maybe warn user
            return null;
        }
    },

    /**
     * Enforce login on a page
     * Call this at the start of scripts for protected pages
     */
    requireLogin: () => {
        Auth.checkLogin(true);
    },

    /**
     * Logout the user
     */
    logout: () => {
        Auth.clearAuth();
        window.location.href = '/login.html';
    }
};

// Expose Auth globally
window.Auth = Auth;
