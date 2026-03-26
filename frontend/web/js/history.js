/**
 * history.js — Fetches chord visualizations & tablature history,
 *              renders them as clickable cards.
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

    // ── Card Builders ──

    function buildChordCard(item) {
        const card = document.createElement('a');
        card.className = 'history-card';
        card.href = `/chords?id=${encodeURIComponent(item.id)}`;

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
                <span class="card-status status-done">Done</span>
            </div>
            ${chipsHTML}
            <div class="card-footer">
                <span class="card-date">${formatDate(item.uploaded_at)}</span>
                <span class="card-arrow">→</span>
            </div>
        `;
        return card;
    }

    function buildTabCard(item) {
        const card = document.createElement('a');
        card.className = 'history-card';
        card.href = `/tablature?id=${encodeURIComponent(item.id)}`;

        card.innerHTML = `
            <div class="card-top">
                <span class="card-name">${escapeHtml(item.tab_name || item.original_filename || 'Untitled')}</span>
                <span class="card-status ${statusClass(item.status)}">${statusLabel(item.status)}</span>
            </div>
            <div class="card-footer">
                <span class="card-date">${formatDate(item.uploaded_at)}</span>
                <span class="card-arrow">→</span>
            </div>
        `;
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

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
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
