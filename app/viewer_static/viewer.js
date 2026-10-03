import RFB from '/desktop/novnc/core/rfb.js';

const screen = document.getElementById('screen');
const status = document.getElementById('status');
const loginPanel = document.getElementById('login-panel');
const loginForm = document.getElementById('login-form');
const tokenInput = document.getElementById('viewer-token');
const loginButton = document.getElementById('login-button');
const logoutButton = document.getElementById('logout');
let rfb = null;
let generation = null;
let checking = false;
let signingIn = false;

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
    status.textContent = message;
}

function connect(nextGeneration) {
    disconnect();
    generation = nextGeneration;
    screen.hidden = false;
    status.textContent = 'Connecting to the read-only display…';
    const url = new URL('/desktop/ws', window.location.href);
    url.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const client = new RFB(screen, url.href);
    rfb = client;
    client.viewOnly = true;
    client.scaleViewport = true;
    client.resizeSession = false;
    client.addEventListener('connect', () => {
        if (rfb === client) status.textContent = 'Live display — read only';
    });
    client.addEventListener('disconnect', () => {
        if (rfb !== client) return;
        disconnect();
        status.textContent = 'Display disconnected. Checking for an active task…';
    });
    client.addEventListener('credentialsrequired', () => {
        if (rfb !== client) return;
        disconnect();
        status.textContent = 'Display backend unavailable. Contact the operator.';
    });
}

async function checkStatus() {
    if (checking || signingIn) return;
    checking = true;
    try {
        const response = await fetch('/desktop/status', {cache: 'no-store', credentials: 'same-origin'});
        if (response.status === 401) {
            requireLogin('Sign in to view the active task.');
            return;
        }
        if (!response.ok) {
            disconnect();
            status.textContent = 'Display viewer is unavailable.';
            return;
        }
        const info = await response.json();
        loginPanel.hidden = true;
        logoutButton.hidden = false;
        if (info.state === 'live') {
            if (!rfb || generation !== info.generation) connect(info.generation);
        } else {
            disconnect();
            status.textContent = info.state === 'idle'
                ? 'No active task. The display will reconnect when a task starts.'
                : 'A task is running, but its display viewer is unavailable.';
        }
    } catch {
        disconnect();
        status.textContent = 'Cannot reach the viewer service. Retrying…';
    } finally {
        checking = false;
    }
}

loginForm.addEventListener('submit', async event => {
    event.preventDefault();
    signingIn = true;
    loginButton.disabled = true;
    try {
        const response = await fetch('/desktop/login', {
            method: 'POST', credentials: 'same-origin', cache: 'no-store',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({token: tokenInput.value}),
        });
        tokenInput.value = '';
        if (!response.ok) {
            requireLogin(response.status === 429 ? 'Too many login attempts. Try again later.' : 'Viewer sign-in failed. Check the token and configured origin.');
            return;
        }
        loginPanel.hidden = true;
    } catch {
        tokenInput.value = '';
        requireLogin('Viewer sign-in could not connect to the service.');
    } finally {
        signingIn = false;
        loginButton.disabled = false;
    }
    await checkStatus();
});

logoutButton.addEventListener('click', async () => {
    try {
        const response = await fetch('/desktop/logout', {method: 'POST', credentials: 'same-origin', cache: 'no-store'});
        if (!response.ok) throw new Error('logout failed');
        requireLogin('Signed out.');
    } catch {
        status.textContent = 'Could not sign out. Retry or close this page; the session expires automatically.';
    }
});

window.addEventListener('pagehide', disconnect);
setInterval(checkStatus, 3000);
checkStatus();
