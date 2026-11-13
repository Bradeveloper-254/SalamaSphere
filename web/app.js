const API = localStorage.getItem('salamaApiBase') || 'http://127.0.0.1:8000';
const configs = {
  survivor: {
    label: 'Victim Dashboard',
    title: 'Your safety centre',
    tabs: [
      ['dashboard', '⌂', 'Dashboard'],
      ['sos', '!', 'SOS & incident logging'],
      ['vault', '▣', 'Evidence vault'],
      ['contacts', '♧', 'Trusted contacts'],
      ['navigation', '⌁', 'Victim navigation'],
    ],
  },
  authority: {
    label: 'Authority Dashboard',
    title: 'Assigned case operations',
    tabs: [
      ['dashboard', '⌂', 'Dashboard'],
      ['cases', '▤', 'Assigned cases'],
      ['alerts', '!', 'Urgent alerts'],
      ['review', '✓', 'Case-review status'],
      ['navigation', '⌁', 'Authority case details'],
    ],
  },
  admin: {
    label: 'Admin Dashboard',
    title: 'System operations',
    tabs: [
      ['dashboard', '⌂', 'Dashboard'],
      ['assignments', '⇢', 'Assign incidents'],
      ['health', '◉', 'System health'],
      ['users', '♙', 'User statistics'],
      ['devices', '⌁', 'Device status'],
      ['sync', '↕', 'Sync queue'],
      ['settings', '⚙', 'Navigation & settings'],
    ],
  },
};

const state = {
  role: 'survivor',
  tab: 'dashboard',
  data: { summary: {}, incidents: [] },
  contacts: [],
  assignments: [],
  notifications: [],
  location: null,
  locationError: '',
  notificationError: '',
  showNotifications: false,
};
const nav = document.querySelector('#navigation');
const screen = document.querySelector('#screen');
const notice = document.querySelector('#notice');
const notificationToggle = document.querySelector('#notification-toggle');
let activeIncidentAudio = null;
let activeIncidentAudioUrl = null;

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[character]));
}

function showNotice(message, success = false) {
  notice.textContent = message;
  notice.classList.toggle('success', success);
  notice.hidden = false;
}

function hideNotice() {
  notice.hidden = true;
  notice.classList.remove('success');
}

async function api(path, options = {}) {
  const token = localStorage.getItem('salamaToken');
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Token ${token}`;
  if (options.body) headers['Content-Type'] = 'application/json';

  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 204) return null;

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const detail = payload && typeof payload === 'object'
      ? payload.detail || Object.values(payload).flat().join(' ')
      : payload;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return payload;
}

function listFrom(payload) {
  return Array.isArray(payload) ? payload : payload.results || [];
}

function googleMapsUrl(latitude, longitude) {
  if (latitude == null || longitude == null
      || String(latitude).trim() === '' || String(longitude).trim() === '') {
    return null;
  }
  const lat = Number(latitude);
  const lon = Number(longitude);
  if (!Number.isFinite(lat) || lat < -90 || lat > 90
      || !Number.isFinite(lon) || lon < -180 || lon > 180) {
    return null;
  }
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${lat},${lon}`)}`;
}

function locationStatusMarkup(location) {
  const mapUrl = googleMapsUrl(location.latitude, location.longitude);
  const mapLink = mapUrl
    ? ` <a href="${esc(mapUrl)}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a>`
    : '';
  return `Location captured (accuracy +/- ${Math.round(location.accuracy)} m).${mapLink}`;
}

