// CRITICAL: Require authentication before showing page
// This will redirect to /login if user is not authenticated
Auth.requireLogin();

// Load sidebar component
fetch('/sidenav')
.then(response => {
    if (!response.ok) {
        throw new Error(`Failed to load sidebar: ${response.status} ${response.statusText}`);
    }
    return response.text();
})
.then(html => {
    const container = document.getElementById('sidebar-container');
    container.innerHTML = html;

    // Highlight current page in navigation
    const currentPath = window.location.pathname;
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
    document.getElementById('sidebar-container').innerHTML =
        `<div style="color:#f33; padding:2rem; text-align:center;">
            Failed to load sidebar<br><small>${err.message}</small>
        </div>`;
});