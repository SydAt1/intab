// CRITICAL: Require authentication before showing page
// This will redirect to /login.html if user is not authenticated
Auth.requireLogin();

// Load sidebar component
fetch('sidenav.html')
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
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    const pageName = currentPath.replace('.html', '');
    
    document.querySelectorAll('.nav-item').forEach(link => {
        const href = link.getAttribute('href');
        if (href) {
            const linkPage = href.replace('.html', '');
            if (linkPage === pageName) {
                link.classList.add('active');
            }
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