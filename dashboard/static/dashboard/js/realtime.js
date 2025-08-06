(function () {
  const rowsContainer = document.getElementById('realtimeRows');
  const statusPill = document.getElementById('wsStatus');
  const statusText = document.getElementById('wsStatusText');
  const MAX_ROWS = 500;

  if (!rowsContainer || !statusPill || !statusText) {
    // Not on realtime page
    return;
  }

  function setStatus(state, text) {
    statusPill.classList.remove('status-connected', 'status-reconnecting', 'status-disconnected');
    statusPill.classList.add(`status-${state}`);
    statusText.textContent = text;
  }

  function wsUrl() {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.host;
    return `${scheme}://${host}/ws/dashboard/realtime/`;
    // If behind a reverse proxy with script prefix, consider using window.location.pathname prefix
  }

  function severityBadge(sev) {
    const s = (sev || '').toLowerCase();
    const cls = s === 'critical' ? 'sev-critical' : s === 'warning' ? 'sev-warning' : 'sev-info';
    return `<span class="sev-badge ${cls}">${(sev || '').toUpperCase()}</span>`;
  }

  function prependRow(payload) {
    const tr = document.createElement('tr');
    const time = payload.time || '';
    const sev = payload.severity || '';
    const src = payload.source || '';
    const msg = payload.message || '';
    const env = payload.environment || '';
    const ack = payload.acknowledged === true;
    const groupId = payload.group_id || '';
    const instanceId = payload.id || '';
    const details = payload.detail_url || '#';

    tr.innerHTML = `
      <td class="truncate" title="${escapeHtml(time)}">${escapeHtml(time)}</td>
      <td>${severityBadge(sev)}</td>
      <td class="truncate" title="${escapeHtml(src)}">${escapeHtml(src)}</td>
      <td class="truncate" title="${escapeHtml(msg)}">${escapeHtml(msg)}</td>
      <td class="truncate" title="${escapeHtml(env)}">${escapeHtml(env)}</td>
      <td>${ack ? 'Yes' : 'No'}</td>
      <td>
        <div class="btn-group btn-group-sm" role="group">
          <a href="${details}" class="btn btn-outline-primary">Details</a>
          <button class="btn btn-outline-success" data-group-id="${groupId}" data-instance-id="${instanceId}" data-action="ack">Ack</button>
        </div>
      </td>
    `;
    rowsContainer.prepend(tr);

    // Trim
    while (rowsContainer.children.length > MAX_ROWS) {
      rowsContainer.removeChild(rowsContainer.lastElementChild);
    }
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll('&', '&')
      .replaceAll('<', '<')
      .replaceAll('>', '>')
      .replaceAll('"', '"')
      .replaceAll("'", '&#039;');
  }

  async function acknowledge(groupId, instanceId) {
    if (!groupId) return;
    try {
      // Adjust if an existing endpoint differs
      const url = `/api/alerts/${groupId}/acknowledge/`;
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ alert_instance_id: instanceId || null }),
        credentials: 'same-origin',
      });
      if (!resp.ok) throw new Error(`Ack failed: ${resp.status}`);
      if (window.toastr) toastr.success('Acknowledged');
    } catch (e) {
      console.error(e);
      if (window.toastr) toastr.error('Failed to acknowledge alert');
    }
  }

  function getCsrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  rowsContainer.addEventListener('click', function (e) {
    const btn = e.target.closest('button[data-action="ack"]');
    if (!btn) return;
    const groupId = btn.getAttribute('data-group-id');
    const instanceId = btn.getAttribute('data-instance-id');
    acknowledge(groupId, instanceId);
  });

  let socket = null;
  let retry = 0;
  const backoff = [1000, 2000, 5000, 10000, 15000, 30000];

  function connect() {
    try {
      socket = new WebSocket(wsUrl());
    } catch (e) {
      console.error('WebSocket init error', e);
      scheduleReconnect();
      return;
    }

    socket.onopen = function () {
      retry = 0;
      setStatus('connected', 'Connected');
    };

    socket.onmessage = function (evt) {
      try {
        const payload = JSON.parse(evt.data);
        // Only show unacknowledged items
        if (payload.acknowledged === true) return;
        prependRow(payload);
      } catch (e) {
        console.error('Invalid message payload', e);
      }
    };

    socket.onerror = function () {
      setStatus('reconnecting', 'Reconnecting...');
    };

    socket.onclose = function () {
      setStatus('disconnected', 'Disconnected');
      scheduleReconnect();
    };
  }

  function scheduleReconnect() {
    const delay = backoff[Math.min(retry, backoff.length - 1)];
    retry += 1;
    setStatus('reconnecting', `Reconnecting in ${Math.round(delay / 1000)}s...`);
    setTimeout(connect, delay);
  }

  // Start
  setStatus('reconnecting', 'Connecting...');
  connect();
})();