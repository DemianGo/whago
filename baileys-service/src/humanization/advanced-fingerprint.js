"use strict";
/**
 * Advanced Fingerprint - Fingerprint estendido com dispositivos reais
 *
 * Integra com device-profiles para gerar fingerprints ultra-realistas
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateAdvancedFingerprint = generateAdvancedFingerprint;
exports.toBaileysConfig = toBaileysConfig;
exports.generateCustomHeaders = generateCustomHeaders;
exports.saveFingerprintToJSON = saveFingerprintToJSON;
exports.loadFingerprintFromJSON = loadFingerprintFromJSON;
const crypto = require("crypto");
const device_profiles_1 = require("./device-profiles");
/**
 * Lista de timezones brasileiros
 */
const BRAZIL_TIMEZONES = [
    { name: 'America/Sao_Paulo', offset: -180 }, // UTC-3 (maior parte)
    { name: 'America/Manaus', offset: -240 }, // UTC-4 (Amazonas)
    { name: 'America/Rio_Branco', offset: -300 }, // UTC-5 (Acre)
    { name: 'America/Fortaleza', offset: -180 }, // UTC-3
    { name: 'America/Recife', offset: -180 }, // UTC-3
    { name: 'America/Belem', offset: -180 }, // UTC-3
    { name: 'America/Cuiaba', offset: -240 }, // UTC-4 (Mato Grosso)
    { name: 'America/Porto_Velho', offset: -240 }, // UTC-4 (Rondônia)
    { name: 'America/Boa_Vista', offset: -240 } // UTC-4 (Roraima)
];
/**
 * WebGL Vendors/Renderers comuns em Android
 */
const WEBGL_CONFIGS = [
    { vendor: 'Qualcomm', renderer: 'Adreno (TM) 619' },
    { vendor: 'Qualcomm', renderer: 'Adreno (TM) 642L' },
    { vendor: 'Qualcomm', renderer: 'Adreno (TM) 650' },
    { vendor: 'ARM', renderer: 'Mali-G52 MC2' },
    { vendor: 'ARM', renderer: 'Mali-G57 MC2' },
    { vendor: 'ARM', renderer: 'Mali-G68 MC4' },
    { vendor: 'ARM', renderer: 'Mali-G76 MC4' },
    { vendor: 'Qualcomm', renderer: 'Adreno (TM) 730' },
    { vendor: 'Qualcomm', renderer: 'Adreno (TM) 640' },
    { vendor: 'ARM', renderer: 'Mali-G77 MC9' }
];
/**
 * Security patches realistas (últimos 12 meses)
 */
function generateSecurityPatch(androidVersion) {
    const year = 2024;
    const month = Math.floor(Math.random() * 12) + 1;
    const day = Math.floor(Math.random() * 28) + 1;
    return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}
/**
 * Gera User-Agent realista baseado no dispositivo
 */
function generateUserAgent(profile) {
    const { manufacturer, model, os, browser } = profile;
    // Formato: Mozilla/5.0 (Linux; Android VERSION; MODEL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/VERSION Mobile Safari/537.36
    return (`Mozilla/5.0 (Linux; Android ${os.version}; ${model}) ` +
        `AppleWebKit/537.36 (KHTML, like Gecko) ` +
        `Chrome/${browser.version} Mobile Safari/537.36`);
}
/**
 * Seleciona WebGL config aleatória
 */
function selectWebGLConfig() {
    return WEBGL_CONFIGS[Math.floor(Math.random() * WEBGL_CONFIGS.length)];
}
/**
 * Seleciona timezone brasileiro aleatório
 */
function selectBrazilianTimezone() {
    // 70% São Paulo (mais comum)
    if (Math.random() < 0.7) {
        return BRAZIL_TIMEZONES[0]; // America/Sao_Paulo
    }
    return BRAZIL_TIMEZONES[Math.floor(Math.random() * BRAZIL_TIMEZONES.length)];
}
/**
 * Gera fingerprint avançado
 */
