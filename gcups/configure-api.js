// Enables the GC UPS HTTP server and applies GCUPS_HTTP_PORT / GCUPS_PASSWORD
// to the app's settings document before the app starts.
//
// Runs on the app's own bundled Node runtime (ELECTRON_RUN_AS_NODE=1) and
// uses the PouchDB modules shipped inside app.asar, so the document is written
// exactly the way the app itself would write it.
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const GCUPS_HOME = process.env.GCUPS_HOME || '/opt/gcups';
const APP_MODULES = path.join(GCUPS_HOME, 'resources/app.asar/node_modules');
const PouchDB = require(path.join(APP_MODULES, 'pouchdb-core'));
PouchDB.plugin(require(path.join(APP_MODULES, 'pouchdb-adapter-leveldb')));

// From the app's settings document definition
// (main/process/fetcher/modules/settings/documents/settings.document.js).
const SETTINGS_DB = '/var/lib/gcups/db/gcups-rxdb-1-settings';
const SETTINGS_ID = 'a733f0a7-4fe2-4120-8603-775370fd871a';

function log(message) {
    console.log(`[gcups-container] ${message}`);
}

function readConfig(env) {
    const rawPort = env.GCUPS_HTTP_PORT || '8080';
    const port = Number(rawPort);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
        throw new Error(`invalid GCUPS_HTTP_PORT: ${rawPort}`);
    }
    return { port, password: env.GCUPS_PASSWORD || '' };
}

// Same scheme as the app's JwtPasswordAuthenticator.encryptPassword().
function hashPassword(password, salt) {
    return crypto.createHmac('sha512', salt).update(password).digest('base64');
}

// Returns the new `api` section: always enabled on the configured port, with
// the password replaced only when one is configured.
function applyApiSettings(api, { port, password }) {
    const updated = { ...api, enable: true, port };
    if (password) {
        updated.salt = crypto.randomBytes(16).toString('hex');
        updated.password = hashPassword(password, updated.salt);
    } else if (!updated.password) {
        throw new Error('GCUPS_PASSWORD is empty and no password is stored yet');
    }
    return updated;
}

async function loadSettings(db) {
    try {
        return await db.get(SETTINGS_ID);
    } catch (e) {
        if (e.status !== 404) throw e;
        return { _id: SETTINGS_ID };
    }
}

async function main() {
    const config = readConfig(process.env);

    fs.mkdirSync(path.dirname(SETTINGS_DB), { recursive: true });
    const db = new PouchDB(SETTINGS_DB, { adapter: 'leveldb' });
    try {
        const settings = await loadSettings(db);
        settings.api = applyApiSettings(settings.api || {}, config);
        await db.put(settings);
    } finally {
        await db.close();
    }

    const passwordSource = config.password ? 'set from GCUPS_PASSWORD' : 'kept from the volume';
    log(`HTTP server enabled on port ${config.port}, password ${passwordSource}`);
}

main().catch((e) => {
    console.error(`[gcups-container] failed to configure HTTP server: ${e.message}`);
    process.exit(1);
});