function incidentRows() {
  const incidents = state.data.incidents || [];
  if (!incidents.length) {
    return '<div class="empty">No records are available for this view.</div>';
  }

  return `<div class="table-wrap"><table><thead><tr>
    <th>Incident</th><th>Priority</th><th>Status</th><th>Source</th>
    <th>Location</th><th>Audio</th><th>Received</th>
  </tr></thead><tbody>${incidents.map((incident) => {
    const mapUrl = googleMapsUrl(incident.latitude, incident.longitude);
    const location = mapUrl
      ? `<a href="${esc(mapUrl)}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a>`
      : 'Unavailable';
    return `<tr>
      <td>${esc(String(incident.id).slice(0, 8))}...</td>
      <td><span class="badge ${incident.is_sos ? 'urgent' : esc(incident.threat_level)}">${incident.is_sos ? 'SOS' : esc(incident.threat_level)}</span></td>
      <td><span class="badge ${esc(incident.status)}">${esc(incident.status)}</span></td>
      <td>${esc(incident.source)}</td><td>${location}</td>
      <td>${incident.audio_available
    ? `<button class="text-action" data-play-audio="${esc(incident.id)}">Play recorded audio</button>`
    : 'Not uploaded yet'}</td>
      <td>${incident.received_at ? new Date(incident.received_at).toLocaleString() : '-'}</td>
    </tr>`;
  }).join('')}</tbody></table></div>`;
}

function renderNav() {
  const config = configs[state.role];
  document.querySelector('#section-label').textContent = config.label;
  document.querySelector('#screen-title').textContent = config.title;
  nav.innerHTML = config.tabs.map(([id, icon, label]) => `
    <button class="nav-tab ${id === state.tab ? 'active' : ''}" data-tab="${id}">
      <span class="nav-icon">${icon}</span><span class="nav-label">${label}</span>
    </button>`).join('');

  nav.querySelectorAll('button').forEach((button) => {
    button.onclick = () => {
      state.tab = button.dataset.tab;
      state.showNotifications = false;
      renderNav();
      renderScreen();
      if (state.role === 'survivor' && state.tab === 'sos') requestLocation();
      if (state.role === 'survivor' && state.tab === 'contacts') loadContacts();
      if (state.role === 'admin' && state.tab === 'assignments') loadAssignments();
    };
  });
}

function renderContacts() {
  const rows = state.contacts.length
    ? `<div class="table-wrap"><table><thead><tr><th>Name</th><th>Phone</th><th>Relationship</th><th>SOS alerts</th><th></th></tr></thead><tbody>
      ${state.contacts.map((contact) => `<tr>
        <td>${esc(contact.name)}</td><td>${esc(contact.phone_number)}</td>
        <td>${esc(contact.relationship || '-')}</td>
        <td>${contact.receive_sos_alerts ? 'Enabled' : 'Disabled'}</td>
        <td><button class="text-action" data-remove-contact="${contact.id}">Remove</button></td>
      </tr>`).join('')}
    </tbody></table></div>`
    : '<div class="empty">No trusted contacts saved yet.</div>';

  return `<div class="panel">
    <div class="section-head"><h2>Trusted contacts</h2><button class="action" id="refresh-contacts">Refresh</button></div>
    ${rows}
  </div>
  <div class="panel form-panel">
    <h2>Add a trusted contact</h2>
    <form id="contact-form" class="form-grid">
      <label>Name<input name="name" maxlength="100" required></label>
      <label>Phone (international format)<input name="phone_number" type="tel" placeholder="+2547XXXXXXXX" required></label>
      <label>Relationship<input name="relationship" maxlength="50"></label>
      <label class="check-field"><input name="receive_sos_alerts" type="checkbox" checked> Receive SOS alerts</label>
      <label class="check-field"><input name="confirm_sos_consent" type="checkbox"> I confirm this person agreed to receive SOS alerts</label>
      <div><button class="action" type="submit">Save contact</button></div>
    </form>
  </div>`;
}

function renderIncidentForm() {
  const locationText = state.location
    ? locationStatusMarkup(state.location)
    : state.locationError || 'Requesting location permission...';
  return `<div class="panel form-panel">
    <div class="section-head"><h2>Report an incident</h2><button class="action secondary" id="retry-location" type="button">Get my location</button></div>
    <p class="muted" id="location-status">${state.location ? locationText : esc(locationText)}</p>
    <form id="incident-form" class="form-grid">
      <label>What happened?<textarea name="description" rows="4" maxlength="5000" required></textarea></label>
      <label>Threat level<select name="threat_level"><option value="medium">Medium</option><option value="high">High</option><option value="low">Low</option></select></label>
      <label class="check-field"><input name="is_sos" type="checkbox"> This is an SOS emergency</label>
      <div><button class="action" type="submit">Create incident</button></div>
    </form>
  </div>`;
}

function renderAssignments() {
  if (!state.assignments.length) {
    return '<div class="panel"><div class="empty">There are no unassigned incidents.</div></div>';
  }
  return `<div class="panel"><div class="section-head"><h2>Unassigned incidents</h2><button class="action" id="refresh-assignments">Refresh</button></div>
    <div class="assignment-list">${state.assignments.map(({ incident, authorities, error }) => `
      <article class="assignment-item">
        <div><strong>${incident.is_sos ? 'SOS' : esc(incident.threat_level)} incident · ${esc(String(incident.id).slice(0, 8))}...</strong>
          <p>${esc(incident.description || 'No description provided.')}</p>
          <small>${googleMapsUrl(incident.latitude, incident.longitude)
    ? `Location: <a href="${esc(googleMapsUrl(incident.latitude, incident.longitude))}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a>`
    : 'Location unavailable; distance cannot be calculated.'}</small>
          <p>${incident.audio_available
    ? `<button class="text-action" data-play-audio="${esc(incident.id)}">Play recorded audio</button>`
    : 'Recorded audio is not uploaded yet.'}</p>
        </div>
        <form class="assignment-form" data-incident-id="${esc(incident.id)}">
          ${error ? `<p class="inline-error">${esc(error)}</p>` : ''}
          ${authorities.length
    ? `<label>Available authority<select class="assignment-select" required>
              <option value="">Select an authority</option>
              ${authorities.map((authority) => `<option value="${authority.id}">
                ${esc(authority.username)}${authority.distance_km == null ? '' : ` · ${esc(authority.distance_km)} km`}
              </option>`).join('')}
            </select></label><button class="action" type="submit">Assign case</button>`
    : '<p class="muted">No available authorities match this incident.</p>'}
        </form>
      </article>`).join('')}
  </div></div>`;
}

