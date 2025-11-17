/**
 * Advanced Fingerprint - Fingerprint estendido com dispositivos reais
 * 
 * Integra com device-profiles para gerar fingerprints ultra-realistas
 */

import { createHash } from 'crypto';
import { selectRandomDevice, selectDeviceByManufacturer } from './device-profiles';
import type { DeviceProfile } from './device-profiles';

export interface AdvancedFingerprint {
  // IDs únicos
  deviceId: string;
  clientId: string;
  
  // Dispositivo real
  device: {
    manufacturer: string;
    model: string;
    marketName: string;
    brand: string;
  };
  
  // Sistema operacional
  os: {
    name: string;
    version: string;
    sdkVersion: number;
    buildId: string;
    securityPatch: string;
  };
  
  // Navegador
  browser: {
    name: string;
    version: string;
    versionArray: [string, string, string];
    webViewVersion: string;
    userAgent: string;
  };
  
  // Tela
  screen: {
    width: number;
    height: number;
    availWidth: number;
    availHeight: number;
    density: number;
    pixelRatio: number;
    colorDepth: number;
    orientation: 'portrait' | 'landscape';
  };
  
  // Hardware
  hardware: {
    cpuCores: number;
    ramGB: number;
    storageGB: number;
    maxTouchPoints: number;
  };
  
  // Localização (Brasil)
  locale: {
    language: string;
    languages: string[];
    timezone: string;
    timezoneOffset: number;
  };
  
  // Features do navegador
  features: {
    webGL: boolean;
    webGLVendor: string;
    webGLRenderer: string;
    canvas: boolean;
    audio: boolean;
    video: boolean;
    bluetooth: boolean;
    geolocation: boolean;
  };
  
  // Metadados
  metadata: {
    generatedAt: Date;
    chipId: string;
    tenantId: string;
    profileUsed: string;
  };
}

/**
 * Lista de timezones brasileiros
 */
