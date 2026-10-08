// Real-time status feed polling (15s interval) for Campus Placement Portal

document.addEventListener('DOMContentLoaded', function () {
    const feedIndicator = document.getElementById('status-feed-indicator');
    if (!feedIndicator) {
        return; // Only run on pages where student tracking is active
    }

    const lastSyncEl = document.getElementById('status-feed-last-sync');
    const FEED_URL = '/applications/status-feed/';
    const POLL_INTERVAL = 15000; // 15 seconds

    function formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    async function pollStatusFeed() {
        try {
            const response = await fetch(FEED_URL, {
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                console.warn('Status feed polling returned non-200:', response.status);
                return;
            }

            const data = await response.json();
            const now = new Date();

            if (lastSyncEl) {
                lastSyncEl.innerHTML = `<span class="live-pulse me-1"></span> Updated just now <span class="text-muted">(${formatTime(now)})</span>`;
            }

            if (data.applications && data.applications.length > 0) {
                data.applications.forEach(app => {
                    // 1. Update row on My Applications page if present
                    const rowEl = document.querySelector(`tr[data-app-id="${app.id}"]`);
                    if (rowEl) {
                        const badgeEl = rowEl.querySelector('.status-badge');
                        if (badgeEl) {
                            badgeEl.className = `badge ${app.badge_class} status-badge`;
                            badgeEl.textContent = app.status_display;
                        }
                        const updatedEl = rowEl.querySelector('.app-updated-at');
                        if (updatedEl) {
                            updatedEl.textContent = app.updated_at;
                        }
                    }

                    // 2. Update Application Detail page if viewing this app
                    const detailEl = document.querySelector(`[data-detail-app-id="${app.id}"]`);
                    if (detailEl) {
                        const detailBadgeEl = detailEl.querySelector('.detail-status-badge');
                        if (detailBadgeEl) {
                            detailBadgeEl.className = `badge ${app.badge_class} fs-6 detail-status-badge`;
                            detailBadgeEl.textContent = app.status_display;
                        }

                        // Withdraw button visibility
                        const withdrawBtn = document.getElementById('withdraw-button-container');
                        if (withdrawBtn && app.is_final) {
                            withdrawBtn.style.display = 'none';
                        }
                    }
                });
            }
        } catch (err) {
            console.error('Error fetching application status feed:', err);
        }
    }

    // Set initial sync time
    if (lastSyncEl) {
        lastSyncEl.innerHTML = `<span class="live-pulse me-1"></span> Live Sync Active <span class="text-muted">(${formatTime(new Date())})</span>`;
    }

    // Start recurring polling
    setInterval(pollStatusFeed, POLL_INTERVAL);
});
