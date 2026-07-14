const mineflayer = require('mineflayer');
const http = require('http');
const net = require('net');

// ── Config from env ──────────────────────────────────────────────
const MC_HOST     = process.env.MINECRAFT_SERVER    || '127.0.0.1';
const MC_PORT     = parseInt(process.env.MINECRAFT_PORT || '25565');
const MC_USERNAME = process.env.MINECRAFT_USERNAME  || 'HermesBot';
const MC_AUTH     = (process.env.MINECRAFT_AUTH     || 'offline').toLowerCase();
const BRIDGE_PORT = parseInt(process.env.MINECRAFT_BRIDGE_PORT || '13000');

// ── State ────────────────────────────────────────────────────────
let bot = null;
const msgQueue = [];

// ── Bot ──────────────────────────────────────────────────────────
function connectBot() {
    if (bot) { try { bot.end(); } catch (_) {} }

    bot = mineflayer.createBot({
        host: MC_HOST, port: MC_PORT,
        username: MC_USERNAME, auth: MC_AUTH,
    });

    bot.on('login', () => {
        console.log(`[bridge] Logged in as ${bot.username}`);
        process.stdout.write(JSON.stringify({ type: 'status', connected: true, player: bot.username }) + '\n');
    });

    bot.on('chat', (username, message) => {
        if (username === bot.username) return;
        msgQueue.push({ player: username, message, time: Date.now() });
    });

    bot.on('kicked', (reason) => {
        console.log(`[bridge] Kicked: ${JSON.stringify(reason)}`);
        process.stdout.write(JSON.stringify({ type: 'status', connected: false, error: 'kicked' }) + '\n');
    });

    bot.on('end', () => {
        console.log('[bridge] Disconnected, reconnecting in 10s...');
        process.stdout.write(JSON.stringify({ type: 'status', connected: false }) + '\n');
        bot = null;
        setTimeout(connectBot, 10000);
    });

    bot.on('error', (err) => console.error('[bridge] Error:', err.message));

    // ── Idle wander ──────────────────────────────────────────────
    bot.on('spawn', () => {
        console.log('[bridge] Spawned in world, starting idle loop');
        startIdleLoop();
    });
}

let idleTimer = null;
function startIdleLoop() {
    if (idleTimer) clearInterval(idleTimer);
    idleTimer = setInterval(() => {
        if (!bot?.entity) return;
        const dirs = ['forward', 'back', 'left', 'right'];
        const d = dirs[Math.floor(Math.random() * dirs.length)];
        bot.setControlState(d, true);
        setTimeout(() => {
            if (!bot?.entity) return;
            bot.setControlState(d, false);
            bot.setControlState('jump', true);
            setTimeout(() => { if (bot?.entity) bot.setControlState('jump', false); }, 400);
        }, 1000 + Math.random() * 2000);
    }, 8000 + Math.random() * 7000);
}

// ── HTTP server ──────────────────────────────────────────────────
const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');

    if (req.method === 'GET' && req.url === '/health') {
        const online = bot?.entity ? Object.keys(bot.players) : [];
        res.end(JSON.stringify({
            status: bot?.entity ? 'connected' : 'connecting',
            players: online,
            username: bot?.username || MC_USERNAME,
        }));
        return;
    }

    if (req.method === 'GET' && req.url === '/messages') {
        const msgs = msgQueue.splice(0);
        res.end(JSON.stringify(msgs));
        return;
    }

    if (req.method === 'POST' && req.url === '/control') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            try {
                const { control, state } = JSON.parse(body);
                if (bot?.entity) bot.setControlState(control, state);
                res.end(JSON.stringify({ ok: true }));
            } catch (e) {
                res.end(JSON.stringify({ ok: false, error: e.message }));
            }
        });
        return;
    }

    if (req.method === 'POST' && req.url === '/send') {
        let body = '';
        req.on('data', c => body += c);
        req.on('end', () => {
            try {
                const { text, target } = JSON.parse(body);
                if (bot?.entity) {
                    if (target) bot.chat(`/tell ${target} ${text}`);
                    else bot.chat(text);
                }
                res.end(JSON.stringify({ ok: true }));
            } catch (e) {
                res.end(JSON.stringify({ ok: false, error: e.message }));
            }
        });
        return;
    }

    res.statusCode = 404;
    res.end(JSON.stringify({ error: 'not found' }));
});

server.listen(BRIDGE_PORT, () => {
    console.log(`[bridge] HTTP server on port ${BRIDGE_PORT}`);
    process.stdout.write(JSON.stringify({ type: 'bridge_ready', port: BRIDGE_PORT }) + '\n');
    connectBot();
});