const BRAZIL_TIMEZONES = [
  { name: 'America/Sao_Paulo', offset: -180 },      // UTC-3 (maior parte)
  { name: 'America/Manaus', offset: -240 },         // UTC-4 (Amazonas)
  { name: 'America/Rio_Branco', offset: -300 },     // UTC-5 (Acre)
  { name: 'America/Fortaleza', offset: -180 },      // UTC-3
  { name: 'America/Recife', offset: -180 },         // UTC-3
  { name: 'America/Belem', offset: -180 },          // UTC-3
  { name: 'America/Cuiaba', offset: -240 },         // UTC-4 (Mato Grosso)
  { name: 'America/Porto_Velho', offset: -240 },    // UTC-4 (Rondônia)
  { name: 'America/Boa_Vista', offset: -240 }       // UTC-4 (Roraima)
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
function generateSecurityPatch(androidVersion: string): string {
  const year = 2024;
  const month = Math.floor(Math.random() * 12) + 1;
  const day = Math.floor(Math.random() * 28) + 1;
  
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

/**
 * Gera User-Agent realista baseado no dispositivo
 */
function generateUserAgent(profile: DeviceProfile): string {
  const { manufacturer, model, os, browser } = profile;
  
  // Formato: Mozilla/5.0 (Linux; Android VERSION; MODEL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/VERSION Mobile Safari/537.36
  return (
    `Mozilla/5.0 (Linux; Android ${os.version}; ${model}) ` +
    `AppleWebKit/537.36 (KHTML, like Gecko) ` +
    `Chrome/${browser.version} Mobile Safari/537.36`
  );
}

/**
 * Seleciona WebGL config aleatória
 */
function selectWebGLConfig(): { vendor: string; renderer: string } {
  return WEBGL_CONFIGS[Math.floor(Math.random() * WEBGL_CONFIGS.length)];
}

/**
 * Seleciona timezone brasileiro aleatório
 */
function selectBrazilianTimezone(): { name: string; offset: number } {
  // 70% São Paulo (mais comum)
  if (Math.random() < 0.7) {
    return BRAZIL_TIMEZONES[0]; // America/Sao_Paulo
  }
  
  return BRAZIL_TIMEZONES[Math.floor(Math.random() * BRAZIL_TIMEZONES.length)];
}

/**
 * Gera fingerprint avançado
 */
export function generateAdvancedFingerprint(
  tenantId: string,
  chipId: string,
  preferredManufacturer?: string
): AdvancedFingerprint {
  // Selecionar dispositivo real
  const profile = preferredManufacturer
    ? selectDeviceByManufacturer(preferredManufacturer)
    : selectRandomDevice();

  console.log(
    `[AdvancedFingerprint] Tenant ${tenantId} | Chip ${chipId.substring(0, 8)} ` +
    `→ ${profile.manufacturer} ${profile.marketName}`
  );

  // Gerar IDs únicos
  const deviceId = createHash('sha256')
    .update(`${chipId}:${Date.now()}:${Math.random()}`)
    .digest('hex')
    .substring(0, 16)
    .toUpperCase();

  const clientId = createHash('md5')
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
  const versionArray: [string, string, string] = [
    browserVersionParts[0] || '124',
    browserVersionParts[1] || '0',
    browserVersionParts[2] || '6367'
  ];

  // Screen (com ligeiras variações na availHeight para barra de status)
  const statusBarHeight = Math.floor(Math.random() * 40) + 24; // 24-64px
  const navBarHeight = Math.floor(Math.random() * 20) + 48; // 48-68px

  // Orientação (90% portrait)
  const orientation: 'portrait' | 'landscape' = Math.random() < 0.9 ? 'portrait' : 'landscape';

  const fingerprint: AdvancedFingerprint = {
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

  console.log(
    `[AdvancedFingerprint] ✅ Gerado:`,
    `\n  Device: ${fingerprint.device.marketName}`,
    `\n  Android: ${fingerprint.os.version} (SDK ${fingerprint.os.sdkVersion})`,
    `\n  Chrome: ${fingerprint.browser.version}`,
    `\n  Screen: ${fingerprint.screen.width}x${fingerprint.screen.height} @${fingerprint.screen.pixelRatio}x`,
    `\n  GPU: ${fingerprint.features.webGLVendor} ${fingerprint.features.webGLRenderer}`,
    `\n  Timezone: ${fingerprint.locale.timezone}`,
    `\n  Device ID: ${fingerprint.deviceId}`
  );

  return fingerprint;
}

/**
 * Converte fingerprint para formato Baileys
 */
export function toBaileysConfig(fingerprint: AdvancedFingerprint): {
  browser: [string, string, string];
  manufacturer: string;
  deviceId?: string;
} {
  return {
    browser: [
      fingerprint.device.marketName,
      'Chrome',
      fingerprint.browser.version
    ] as [string, string, string],
    manufacturer: fingerprint.device.manufacturer,
    deviceId: fingerprint.deviceId
  };
}

/**
 * Gera headers HTTP customizados baseados no fingerprint
 */
export function generateCustomHeaders(fingerprint: AdvancedFingerprint): Record<string, string> {
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
  const acceptLanguage = acceptLanguageVariations[
    Math.floor(Math.random() * acceptLanguageVariations.length)
  ];
  
  const acceptEncoding = acceptEncodingVariations[
    Math.floor(Math.random() * acceptEncodingVariations.length)
  ];

  // Headers customizados
  const headers: Record<string, string> = {
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
export function saveFingerprintToJSON(fingerprint: AdvancedFingerprint): string {
  return JSON.stringify(fingerprint, null, 2);
}

/**
 * Carrega fingerprint de JSON
 */
export function loadFingerprintFromJSON(json: string): AdvancedFingerprint {
  const data = JSON.parse(json);
  data.metadata.generatedAt = new Date(data.metadata.generatedAt);
  return data as AdvancedFingerprint;
}

export default generateAdvancedFingerprint;