function renderNotificationPanel() {
  if (!state.showNotifications) return '';
  if (state.notificationError) {
    return `<div class="panel notification-panel"><div class="section-head"><h2>Notifications</h2><button class="text-action" id="close-notifications">Close</button></div><p class="inline-error">${esc(state.notificationError)}</p></div>`;
  }
  const items = state.notifications.length
    ? `<div class="notification-list">${state.notifications.map((item) => `
        <article class="notification-item ${item.is_read ? '' : 'unread'}">
          <div><strong>${esc(item.title)}</strong><p>${esc(item.message)}</p><small>${new Date(item.created_at).toLocaleString()}</small></div>
          ${item.is_read ? '' : `<button class="text-action" data-read-notification="${esc(item.id)}">Mark read</button>`}
        </article>`).join('')}</div>`
    : '<div class="empty">You have no notifications.</div>';
  return `<div class="panel notification-panel"><div class="section-head"><h2>Notifications</h2><button class="text-action" id="close-notifications">Close</button></div>${items}</div>`;
}

function renderScreen() {
  const summary = state.data.summary || {};
  const tabLabel = configs[state.role].tabs.find(([id]) => id === state.tab)?.[2] || '';

  if (state.role === 'survivor' && state.tab === 'contacts') {
    screen.innerHTML = renderContacts();
    bindContactForm();
  } else if (state.role === 'survivor' && state.tab === 'sos') {
    screen.innerHTML = renderIncidentForm();
    bindIncidentForm();
  } else if (state.role === 'admin' && state.tab === 'assignments') {
    screen.innerHTML = renderAssignments();
    bindAssignmentForms();
  } else if (state.tab === 'dashboard') {
    screen.innerHTML = `<div class="grid">
      <div class="card"><div class="metric-label">Total incidents</div><div class="metric">${summary.total || 0}</div></div>
      <div class="card"><div class="metric-label">Urgent / SOS</div><div class="metric coral">${summary.urgent || 0}</div></div>
      <div class="card"><div class="metric-label">Open cases</div><div class="metric teal">${summary.open || 0}</div></div>
      <div class="card"><div class="metric-label">Reviewed</div><div class="metric">${summary.reviewed || 0}</div></div>
    </div><div class="panel"><div class="section-head"><h2>Relevant incident records</h2></div>${incidentRows()}</div>`;
  } else {
    screen.innerHTML = `<div class="panel"><div class="section-head"><h2>${esc(tabLabel)}</h2><button class="action" id="refresh-dashboard">Refresh</button></div>
      <div class="feature-grid"><div class="card feature"><span class="feature-icon">${state.role === 'survivor' ? '▣' : state.role === 'authority' ? '✓' : '◉'}</span>
        <div><h3>${state.role === 'survivor' ? 'Protected records' : state.role === 'authority' ? 'Evidence integrity' : 'Operational controls'}</h3>
        <p>Role-specific tools, status and privacy controls are connected to the SalamaSphere API.</p></div></div></div>
      </div><div class="panel"><div class="section-head"><h2>Relevant incident records</h2></div>${incidentRows()}</div>`;
    document.querySelector('#refresh-dashboard').onclick = load;
  }

  screen.insertAdjacentHTML('beforeend', renderNotificationPanel());
  bindIncidentAudioButtons();
  bindNotificationPanel();
}

