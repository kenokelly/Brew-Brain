/**
 * Brew Brain - Shared Navigation Component
 * Include in all pages: <script src="/static/js/nav.js"></script>
 * 
 * Usage:
 *   1. Add <div id="bb-nav"></div> where you want the header
 *   2. Add <div id="bb-mobile-nav"></div> for mobile bottom nav
 *   3. Call initNav() after DOM ready
 */

const NAV_PAGES = [
    { href: '/', icon: 'layout-dashboard', label: 'Dashboard', match: ['/', 'index.html'] },
    { href: '/?tab=settings', icon: 'settings', label: 'Settings', match: ['settings'] },
    { href: 'http://192.168.155.226:1880/ui/', icon: 'external-link', label: 'TiltPi', match: ['tiltpi'] },
    { href: '/static/taplist.html', icon: 'beer', label: 'Tap List', match: ['taplist'] },
    { href: '/static/automation.html', icon: 'bot', label: 'Automation & Tools', match: ['automation'] },
    { href: '/static/help.html', icon: 'circle-help', label: 'Help & Documentation', match: ['help'] }
];

function isActivePage(page) {
    const path = window.location.pathname;
    return page.match.some(m => {
        if (m === '/') return path === '/' || path === '/index.html' || path.endsWith('/static/index.html');
        return path.includes(m);
    });
}

function renderHeader(showStatus = false) {
    const navLinks = NAV_PAGES.map(p =>
        `<a href="${p.href}" class="bb-nav-link${isActivePage(p) ? ' active' : ''}" aria-label="${p.label}" title="${p.label}">
            <i data-lucide="${p.icon}"></i>
        </a>`
    ).join('');

    const statusHtml = showStatus ? `
        <div class="bb-status-indicators" role="status" aria-label="System Status">
            <span id="piTemp" class="bb-status-item" aria-label="CPU Temperature"><i data-lucide="cpu"></i> <span>--°C</span></span>
            <span id="rssiIndicator" class="bb-status-item" aria-label="WiFi Strength"><i data-lucide="signal"></i></span>
            <span id="lastSync" class="bb-status-item" aria-label="Last Sync Time">--:--</span>
            <span id="connectionDot" class="bb-status-dot offline" aria-label="Connection Status"></span>
        </div>
    ` : '';

    return `
    <header class="bb-header" role="banner">
        <a href="/" class="bb-header-brand" aria-label="Brew Brain Dashboard">
            <i data-lucide="beer"></i>
            <h1>Brew Brain</h1>
        </a>
        <div class="bb-header-right">
            <nav class="bb-header-nav" aria-label="Main Navigation">${navLinks}</nav>
            ${statusHtml}
        </div>
    </header>
    `;
}

function renderMobileNav() {
    const items = NAV_PAGES.map(p =>
        `<a href="${p.href}" class="bb-mobile-nav-item${isActivePage(p) ? ' active' : ''}" aria-label="${p.label}">
            <i data-lucide="${p.icon}"></i>
            <span>${p.label}</span>
        </a>`
    ).join('');

    return `<nav class="bb-mobile-nav" aria-label="Mobile Navigation">${items}</nav>`;
}

// Toast System
function initToastSystem() {
    if (!document.getElementById('toast-container')) {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
}

window.showToast = function (message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return; // Should be inited

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.role = 'alert';

    // Icons based on type
    let iconName = 'info';
    if (type === 'success') iconName = 'check-circle';
    if (type === 'error') iconName = 'alert-circle';

    toast.innerHTML = `
        <div class="toast-icon"><i data-lucide="${iconName}"></i></div>
        <div class="toast-message">${message}</div>
    `;

    container.appendChild(toast);

    // Re-render icons for this toast
    if (typeof lucide !== 'undefined') {
        lucide.createIcons({
            root: toast
        });
    }

    // Remove after 3s
    setTimeout(() => {
        toast.style.animation = 'toast-out 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function initNav(options = {}) {
    const { showStatus = false } = options;

    // Inject header
    const navContainer = document.getElementById('bb-nav');
    if (navContainer) {
        navContainer.innerHTML = renderHeader(showStatus);
    }

    // Inject mobile nav
    const mobileNavContainer = document.getElementById('bb-mobile-nav');
    if (mobileNavContainer) {
        mobileNavContainer.innerHTML = renderMobileNav();
    }

    // Init Toast System
    initToastSystem();

    // Reinitialize Lucide icons for injected content
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // If showing status, start polling
    if (showStatus) {
        fetchNavStatus();
        setInterval(fetchNavStatus, 10000);
    }
}

async function fetchNavStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();

        // Update PI temp
        const piTemp = document.querySelector('#piTemp span');
        if (piTemp) piTemp.textContent = `${data.pi_temp || '--'}°C`;

        // Update RSSI indicator color
        const rssi = data.rssi;
        const rssiEl = document.getElementById('rssiIndicator');
        if (rssiEl) {
            rssiEl.className = 'bb-status-item ' + (
                rssi === null ? '' :
                    rssi > -60 ? 'text-green' :
                        rssi > -80 ? 'text-amber' : 'text-red'
            );
        }

        // Update last sync
        const lastSync = document.getElementById('lastSync');
        if (lastSync && data.last_sync) {
            const d = new Date(data.last_sync);
            lastSync.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }

        // Update connection dot
        const dot = document.getElementById('connectionDot');
        if (dot) {
            dot.className = 'bb-status-dot online';
        }
    } catch (e) {
        const dot = document.getElementById('connectionDot');
        if (dot) {
            dot.className = 'bb-status-dot offline';
        }
    }
}

// Auto-init if placeholders exist on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    // Only auto-init if explicit placeholders exist
    const hasNav = document.getElementById('bb-nav');
    const hasMobile = document.getElementById('bb-mobile-nav');
    // Also init if we just want global toasts available (e.g. valid pages)
    if (hasNav || hasMobile) {
        // Check for data attribute for status
        const showStatus = hasNav && hasNav.dataset.showStatus === 'true';
        initNav({ showStatus });
    } else {
        // Even if no nav, init toasts for other pages that might import nav.js but not use the header
        initToastSystem();
    }
});
