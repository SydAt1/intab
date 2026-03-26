/**
 * Auth module for handling client-side authentication
 */
const Auth = {
    // API Endpoints
    endpoints: {
        login: '/api/login',
        register: '/api/register',
        me: '/api/me'
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
        // Also set in sessionStorage for easy access by other scripts
        sessionStorage.setItem('session_id', sessionId);
        if (user) {
            localStorage.setItem('user_data', JSON.stringify(user));
            sessionStorage.setItem('username', user.username || '');
        }
    },

    /**
     * Clear all authentication data
     */
    clearAuth: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('session_id');
        localStorage.removeItem('user_data');
        sessionStorage.removeItem('session_id');
        sessionStorage.removeItem('username');
    },

    /**
     * Get the session ID
     */
    getSessionId: () => {
        return sessionStorage.getItem('session_id') || localStorage.getItem('session_id');
    },

    /**
     * Get the access token
     */
    getToken: () => {
        return localStorage.getItem('access_token');
    },

    /**
     * Verify authentication with the server
     * Redirects to login if invalid
     * @param {boolean} redirectIfInvalid - Whether to redirect to login if auth fails
     * @returns {Promise<object|null>} User data if valid, null otherwise
     */
    checkLogin: async (redirectIfInvalid = true) => {
        const token = Auth.getToken();
        const sessionId = Auth.getSessionId();

        if (!token && !sessionId) {
            if (redirectIfInvalid) {
                sessionStorage.setItem('redirect_after_login', window.location.pathname);
                window.location.href = '/login';
            }
            return null;
        }

        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            if (token) headers['Authorization'] = `Bearer ${token}`;
            if (sessionId) headers['X-Session-Id'] = sessionId;

            const response = await fetch(Auth.endpoints.me, { headers });

            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    Auth.clearAuth();
                    if (redirectIfInvalid) {
                        sessionStorage.setItem('redirect_after_login', window.location.pathname);
                        window.location.href = '/login';
                    }
                }
                return null;
            }

            const user = await response.json();
            localStorage.setItem('user_data', JSON.stringify(user));
            if (user.username) sessionStorage.setItem('username', user.username);
            return user;

        } catch (error) {
            console.error('Auth check failed:', error);
            return null;
        }
    },

    /**
     * Update the sidebar UI with user info and toggle login/logout button
     */
    updateSidebar: async () => {
        const userNameEl = document.getElementById('userName');
        const userIconEl = document.getElementById('userIcon');
        const userStatusEl = document.getElementById('userStatus');
        const authLink = document.getElementById('authLink');
        const authText = document.getElementById('authText');
        const authIcon = document.getElementById('authIcon');

        // Verify/update from server
        const user = await Auth.checkLogin(false);
        const isLoggedIn = !!user;

        if (!userNameEl) return; // Sidebar profile section not present

        if (isLoggedIn && user.username) {
            // Logged in state
            userNameEl.textContent = user.username;
            userIconEl.textContent = user.username.charAt(0).toUpperCase();
            userStatusEl.textContent = "Active";
            userStatusEl.style.color = "var(--spotify-green)";

            // Update auth button to "Log Out"
            if (authText && authIcon && authLink) {
                authText.textContent = "Log Out";
                authIcon.textContent = "🚪";
                authLink.removeAttribute('href');
                authLink.style.cursor = 'pointer';
                authLink.onclick = (e) => {
                    e.preventDefault();
                    Auth.logout();
                };
            }
        } else {
            // Guest state
            userNameEl.textContent = "Guest";
            userIconEl.textContent = "?";
            userStatusEl.textContent = "Visitor";
            userStatusEl.style.color = "#888";

            // Update auth button to "Login"
            if (authText && authIcon && authLink) {
                authText.textContent = "Login";
                authIcon.textContent = "🔑";
                authLink.href = "/login";
                authLink.onclick = null;
            }
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
    logout: async () => {
        const sessionId = Auth.getSessionId();

        // Clear frontend auth data
        Auth.clearAuth();

        // Call backend to invalidate session
        if (sessionId) {
            try {
                await fetch('/api/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Session-Id': sessionId
                    }
                });
            } catch (err) {
                console.warn("Backend logout failed (network error), but frontend is cleared.");
            }
        }

        // Redirect to home page
        window.location.href = '/';
    }
};

// Expose Auth globally
window.Auth = Auth;