function bindIncidentAudioButtons() {
  screen.querySelectorAll('[data-play-audio]').forEach((button) => {
    button.onclick = async () => {
      button.disabled = true;
      try {
        const token = localStorage.getItem('salamaToken');
        const response = await fetch(
          `${API}/api/incidents/${encodeURIComponent(button.dataset.playAudio)}/audio/`,
          { headers: token ? { Authorization: `Token ${token}` } : {} },
        );
        if (!response.ok) {
          const detail = await response.text();
          throw new Error(detail || `Audio request failed (${response.status}).`);
        }

        if (activeIncidentAudio) activeIncidentAudio.pause();
        if (activeIncidentAudioUrl) URL.revokeObjectURL(activeIncidentAudioUrl);
        activeIncidentAudioUrl = URL.createObjectURL(await response.blob());
        activeIncidentAudio = new Audio(activeIncidentAudioUrl);
        activeIncidentAudio.onended = () => {
          URL.revokeObjectURL(activeIncidentAudioUrl);
          activeIncidentAudioUrl = null;
          activeIncidentAudio = null;
        };
        await activeIncidentAudio.play();
      } catch (error) {
        showNotice(`Could not play incident audio: ${error.message}`);
      } finally {
        button.disabled = false;
      }
    };
  });
  updateNotificationBadge();
}

function updateNotificationBadge() {
  const unread = state.notifications.filter((item) => !item.is_read).length;
  notificationToggle.innerHTML = `Notifications${unread ? `<span class="notification-count">${unread}</span>` : ''}`;
}

function bindNotificationPanel() {
  const closeButton = document.querySelector('#close-notifications');
  if (closeButton) closeButton.onclick = () => {
    state.showNotifications = false;
    renderScreen();
  };
  screen.querySelectorAll('[data-read-notification]').forEach((button) => {
    button.onclick = async () => {
      try {
        await api(`/api/notifications/${encodeURIComponent(button.dataset.readNotification)}/`, {
          method: 'PATCH',
          body: JSON.stringify({ is_read: true }),
        });
        const notification = state.notifications.find((item) => item.id === button.dataset.readNotification);
        if (notification) notification.is_read = true;
        renderScreen();
      } catch (error) {
        showNotice(`Could not update notification: ${error.message}`);
      }
    };
  });
}

async function loadNotifications() {
  try {
    state.notifications = listFrom(await api('/api/notifications/'));
    state.notificationError = '';
  } catch (error) {
    state.notificationError = error.message;
  }
  updateNotificationBadge();
  if (state.showNotifications) renderScreen();
}

async function loadContacts() {
  try {
    state.contacts = listFrom(await api('/api/trusted-contacts/'));
    renderScreen();
  } catch (error) {
    showNotice(`Could not load trusted contacts: ${error.message}`);
  }
}

function bindContactForm() {
  const form = document.querySelector('#contact-form');
  form.onsubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    try {
      await api('/api/trusted-contacts/', {
        method: 'POST',
        body: JSON.stringify({
          name: formData.get('name'),
          phone_number: formData.get('phone_number'),
          relationship: formData.get('relationship'),
          receive_sos_alerts: formData.has('receive_sos_alerts'),
          confirm_sos_consent: formData.has('confirm_sos_consent'),
        }),
      });
      showNotice('Trusted contact saved.', true);
      state.contacts = listFrom(await api('/api/trusted-contacts/'));
      renderScreen();
    } catch (error) {
      showNotice(`Could not save trusted contact: ${error.message}`);
    }
  };
  document.querySelector('#refresh-contacts').onclick = loadContacts;
  screen.querySelectorAll('[data-remove-contact]').forEach((button) => {
    button.onclick = async () => {
      if (!window.confirm('Remove this trusted contact?')) return;
      try {
        await api(`/api/trusted-contacts/${encodeURIComponent(button.dataset.removeContact)}/`, {
          method: 'DELETE',
        });
        state.contacts = state.contacts.filter((contact) => String(contact.id) !== button.dataset.removeContact);
        showNotice('Trusted contact removed.', true);
        renderScreen();
      } catch (error) {
        showNotice(`Could not remove trusted contact: ${error.message}`);
      }
    };
  });
}