function generateAdvancedFingerprint(tenantId, chipId, preferredManufacturer) {
    // Selecionar dispositivo real
    const profile = preferredManufacturer
        ? (0, device_profiles_1.selectDeviceByManufacturer)(preferredManufacturer)
        : (0, device_profiles_1.selectRandomDevice)();
    console.log(`[AdvancedFingerprint] Tenant ${tenantId} | Chip ${chipId.substring(0, 8)} ` +
        `→ ${profile.manufacturer} ${profile.marketName}`);
    // Gerar IDs únicos
    const deviceId = crypto
        .createHash('sha256')
        .update(`${chipId}:${Date.now()}:${Math.random()}`)
        .digest('hex')
        .substring(0, 16)
        .toUpperCase();
    const clientId = crypto
        .createHash('md5')
        .update(`${tenantId}:${chipId}:${Date.now()}`)
        .digest('hex')
        .substring(0, 32);
    // Timezone brasileiro
    const timezone = selectBrazilianTimezone();
    // WebGL
    const webgl = selectWebGLConfig();
    // User-Agent
    const userAgent = generateUserAgent(profile);
    // Browser version array
    const browserVersionParts = profile.browser.version.split('.');
    const versionArray = [
        browserVersionParts[0] || '124',
        browserVersionParts[1] || '0',
        browserVersionParts[2] || '6367'
    ];
    // Screen (com ligeiras variações na availHeight para barra de status)
    const statusBarHeight = Math.floor(Math.random() * 40) + 24; // 24-64px
    const navBarHeight = Math.floor(Math.random() * 20) + 48; // 48-68px
    // Orientação (90% portrait)
    const orientation = Math.random() < 0.9 ? 'portrait' : 'landscape';
    const fingerprint = {
        deviceId,
        clientId,
        device: {
            manufacturer: profile.manufacturer,
            model: profile.model,
            marketName: profile.marketName,
            brand: profile.manufacturer
        },
        os: {
            name: 'Android',
            version: profile.os.version,
            sdkVersion: profile.os.sdkVersion,
            buildId: profile.os.buildId,
            securityPatch: generateSecurityPatch(profile.os.version)
        },
        browser: {
            name: 'Chrome',
            version: profile.browser.version,
            versionArray,
            webViewVersion: profile.browser.webViewVersion,
            userAgent
        },
        screen: {
            width: profile.screen.width,
            height: profile.screen.height,
            availWidth: profile.screen.width,
            availHeight: profile.screen.height - statusBarHeight - navBarHeight,
            density: profile.screen.density,
            pixelRatio: profile.screen.pixelRatio,
            colorDepth: 24,
            orientation
        },
        hardware: {
            cpuCores: profile.hardware.cpuCores,
            ramGB: profile.hardware.ramGB,
            storageGB: profile.hardware.storageGB,
            maxTouchPoints: Math.random() < 0.8 ? 5 : 10 // 80% = 5 pontos, 20% = 10 pontos
        },
        locale: {
            language: 'pt-BR',
            languages: ['pt-BR', 'pt', 'en-US', 'en'],
            timezone: timezone.name,
            timezoneOffset: timezone.offset
        },
        features: {
            webGL: true,
            webGLVendor: webgl.vendor,
            webGLRenderer: webgl.renderer,
            canvas: true,
            audio: true,
            video: true,
            bluetooth: Math.random() < 0.7, // 70% tem bluetooth
            geolocation: Math.random() < 0.8 // 80% tem geolocation
        },
        metadata: {
            generatedAt: new Date(),
            chipId,
            tenantId,
            profileUsed: `${profile.manufacturer} ${profile.marketName}`
        }
    };
    console.log(`[AdvancedFingerprint] ✅ Gerado:`, `\n  Device: ${fingerprint.device.marketName}`, `\n  Android: ${fingerprint.os.version} (SDK ${fingerprint.os.sdkVersion})`, `\n  Chrome: ${fingerprint.browser.version}`, `\n  Screen: ${fingerprint.screen.width}x${fingerprint.screen.height} @${fingerprint.screen.pixelRatio}x`, `\n  GPU: ${fingerprint.features.webGLVendor} ${fingerprint.features.webGLRenderer}`, `\n  Timezone: ${fingerprint.locale.timezone}`, `\n  Device ID: ${fingerprint.deviceId}`);
    return fingerprint;
}
/**
 * Converte fingerprint para formato Baileys
 */
function toBaileysConfig(fingerprint) {
    return {
        browser: [
            fingerprint.device.marketName,
            'Chrome',
            fingerprint.browser.version
        ],
        manufacturer: fingerprint.device.manufacturer,
        deviceId: fingerprint.deviceId
    };
}
/**
 * Gera headers HTTP customizados baseados no fingerprint
 */
function generateCustomHeaders(fingerprint) {
    // Variações na ordem e valores de Accept-Language
    const acceptLanguageVariations = [
        'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'pt-BR,pt;q=0.9,en;q=0.8',
        'pt-BR;q=0.9,pt;q=0.8,en-US;q=0.7,en;q=0.6',
        'pt-BR,pt;q=0.95,en-US;q=0.9,en;q=0.85',
        'pt-BR,pt;q=0.9'
    ];
    // Variações em Accept-Encoding
    const acceptEncodingVariations = [
        'gzip, deflate, br',
        'gzip, deflate, br, zstd',
        'gzip, deflate',
        'br, gzip, deflate'
    ];
    // Sec-CH-UA (Client Hints - Chrome)
    const secChUa = `"Chromium";v="${fingerprint.browser.versionArray[0]}", "Google Chrome";v="${fingerprint.browser.versionArray[0]}", "Not-A.Brand";v="99"`;
    const secChUaMobile = '?1'; // Mobile
    const secChUaPlatform = '"Android"';
    // Selecionar variações aleatórias
    const acceptLanguage = acceptLanguageVariations[Math.floor(Math.random() * acceptLanguageVariations.length)];
    const acceptEncoding = acceptEncodingVariations[Math.floor(Math.random() * acceptEncodingVariations.length)];
    // Headers customizados
    const headers = {
        'User-Agent': fingerprint.browser.userAgent,
        'Accept-Language': acceptLanguage,
        'Accept-Encoding': acceptEncoding,
        'Accept': '*/*',
        'Origin': 'https://web.whatsapp.com',
        'Referer': 'https://web.whatsapp.com/',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Sec-CH-UA': secChUa,
        'Sec-CH-UA-Mobile': secChUaMobile,
        'Sec-CH-UA-Platform': secChUaPlatform
    };
    // Adicionar headers opcionais (50% de chance)
    if (Math.random() < 0.5) {
        headers['Cache-Control'] = 'no-cache';
    }
    if (Math.random() < 0.3) {
        headers['Pragma'] = 'no-cache';
    }
    if (Math.random() < 0.5) {
        headers['DNT'] = '1'; // Do Not Track
    }
    return headers;
}
/**
 * Salva fingerprint em JSON (para cache/auditoria)
 */
function saveFingerprintToJSON(fingerprint) {
    return JSON.stringify(fingerprint, null, 2);
}
/**
 * Carrega fingerprint de JSON
 */
function loadFingerprintFromJSON(json) {
    const data = JSON.parse(json);
    data.metadata.generatedAt = new Date(data.metadata.generatedAt);
    return data;
}
exports.default = generateAdvancedFingerprint;
