import RFB from '/desktop/novnc/core/rfb.js';

const el = id => document.getElementById(id);
const screen = el('screen');
const status = el('status');
const loginPanel = el('login-panel');
const loginForm = el('login-form');
const tokenInput = el('viewer-token');
const loginButton = el('login-button');
const logoutButton = el('logout');
const panel = el('profile-panel');
const profiles = el('profiles');
const panelError = el('panel-error');
let rfb = null;
let generation = null;
let checking = false;
let signingIn = false;
let busy = false;
let browser = {};
let loadedProfiles = false;

function disconnect() {
    const previous = rfb;
    rfb = null;
    generation = null;
    if (previous) previous.disconnect();
    screen.replaceChildren();
    screen.hidden = true;
}

function requireLogin(message) {
    disconnect();
    loginPanel.hidden = false;
    logoutButton.hidden = true;
    panel.hidden = true;
    loadedProfiles = false;
    browser = {};
    status.textContent = message;
}

function connect(nextGeneration, inputAllowed) {
    disconnect();
    generation = nextGeneration;
    screen.hidden = false;
    status.textContent = inputAllowed ? 'Connecting to your manual desktop…' : 'Connecting to the read-only display…';
    const url = new URL('/desktop/ws', window.location.href);
    url.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    url.searchParams.set('generation', nextGeneration);
    const client = new RFB(screen, url.href);
    rfb = client;
    client.viewOnly = !inputAllowed;
    client.scaleViewport = true;
    client.resizeSession = false;
    // No clipboard event listener: no automatic import/export of clipboard data.
    client.addEventListener('connect', () => {
        if (rfb === client) status.textContent = inputAllowed ? 'Your manual desktop — mouse and keyboard enabled' : 'Live display — read only';
    });
    client.addEventListener('disconnect', () => {
        if (rfb !== client) return;
        disconnect();
        status.textContent = 'Display disconnected. Checking session state…';
    });
    client.addEventListener('credentialsrequired', () => {
        if (rfb !== client) return;
        disconnect();
        status.textContent = 'Display backend unavailable. Contact the operator.';
    });
}

async function post(path, data = {}) {
    const response = await fetch(path, {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data),
    });
    const result = await response.json();
    if (response.status === 401) requireLogin('Viewer session expired. Sign in again.');
    if (!response.ok) throw new Error(result.detail || 'Request failed');
    return result;
}

function updateSelection() {
    el('profile-id').textContent = profiles.value ? `Selected profile ID: ${profiles.value}` : 'Select or create a profile.';
    updateControls();
}

async function refreshProfiles(selected = profiles.value) {
    const result = await post('/desktop/profiles/list');
    profiles.replaceChildren(new Option('Select a profile', ''));
    for (const profile of result.profiles) {
        // Option text is escaped by the DOM, never rendered as HTML.
        profiles.add(new Option(profile.label, profile.id));
    }
    profiles.value = selected;
    loadedProfiles = true;
    updateSelection();
}

function updateControls() {
    const idle = ['idle', 'error'].includes(browser.state);
    profiles.disabled = !idle || busy;
    el('open-browser').disabled = busy || !idle || !profiles.value;
    el('close-browser').disabled = busy || !browser.is_owner || !['opening', 'manual', 'closing'].includes(browser.state);
    el('pause-task').disabled = busy || !browser.can_pause;
    el('resume-task').disabled = busy || !browser.is_owner || browser.control !== 'manual';
    el('create-profile').disabled = busy || !idle;
    const seconds = browser.remaining_seconds;
    const countdown = seconds === null || seconds === undefined ? '' : ` — ${Math.ceil(seconds / 60)} min remaining`;
    el('session-state').textContent = `Session: ${browser.state || 'idle'}${browser.control ? ' / ' + browser.control : ''}${countdown}. Active profile: ${browser.profile_id || 'ephemeral / none'}. Standalone limit: ${Math.round((browser.manual_limit_seconds || 1800) / 60)} min; task manual limit: ${Math.round((browser.task_manual_limit_seconds || 600) / 60)} min.`;
    el('session-state').classList.toggle('expiring', seconds !== null && seconds !== undefined && seconds <= 60);
    if (browser.error) panelError.textContent = browser.error;
}

async function checkStatus() {
    if (checking || signingIn) return;
    checking = true;
    try {
        const response = await fetch('/desktop/status', {cache: 'no-store', credentials: 'same-origin'});
        if (response.status === 401) {
            requireLogin('Sign in to manage browser profiles and view the desktop.');
            return;
        }
        if (!response.ok) throw new Error('Viewer unavailable');
        const info = await response.json();
        loginPanel.hidden = true;
        logoutButton.hidden = false;
        panel.hidden = false;
        browser = info.browser || {};
        updateControls();
        if (!loadedProfiles) await refreshProfiles(browser.profile_id || '');
        if (info.state === 'live' && info.generation) {
            if (!rfb || generation !== info.generation) connect(info.generation, info.input_allowed === true);
            else rfb.viewOnly = info.input_allowed !== true;
        } else {
            disconnect();
            status.textContent = info.state === 'owner_only' ? 'Manual desktop is private to its owner.'
                : info.state === 'idle' ? 'Desktop idle. Select a profile and open Chrome, or submit an agent task.'
                : 'Desktop unavailable or starting. Waiting for backend readiness…';
        }
    } catch {
        disconnect();
        status.textContent = 'Cannot reach the viewer service. Retrying…';
    } finally {
        checking = false;
    }
}

async function action(path, payload, after) {
    if (busy) return;
    busy = true;
    panelError.textContent = '';
    updateControls();
    try {
        const result = await post(path, payload);
        if (after) await after(result);
    } catch (error) {
        panelError.textContent = error.message;
    } finally {
        busy = false;
        updateControls();
    }
    await checkStatus();
}

loginForm.addEventListener('submit', async event => {
    event.preventDefault();
    signingIn = true;
    loginButton.disabled = true;
    try {
        await post('/desktop/login', {token: tokenInput.value});
        tokenInput.value = '';
        loginPanel.hidden = true;
    } catch {
        tokenInput.value = '';
        requireLogin('Viewer sign-in failed. Check the token and configured origin.');
    } finally {
        signingIn = false;
        loginButton.disabled = false;
    }
    await checkStatus();
});

logoutButton.addEventListener('click', async () => {
    // Revoke frontend input immediately; backend retires interactive generation.
    if (rfb) rfb.viewOnly = true;
    try {
        await post('/desktop/logout');
        requireLogin('Signed out. Manual browser access closed.');
    } catch {
        status.textContent = 'Could not sign out. Retry; session expiry/disconnect grace closes manual access.';
    }
});
profiles.addEventListener('change', updateSelection);
el('profile-form').addEventListener('submit', event => {
    event.preventDefault();
    action('/desktop/profiles', {label: el('profile-label').value}, async result => {
        el('profile-label').value = '';
        await refreshProfiles(result.profile.id);
    });
});
el('open-browser').addEventListener('click', () => action('/desktop/browser/open', {browser_profile_id: profiles.value}));
el('close-browser').addEventListener('click', () => {
    if (rfb) rfb.viewOnly = true;
    action('/desktop/browser/close', {generation: browser.generation});
});
el('pause-task').addEventListener('click', () => action('/desktop/task/pause', {task_id: browser.task_id, generation: browser.generation}));
el('resume-task').addEventListener('click', () => {
    if (rfb) rfb.viewOnly = true;
    action('/desktop/task/resume', {task_id: browser.task_id, generation: browser.generation});
});
window.addEventListener('pagehide', disconnect);
setInterval(checkStatus, 3000);
checkStatus();
