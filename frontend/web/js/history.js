/**
 * history.js — Fetches chord visualizations & tablature history,
 *              renders them as clickable cards with delete support.
 */

(function () {
    'use strict';

    const overlay = document.getElementById('loading-overlay');

    // ── Helpers ──

    function getToken() {
        return localStorage.getItem('access_token') || localStorage.getItem('token') || '';
    }

    function authHeaders() {
        return {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json'
        };
    }

    function formatDate(isoStr) {
        if (!isoStr) return '—';
        const d = new Date(isoStr);
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
    }

    function statusClass(status) {
        const map = {
            done: 'status-done',
            processing: 'status-processing',
            pending: 'status-pending',
            failed: 'status-failed'
        };
        return map[status] || 'status-pending';
    }

    function statusLabel(status) {
        const map = {
            done: 'Done',
            processing: 'Processing',
            pending: 'Pending',
            failed: 'Failed'
        };
        return map[status] || status;
    }

    function hideOverlay() {
        if (overlay) overlay.classList.add('hidden');
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ── Delete Confirmation Modal ──

    function createDeleteModal() {
        const modal = document.createElement('div');
        modal.id = 'delete-modal';
        modal.className = 'delete-modal';
        modal.innerHTML = `
            <div class="delete-modal-backdrop"></div>
            <div class="delete-modal-dialog">
                <div class="delete-modal-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                        stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        <line x1="10" y1="11" x2="10" y2="17"/>
                        <line x1="14" y1="11" x2="14" y2="17"/>
                    </svg>
                </div>
                <h3 class="delete-modal-title">Delete this item?</h3>
                <p class="delete-modal-desc">
                    This will permanently remove the audio file and all associated data.
                    This action cannot be undone.
                </p>
                <div class="delete-modal-actions">
                    <button class="delete-modal-btn cancel" id="delete-cancel">Cancel</button>
                    <button class="delete-modal-btn confirm" id="delete-confirm">
                        <span class="btn-text">Delete</span>
                        <span class="btn-spinner" style="display:none;"></span>
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }

    let deleteModal = null;
    let pendingDeleteResolve = null;

    function showDeleteModal(itemName) {
        if (!deleteModal) {
            deleteModal = createDeleteModal();

            deleteModal.querySelector('.delete-modal-backdrop').addEventListener('click', () => {
                closeDeleteModal(false);
            });
            deleteModal.querySelector('#delete-cancel').addEventListener('click', () => {
                closeDeleteModal(false);
            });
            deleteModal.querySelector('#delete-confirm').addEventListener('click', () => {
                closeDeleteModal(true);
            });
        }

        // Update title with item name
        const title = deleteModal.querySelector('.delete-modal-title');
        title.textContent = `Delete "${itemName}"?`;

        // Reset confirm button state
        const confirmBtn = deleteModal.querySelector('#delete-confirm');
        confirmBtn.querySelector('.btn-text').textContent = 'Delete';
        confirmBtn.querySelector('.btn-spinner').style.display = 'none';
        confirmBtn.disabled = false;

        deleteModal.classList.add('open');
        document.body.style.overflow = 'hidden';

        return new Promise(resolve => {
            pendingDeleteResolve = resolve;
        });
    }

    function closeDeleteModal(confirmed) {
        if (deleteModal) {
            deleteModal.classList.remove('open');
            document.body.style.overflow = '';
        }
        if (pendingDeleteResolve) {
            pendingDeleteResolve(confirmed);
            pendingDeleteResolve = null;
        }
    }

    // ── Delete Handler ──

    async function handleDelete(audioId, cardEl, type) {
        const nameEl = cardEl.querySelector('.card-name');
        const itemName = nameEl ? nameEl.textContent : 'this item';

        const confirmed = await showDeleteModal(itemName);
        if (!confirmed) return;

        // Determine API path based on type
        const endpoint = type === 'chord'
            ? `/api/chords/${audioId}`
            : `/api/audio/${audioId}`;

        try {
            const res = await fetch(endpoint, {
                method: 'DELETE',
                headers: authHeaders()
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || res.statusText);
            }

            // Animate card out
            cardEl.style.transition = 'opacity .35s, transform .35s';
            cardEl.style.opacity = '0';
            cardEl.style.transform = 'scale(0.92) translateY(8px)';

            setTimeout(() => {
                cardEl.remove();
                updateSectionCounts();
            }, 380);

        } catch (e) {
            console.error('Delete failed:', e);
            alert('Failed to delete: ' + e.message);
        }
    }

    function updateSectionCounts() {
        // Update chord count
        const chordsGrid = document.getElementById('chords-grid');
        const chordsCount = document.getElementById('chords-count');
        if (chordsGrid && chordsCount) {
            const cards = chordsGrid.querySelectorAll('.history-card');
            const n = cards.length;
            chordsCount.textContent = n > 0 ? `${n} item${n !== 1 ? 's' : ''}` : '';
            if (n === 0 && !chordsGrid.querySelector('.empty-state')) {
                chordsGrid.innerHTML = '';
                chordsGrid.appendChild(buildEmptyState(
                    'No chord visualizations yet.',
                    'Visualize your first chords',
                    '/chords'
                ));
            }
        }

        // Update tablature count
        const tabsGrid = document.getElementById('tabs-grid');
        const tabsCount = document.getElementById('tabs-count');
        if (tabsGrid && tabsCount) {
            const cards = tabsGrid.querySelectorAll('.history-card');
            const n = cards.length;
            tabsCount.textContent = n > 0 ? `${n} item${n !== 1 ? 's' : ''}` : '';
            if (n === 0 && !tabsGrid.querySelector('.empty-state')) {
                tabsGrid.innerHTML = '';
                tabsGrid.appendChild(buildEmptyState(
                    'No tablature transcriptions yet.',
                    'Transcribe your first audio',
                    '/tablature'
                ));
            }
        }
    }

    // ── Card Builders ──

    function buildDeleteButton() {
        const btn = document.createElement('button');
        btn.className = 'card-delete-btn';
        btn.setAttribute('aria-label', 'Delete');
        btn.setAttribute('title', 'Delete');
        btn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
        `;
        return btn;
    }

    function buildChordCard(item) {
        const card = document.createElement('div');
        card.className = 'history-card';
        card.dataset.audioId = item.id;

        // Extract unique chord names for preview chips
        const chordNames = [];
        if (item.chords && item.chords.length > 0) {
            const seen = new Set();
            for (const c of item.chords) {
                const name = c.chord || c.name || c;
                if (name && name !== 'N' && !seen.has(name)) {
                    seen.add(name);
                    chordNames.push(name);
                }
                if (chordNames.length >= 6) break;
            }
        }

        let chipsHTML = '';
        if (chordNames.length > 0) {
            const show = chordNames.slice(0, 5);
            const extra = chordNames.length > 5 ? chordNames.length - 5 : 0;
            chipsHTML = '<div class="card-chords">' +
                show.map(n => `<span class="chord-chip">${escapeHtml(n)}</span>`).join('') +
                (extra > 0 ? `<span class="chord-chip more">+${extra}</span>` : '') +
                '</div>';
        }

        card.innerHTML = `
            <div class="card-top">
                <span class="card-name">${escapeHtml(item.tab_name || item.original_filename || 'Untitled')}</span>
                <div class="card-top-actions">
                    <span class="card-status status-done">Done</span>
                </div>
            </div>
            ${chipsHTML}
            <div class="card-footer">
                <span class="card-date">${formatDate(item.uploaded_at)}</span>
                <span class="card-arrow">→</span>
            </div>
        `;

        // Add delete button to actions area
        const actionsDiv = card.querySelector('.card-top-actions');
        const deleteBtn = buildDeleteButton();
        actionsDiv.appendChild(deleteBtn);

        // Navigate on card click, but not on delete button
        card.addEventListener('click', (e) => {
            if (e.target.closest('.card-delete-btn')) return;
            window.location.href = `/chords?id=${encodeURIComponent(item.id)}`;
        });

        // Delete handler
        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            handleDelete(item.id, card, 'chord');
        });

        return card;
    }

    function buildTabCard(item) {
        const card = document.createElement('div');
        card.className = 'history-card';
        card.dataset.audioId = item.id;

        card.innerHTML = `
            <div class="card-top">
                <span class="card-name">${escapeHtml(item.tab_name || item.original_filename || 'Untitled')}</span>
                <div class="card-top-actions">
                    <span class="card-status ${statusClass(item.status)}">${statusLabel(item.status)}</span>
                </div>
            </div>
            <div class="card-footer">
                <span class="card-date">${formatDate(item.uploaded_at)}</span>
                <span class="card-arrow">→</span>
            </div>
        `;

        // Add delete button to actions area
        const actionsDiv = card.querySelector('.card-top-actions');
        const deleteBtn = buildDeleteButton();
        actionsDiv.appendChild(deleteBtn);

        // Navigate on card click, but not on delete button
        card.addEventListener('click', (e) => {
            if (e.target.closest('.card-delete-btn')) return;
            window.location.href = `/tablature?id=${encodeURIComponent(item.id)}`;
        });

        // Delete handler
        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            handleDelete(item.id, card, 'tab');
        });

        return card;
    }

    function buildEmptyState(message, ctaText, ctaHref) {
        const div = document.createElement('div');
        div.className = 'empty-state';
        div.innerHTML = `
            <div class="empty-icon">🎸</div>
            <div class="empty-text">${message}</div>
            <a href="${ctaHref}" class="empty-cta">${ctaText} →</a>
        `;
        return div;
    }

    // ── Data Fetching ──

    async function fetchChords() {
        try {
            const res = await fetch('/api/chords/my-chords', {
                headers: authHeaders()
            });
            if (!res.ok) throw new Error(res.statusText);
            return await res.json();
        } catch (e) {
            console.error('Failed to fetch chords history:', e);
            return [];
        }
    }

    async function fetchTabs() {
        try {
            const res = await fetch('/api/audio/my-uploads', {
                headers: authHeaders()
            });
            if (!res.ok) throw new Error(res.statusText);
            return await res.json();
        } catch (e) {
            console.error('Failed to fetch tablature history:', e);
            return [];
        }
    }

    // ── Render ──

    function renderChords(items) {
        const grid = document.getElementById('chords-grid');
        const countEl = document.getElementById('chords-count');
        if (!grid) return;

        grid.innerHTML = '';
        countEl.textContent = items.length > 0 ? `${items.length} item${items.length !== 1 ? 's' : ''}` : '';

        if (items.length === 0) {
            grid.appendChild(buildEmptyState(
                'No chord visualizations yet.',
                'Visualize your first chords',
                '/chords'
            ));
            return;
        }

        items.forEach(item => grid.appendChild(buildChordCard(item)));
    }

    function renderTabs(items) {
        const grid = document.getElementById('tabs-grid');
        const countEl = document.getElementById('tabs-count');
        if (!grid) return;

        grid.innerHTML = '';
        countEl.textContent = items.length > 0 ? `${items.length} item${items.length !== 1 ? 's' : ''}` : '';

        if (items.length === 0) {
            grid.appendChild(buildEmptyState(
                'No tablature transcriptions yet.',
                'Transcribe your first audio',
                '/tablature'
            ));
            return;
        }

        items.forEach(item => grid.appendChild(buildTabCard(item)));
    }

    // ── Init ──

    async function init() {
        // Fetch both in parallel
        const [chords, tabs] = await Promise.all([fetchChords(), fetchTabs()]);

        renderChords(chords);
        renderTabs(tabs);

        hideOverlay();
    }

    // Wait for DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
