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
    { href: '/static/taplist.html', icon: 'beer', label: 'Taps', match: ['taplist'] },
    { href: '/static/automation.html', icon: 'bot', label: 'Automation', match: ['automation'] },
    { href: '/static/help.html', icon: 'circle-help', label: 'Help', match: ['help'] }
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
        `<a href="${p.href}" class="bb-nav-link${isActivePage(p) ? ' active' : ''}" title="${p.label}">
            <i data-lucide="${p.icon}"></i>
        </a>`
    ).join('');

    const statusHtml = showStatus ? `
        <div class="bb-status-indicators">
            <span id="piTemp" class="bb-status-item"><i data-lucide="cpu"></i> <span>--°C</span></span>
            <span id="rssiIndicator" class="bb-status-item"><i data-lucide="signal"></i></span>
            <span id="lastSync" class="bb-status-item">--:--</span>
            <span id="connectionDot" class="bb-status-dot offline"></span>
        </div>
    ` : '';

    return `
    <header class="bb-header">
        <a href="/" class="bb-header-brand">
            <i data-lucide="beer"></i>
            <h1>Brew Brain</h1>
        </a>
        <div class="bb-header-right">
            <nav class="bb-header-nav">${navLinks}</nav>
            ${statusHtml}
        </div>
    </header>
    `;
}

function renderMobileNav() {
    const items = NAV_PAGES.map(p =>
        `<a href="${p.href}" class="bb-mobile-nav-item${isActivePage(p) ? ' active' : ''}">
            <i data-lucide="${p.icon}"></i>
            <span>${p.label}</span>
        </a>`
    ).join('');

    return `<nav class="bb-mobile-nav">${items}</nav>`;
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
    if (hasNav || hasMobile) {
        // Check for data attribute for status
        const showStatus = hasNav && hasNav.dataset.showStatus === 'true';
        initNav({ showStatus });
    }
});