function requestLocation() {
  state.location = null;
  const status = document.querySelector('#location-status');
  state.locationError = 'Requesting location permission...';
  if (status) status.textContent = state.locationError;
  getCurrentLocation().then((location) => {
    state.location = location;
    state.locationError = '';
    const locationStatus = document.querySelector('#location-status');
    if (locationStatus) {
      locationStatus.innerHTML = locationStatusMarkup(location);
    }
  }).catch((error) => {
    state.locationError = error.message;
    const locationStatus = document.querySelector('#location-status');
    if (locationStatus) locationStatus.textContent = state.locationError;
  });
}

function getCurrentLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('This browser does not support device location.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      }),
      (error) => reject(new Error(error.code === 1
        ? 'Location permission was denied. Allow location in browser settings and retry.'
        : 'Could not determine location. Check device location and retry.')),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  });
}

function bindIncidentForm() {
  document.querySelector('#retry-location').onclick = requestLocation;
  document.querySelector('#incident-form').onsubmit = async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    try {
      state.location = await getCurrentLocation();
      state.locationError = '';
    } catch (error) {
      state.location = null;
      state.locationError = error.message;
      const locationStatus = document.querySelector('#location-status');
      if (locationStatus) locationStatus.textContent = state.locationError;
      if (!window.confirm(`${error.message} Create this incident without location?`)) return;
    }
    const incident = {
      source: 'mobile',
      threat_level: formData.get('threat_level'),
      description: formData.get('description'),
      occurred_at: new Date().toISOString(),
      is_sos: formData.has('is_sos'),
    };
    if (state.location) {
      incident.latitude = Number(state.location.latitude.toFixed(6));
      incident.longitude = Number(state.location.longitude.toFixed(6));
      incident.location_accuracy_m = state.location.accuracy;
      incident.location_source = 'browser_geolocation';
    }
    try {
      await api('/api/incidents/', {
        method: 'POST',
        body: JSON.stringify(incident),
      });
      showNotice('Incident created successfully.', true);
      state.tab = 'dashboard';
      await load();
    } catch (error) {
      showNotice(`Could not create incident: ${error.message}`);
    }
  };
}

async function loadAssignments() {
  try {
    const incidents = listFrom(await api('/api/incidents/admin/unassigned/'));
    state.assignments = await Promise.all(incidents.map(async (incident) => {
      try {
        const query = new URLSearchParams({ incident_id: incident.id });
        const authorities = listFrom(await api(`/api/incidents/admin/assignments/available-authorities/?${query}`));
        return { incident, authorities, error: '' };
      } catch (error) {
        return { incident, authorities: [], error: error.message };
      }
    }));
    renderScreen();
  } catch (error) {
    state.assignments = [];
    showNotice(`Could not load unassigned incidents: ${error.message}`);
    renderScreen();
  }
}

function bindAssignmentForms() {
  const refresh = document.querySelector('#refresh-assignments');
  if (refresh) refresh.onclick = loadAssignments;
  screen.querySelectorAll('.assignment-form').forEach((form) => {
    form.onsubmit = async (event) => {
      event.preventDefault();
      const authorityId = form.querySelector('select')?.value;
      if (!authorityId) return;
      try {
        await api('/api/incidents/admin/assignments/', {
          method: 'POST',
          body: JSON.stringify({
            incident_id: form.dataset.incidentId,
            authority_id: Number(authorityId),
          }),
        });
        showNotice('Incident assigned successfully.', true);
        await loadAssignments();
        await loadNotifications();
      } catch (error) {
        showNotice(`Could not assign incident: ${error.message}`);
      }
    };
  });
}

async function load() {
  hideNotice();
  state.data = { summary: {}, incidents: [] };
  try {
    state.data = await api('/api/dashboard/overview/');
    renderNav();
    renderScreen();
    await loadNotifications();
  } catch (error) {
    showNotice(`Could not load dashboard data: ${error.message}`);
    renderNav();
    renderScreen();
  }
}

document.querySelector('#role').onchange = (event) => {
  state.role = event.target.value;
  state.tab = 'dashboard';
  state.showNotifications = false;
  load();
};
notificationToggle.onclick = () => {
  state.showNotifications = !state.showNotifications;
  if (state.showNotifications) loadNotifications();
  else renderScreen();
};
load();
