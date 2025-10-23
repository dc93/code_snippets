// Media Automation Dashboard JavaScript

// Trigger monitoring check
function triggerMonitor() {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Checking...';

    fetch('/api/monitor/check', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const result = data.result;
                showNotification(
                    'success',
                    `Checked ${result.checked} shows. Found ${result.new_episodes} new episodes.`
                );
                setTimeout(() => location.reload(), 2000);
            } else {
                showNotification('danger', 'Error checking for episodes');
            }
        })
        .catch(error => {
            showNotification('danger', 'Error: ' + error);
        })
        .finally(() => {
            btn.disabled = false;
            btn.innerHTML = originalText;
        });
}

// Show notification
function showNotification(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const container = document.querySelector('main.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }
}

// Auto-refresh stats every 30 seconds
let statsRefreshInterval;
function startStatsRefresh() {
    if (document.querySelector('[data-stats]')) {
        statsRefreshInterval = setInterval(refreshStats, 30000);
    }
}

function refreshStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update stats on page if elements exist
            const showsTotal = document.querySelector('[data-stat="shows-total"]');
            const queueTotal = document.querySelector('[data-stat="queue-total"]');

            if (showsTotal) showsTotal.textContent = data.shows.total;
            if (queueTotal) queueTotal.textContent = data.queue.total;
        })
        .catch(error => console.error('Error refreshing stats:', error));
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Start stats refresh if on dashboard
    startStatsRefresh();

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (statsRefreshInterval) {
        clearInterval(statsRefreshInterval);
    }
});

// Format file sizes
function formatFileSize(bytes) {
    if (!bytes) return 'N/A';

    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

// Format duration
function formatDuration(seconds) {
    if (!seconds) return 'N/A';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}
