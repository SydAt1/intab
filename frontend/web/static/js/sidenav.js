// Check authentication status
const currentPath = window.location.pathname;
const isPublicPage = (currentPath === '/' || currentPath === '/login' || currentPath === '/register');

if (!isPublicPage) {
    Auth.requireLogin();
}

// Load sidebar component if logged in, or if it's a protected page
Auth.checkLogin(false).then(user => {
    if (!user && isPublicPage) {
        // Not logged in and on a public page: don't load the sidebar.
        return;
    }

    fetch('/sidenav')
    .then(response => {
        if (!response.ok) {
            throw new Error(`Failed to load sidebar: ${response.status} ${response.statusText}`);
        }
        return response.text();
    })
    .then(html => {
        const container = document.getElementById('sidebar-container');
        if (container) {
            container.innerHTML = html;
        }

        // Highlight current page in navigation
        // Map pathname to page name for data-page matching
        const pathToPage = {
            '/': 'home',
            '/tablature': 'upload',
            '/fretboard': 'fretboard',
            '/chords': 'chords',
            '/quiz': 'quiz',
            '/output-editing': 'output',
            '/history': 'history'
        };
        const currentPage = pathToPage[currentPath] || '';

        document.querySelectorAll('.nav-item').forEach(link => {
            const page = link.getAttribute('data-page');
            if (page && page === currentPage) {
                link.classList.add('active');
            }
        });

        // Update sidebar with user info
        Auth.updateSidebar();
    })
    .catch(err => {
        console.error('Sidebar loading error:', err);
        const container = document.getElementById('sidebar-container');
        if (container) {
            container.innerHTML =
                `<div style="color:#f33; padding:2rem; text-align:center;">
                    Failed to load sidebar<br><small>${err.message}</small>
                </div>`;
        }
    });
});