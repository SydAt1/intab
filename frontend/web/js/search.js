/**
 * search.js — Fetches and renders search results for tablature uploads.
 */

(function () {
    'use strict';

    const overlay = document.getElementById('loading-overlay');
    const searchForm = document.getElementById('search-form');
    const searchField = document.getElementById('search-field');
    const searchInfo = document.getElementById('search-info');

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

    function showOverlay() {
        if (overlay) overlay.classList.remove('hidden');
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

        const title = deleteModal.querySelector('.delete-modal-title');
        title.textContent = `Delete "${itemName}"?`;

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

    async function handleDelete(audioId, cardEl) {
        const nameEl = cardEl.querySelector('.card-name');
        const itemName = nameEl ? nameEl.textContent : 'this item';

        const confirmed = await showDeleteModal(itemName);
        if (!confirmed) return;

        const endpoint = `/api/audio/${audioId}`;

        try {
            const res = await fetch(endpoint, {
                method: 'DELETE',
                headers: authHeaders()
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || res.statusText);
            }

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
        const tabsGrid = document.getElementById('tabs-grid');
        const tabsCount = document.getElementById('tabs-count');
        if (tabsGrid && tabsCount) {
            const cards = tabsGrid.querySelectorAll('.history-card');
            const n = cards.length;
            tabsCount.textContent = n > 0 ? `${n} item${n !== 1 ? 's' : ''}` : '';
            if (n === 0 && !tabsGrid.querySelector('.empty-state')) {
                tabsGrid.innerHTML = '';
                tabsGrid.appendChild(buildEmptyState(
                    'No matching items found.',
                    'Clear search',
                    '#'
                ));
                // Add event listener to clear search on click
                tabsGrid.querySelector('a').addEventListener('click', (e) => {
                    e.preventDefault();
                    searchField.value = '';
                    tabsGrid.innerHTML = '';
                    searchInfo.style.display = 'block';
                    tabsCount.textContent = '';
                });
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

        const actionsDiv = card.querySelector('.card-top-actions');
        const deleteBtn = buildDeleteButton();
        actionsDiv.appendChild(deleteBtn);

        card.addEventListener('click', (e) => {
            if (e.target.closest('.card-delete-btn')) return;
            window.location.href = `/tablature?id=${encodeURIComponent(item.id)}`;
        });

        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            handleDelete(item.id, card);
        });

        return card;
    }

    function buildEmptyState(message, ctaText, ctaHref) {
        const div = document.createElement('div');
        div.className = 'empty-state';
        div.innerHTML = `
            <div class="empty-icon">🔍</div>
            <div class="empty-text">${message}</div>
            <a href="${ctaHref}" class="empty-cta">${ctaText}</a>
        `;
        return div;
    }

    // ── Search & Fetching ──

    async function performSearch(query) {
        showOverlay();
        try {
            const url = query ? `/api/audio/search?name=${encodeURIComponent(query)}` : `/api/audio/search`;
            const res = await fetch(url, {
                headers: authHeaders()
            });
            if (!res.ok) throw new Error(res.statusText);
            const data = await res.json();
            renderTabs(data);
        } catch (e) {
            console.error('Search failed:', e);
            renderTabs([]); // Render empty on fail
        } finally {
            hideOverlay();
        }
    }

    function renderTabs(items) {
        const grid = document.getElementById('tabs-grid');
        const countEl = document.getElementById('tabs-count');
        
        searchInfo.style.display = 'none'; // Hide info text
        
        if (!grid) return;

        grid.innerHTML = '';
        countEl.textContent = items.length > 0 ? `${items.length} item${items.length !== 1 ? 's' : ''}` : '';

        if (items.length === 0) {
            grid.appendChild(buildEmptyState(
                'No matching items found.',
                'Clear search',
                '#'
            ));
            grid.querySelector('a').addEventListener('click', (e) => {
                e.preventDefault();
                searchField.value = '';
                grid.innerHTML = '';
                searchInfo.style.display = 'block';
                countEl.textContent = '';
            });
            return;
        }

        items.forEach(item => grid.appendChild(buildTabCard(item)));
    }

    // ── Init ──

    function init() {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const q = searchField.value.trim();
            performSearch(q);
        });
    }

    // Wait for DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
