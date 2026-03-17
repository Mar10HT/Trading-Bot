let ws = null;

function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateDashboard(data);
    };

    ws.onclose = () => {
        updateStatusBadge(false);
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

function updateDashboard(data) {
    updateStatusBadge(data.running);

    if (!data.strategies || data.strategies.length === 0) return;

    // Update summary cards
    let totalPnl = 0, totalRealized = 0, totalFees = 0;
    data.strategies.forEach(s => {
        if (s.pnl) {
            totalPnl += s.pnl.total_pnl || 0;
            totalRealized += s.pnl.realized_pnl || 0;
            totalFees += s.pnl.total_fees || 0;
        }
    });

    setPnlValue('total-pnl', totalPnl);
    setPnlValue('realized-pnl', totalRealized);
    document.getElementById('total-fees').textContent = `$${totalFees.toFixed(4)}`;
    document.getElementById('active-pairs').textContent = data.strategies.length;

    // Update strategies
    updateStrategies(data.strategies);
}

function updateStatusBadge(running) {
    const badge = document.getElementById('status-badge');
    if (running) {
        badge.textContent = 'RUNNING';
        badge.className = 'px-2 py-0.5 rounded text-xs font-medium bg-green-900/30 text-green-400';
    } else {
        badge.textContent = 'OFFLINE';
        badge.className = 'px-2 py-0.5 rounded text-xs font-medium bg-gray-700 text-gray-400';
    }
}

function setPnlValue(elementId, value) {
    const el = document.getElementById(elementId);
    const sign = value >= 0 ? '+' : '';
    el.textContent = `${sign}$${value.toFixed(4)}`;
    el.className = `text-2xl font-semibold ${value >= 0 ? 'text-profit' : 'text-loss'}`;
}

function updateStrategies(strategies) {
    const container = document.getElementById('strategies-container');

    if (strategies.length === 0) {
        container.innerHTML = '<div class="text-muted text-center py-8">No active strategies</div>';
        return;
    }

    container.innerHTML = strategies.map(s => {
        const grid = s.grid || {};
        const pnl = s.pnl || {};
        const pnlColor = (pnl.total_pnl || 0) >= 0 ? 'text-profit' : 'text-loss';
        const pnlSign = (pnl.total_pnl || 0) >= 0 ? '+' : '';

        return `
            <div class="border border-border rounded-lg p-4 mb-3 last:mb-0">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full ${s.running ? 'bg-green-500 pulse-dot' : 'bg-gray-600'}"></span>
                        <span class="text-white font-medium">${s.pair}</span>
                        <span class="text-muted">$${(s.price || 0).toFixed(2)}</span>
                    </div>
                    <div class="${pnlColor} font-mono">
                        ${pnlSign}$${(pnl.total_pnl || 0).toFixed(4)}
                    </div>
                </div>

                <div class="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                    <div>
                        <div class="text-muted">Range</div>
                        <div class="text-gray-300">${grid.range || '-'}</div>
                    </div>
                    <div>
                        <div class="text-muted">Levels</div>
                        <div class="text-gray-300">${grid.num_levels || 0}</div>
                    </div>
                    <div>
                        <div class="text-muted">Active Orders</div>
                        <div class="text-gray-300">${s.active_orders || 0}</div>
                    </div>
                    <div>
                        <div class="text-muted">Cycles</div>
                        <div class="text-gray-300">${pnl.completed_cycles || 0}</div>
                    </div>
                    <div>
                        <div class="text-muted">Fees</div>
                        <div class="text-gray-300">$${(pnl.total_fees || 0).toFixed(4)}</div>
                    </div>
                </div>

                ${renderGridLevels(grid)}
            </div>
        `;
    }).join('');
}

function renderGridLevels(grid) {
    if (!grid || !grid.num_levels) return '';

    const buys = grid.active_buys || 0;
    const sells = grid.active_sells || 0;
    const total = grid.num_levels || 1;

    const bars = [];
    for (let i = 0; i < total; i++) {
        let cls = 'grid-level-empty';
        if (i < buys) cls = 'grid-level-buy';
        else if (i >= total - sells) cls = 'grid-level-sell';
        bars.push(`<div class="grid-level ${cls} flex-1"></div>`);
    }

    return `
        <div class="flex gap-1 mt-3">
            ${bars.join('')}
        </div>
        <div class="flex justify-between text-xs text-muted mt-1">
            <span>${buys} buys</span>
            <span>${sells} sells</span>
        </div>
    `;
}

async function fetchTrades() {
    try {
        const res = await fetch('/api/trades?limit=50');
        const data = await res.json();
        updateTrades(data.trades || []);
    } catch (e) {
        // Silently fail - will retry
    }
}

function updateTrades(trades) {
    const tbody = document.getElementById('trades-body');
    const countEl = document.getElementById('trade-count');
    countEl.textContent = `${trades.length} trades`;

    if (trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-8">No trades yet</td></tr>';
        return;
    }

    tbody.innerHTML = trades.map(t => {
        const sideColor = t.side === 'buy' ? 'text-profit' : 'text-loss';
        const time = new Date(t.timestamp).toLocaleTimeString();
        return `
            <tr class="border-b border-border/50 hover:bg-surface-hover">
                <td class="px-4 py-2 text-muted">${time}</td>
                <td class="px-4 py-2">${t.pair}</td>
                <td class="px-4 py-2 ${sideColor} uppercase font-medium">${t.side}</td>
                <td class="px-4 py-2 text-right">${t.price.toFixed(2)}</td>
                <td class="px-4 py-2 text-right">${t.amount.toFixed(8)}</td>
                <td class="px-4 py-2 text-right text-muted">${t.fee.toFixed(6)}</td>
                <td class="px-4 py-2 text-right">${t.grid_level}</td>
            </tr>
        `;
    }).join('');
}

async function stopBot() {
    if (!confirm('Stop all trading strategies?')) return;
    await fetch('/api/controls/stop', { method: 'POST' });
}

async function killBot() {
    if (!confirm('KILL SWITCH: Cancel all orders and stop immediately?')) return;
    await fetch('/api/controls/kill', { method: 'POST' });
}

// Initialize
connectWebSocket();
fetchTrades();
setInterval(fetchTrades, 10000);
