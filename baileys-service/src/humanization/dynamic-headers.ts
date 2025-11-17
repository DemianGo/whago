/**
 * Dynamic Headers - Gera headers HTTP dinâmicos e variáveis
 * 
 * Evita padrões detectáveis variando headers em cada requisição
 */

import type { AdvancedFingerprint } from './advanced-fingerprint';

export interface DynamicHeadersOptions {
  includeOptional?: boolean; // Incluir headers opcionais
  randomizeOrder?: boolean; // Aleatorizar ordem dos headers
  varyValues?: boolean; // Variar valores (q, etc)
}

/**
 * Pools de variações para cada header
 */
const HEADER_VARIATIONS = {
  acceptLanguage: [
    'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'pt-BR,pt;q=0.9,en;q=0.8',
    'pt-BR;q=0.9,pt;q=0.8,en-US;q=0.7,en;q=0.6',
    'pt-BR,pt;q=0.95,en-US;q=0.9,en;q=0.85',
    'pt-BR,pt;q=0.9',
    'pt-BR;q=1.0,pt;q=0.9,en-US;q=0.8',
    'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6',
    'pt-BR,pt;q=0.8,en;q=0.6'
  ],

  acceptEncoding: [
    'gzip, deflate, br',
    'gzip, deflate, br, zstd',
    'gzip, deflate',
    'br, gzip, deflate',
    'gzip, deflate, br',
    'gzip',
    'br, gzip'
  ],

  accept: [
    '*/*',
    'application/json, text/plain, */*',
    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'application/json',
    '*/*;q=0.8'
  ],

  connection: [
    'keep-alive',
    'Keep-Alive',
    undefined // às vezes omitir
  ],

  cacheControl: [
    'no-cache',
    'max-age=0',
    'no-store',
    undefined // às vezes omitir
  ],

  pragma: [
    'no-cache',
    undefined // às vezes omitir
  ],

  upgradeInsecureRequests: [
    '1',
    undefined // às vezes omitir
  ],

  dnt: [
    '1', // Do Not Track
    undefined // às vezes omitir
  ]
};

/**
 * Gera Accept-Language com valores de q aleatórios
 */
function generateAcceptLanguageWithVariation(): string {
  const q1 = (0.85 + Math.random() * 0.14).toFixed(1); // 0.85-0.99
  const q2 = (0.7 + Math.random() * 0.14).toFixed(1);  // 0.70-0.84
  const q3 = (0.5 + Math.random() * 0.19).toFixed(1);  // 0.50-0.69

  const templates = [
    `pt-BR,pt;q=${q1},en-US;q=${q2},en;q=${q3}`,
    `pt-BR,pt;q=${q1},en;q=${q2}`,
    `pt-BR;q=1.0,pt;q=${q1},en-US;q=${q2}`,
    `pt-BR,pt;q=${q1}`,
    `pt-BR;q=${q1},pt;q=${q2},en-US;q=${q3},en;q=0.5`
  ];

  return templates[Math.floor(Math.random() * templates.length)];
}

/**
 * Seleciona valor aleatório de um array (incluindo undefined)
 */
function randomValue<T>(arr: (T | undefined)[]): T | undefined {
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Gera headers dinâmicos baseados no fingerprint
 */
export function generateDynamicHeaders(
  fingerprint: AdvancedFingerprint,
  options: DynamicHeadersOptions = {}
): Record<string, string> {
  const opts = {
    includeOptional: true,
    randomizeOrder: true,
    varyValues: true,
    ...options
  };

  const headers: Record<string, string> = {};

  // ========== HEADERS OBRIGATÓRIOS ==========
  
  // User-Agent (sempre presente)
  headers['User-Agent'] = fingerprint.browser.userAgent;

  // Accept-Language (variável)
  if (opts.varyValues) {
    headers['Accept-Language'] = generateAcceptLanguageWithVariation();
  } else {
    headers['Accept-Language'] = randomValue(HEADER_VARIATIONS.acceptLanguage) || HEADER_VARIATIONS.acceptLanguage[0];
  }

  // Accept-Encoding (variável)
  headers['Accept-Encoding'] = randomValue(HEADER_VARIATIONS.acceptEncoding) || HEADER_VARIATIONS.acceptEncoding[0];

  // Accept (variável)
  headers['Accept'] = randomValue(HEADER_VARIATIONS.accept) || '*/*';

  // Origin e Referer (WhatsApp específico)
  headers['Origin'] = 'https://web.whatsapp.com';
  headers['Referer'] = 'https://web.whatsapp.com/';

  // Sec-Fetch-* (Chrome específico)
  headers['Sec-Fetch-Site'] = 'same-site';
  headers['Sec-Fetch-Mode'] = 'cors';
  headers['Sec-Fetch-Dest'] = 'empty';

  // Sec-CH-UA (Client Hints)
  const chromeVersion = fingerprint.browser.versionArray[0];
  headers['Sec-CH-UA'] = `"Chromium";v="${chromeVersion}", "Google Chrome";v="${chromeVersion}", "Not-A.Brand";v="99"`;
  headers['Sec-CH-UA-Mobile'] = '?1';
  headers['Sec-CH-UA-Platform'] = '"Android"';

  // ========== HEADERS OPCIONAIS ==========
  
  if (opts.includeOptional) {
    // Connection (70% de chance)
    if (Math.random() < 0.7) {
      const connection = randomValue(HEADER_VARIATIONS.connection);
      if (connection) headers['Connection'] = connection;
    }

    // Cache-Control (50% de chance)
    if (Math.random() < 0.5) {
      const cacheControl = randomValue(HEADER_VARIATIONS.cacheControl);
      if (cacheControl) headers['Cache-Control'] = cacheControl;
    }

    // Pragma (30% de chance)
    if (Math.random() < 0.3) {
      const pragma = randomValue(HEADER_VARIATIONS.pragma);
      if (pragma) headers['Pragma'] = pragma;
    }

    // DNT (40% de chance)
    if (Math.random() < 0.4) {
      const dnt = randomValue(HEADER_VARIATIONS.dnt);
      if (dnt) headers['DNT'] = dnt;
    }

    // Upgrade-Insecure-Requests (20% de chance)
    if (Math.random() < 0.2) {
      const upgrade = randomValue(HEADER_VARIATIONS.upgradeInsecureRequests);
      if (upgrade) headers['Upgrade-Insecure-Requests'] = upgrade;
    }

    // X-Requested-With (Android WebView - 60% de chance)
    if (Math.random() < 0.6) {
      headers['X-Requested-With'] = 'XMLHttpRequest';
    }
  }

  // ========== ALEATORIZAR ORDEM ==========
  
  if (opts.randomizeOrder) {
    // Converter para array, embaralhar, e reconverter
    const entries = Object.entries(headers);
    
    // Fisher-Yates shuffle
    for (let i = entries.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [entries[i], entries[j]] = [entries[j], entries[i]];
    }

    // Reconstruir objeto (ordem aleatória)
    const shuffled: Record<string, string> = {};
    for (const [key, value] of entries) {
      shuffled[key] = value;
    }

    return shuffled;
  }

  return headers;
}

/**
 * Gera headers específicos para WebSocket (WhatsApp)
 */
export function generateWebSocketHeaders(
  fingerprint: AdvancedFingerprint
): Record<string, string> {
  return {
    'User-Agent': fingerprint.browser.userAgent,
    'Origin': 'https://web.whatsapp.com',
    'Accept-Language': generateAcceptLanguageWithVariation(),
    'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
    'Sec-WebSocket-Version': '13'
  };
}

/**
 * Gera headers para requisições HTTP normais (API)
 */
export function generateAPIHeaders(
  fingerprint: AdvancedFingerprint,
  contentType?: string
): Record<string, string> {
  const headers = generateDynamicHeaders(fingerprint, {
    includeOptional: true,
    randomizeOrder: false,
    varyValues: true
  });

  // Adicionar Content-Type se especificado
  if (contentType) {
    headers['Content-Type'] = contentType;
  }

  return headers;
}

/**
 * Gera variação de headers para cada requisição
 * (usar em interceptors)
 */
export function varyHeadersPerRequest(
  baseHeaders: Record<string, string>
): Record<string, string> {
  const varied = { ...baseHeaders };

  // Variar Accept-Language (30% de chance)
  if (Math.random() < 0.3) {
    varied['Accept-Language'] = generateAcceptLanguageWithVariation();
  }

  // Variar Accept-Encoding (20% de chance)
  if (Math.random() < 0.2) {
    varied['Accept-Encoding'] = randomValue(HEADER_VARIATIONS.acceptEncoding) || varied['Accept-Encoding'];
  }

  // Adicionar/remover headers opcionais
  if (Math.random() < 0.3) {
    if (varied['DNT']) {
      delete varied['DNT'];
    } else {
      varied['DNT'] = '1';
    }
  }

  if (Math.random() < 0.2) {
    if (varied['Cache-Control']) {
      delete varied['Cache-Control'];
    } else {
      varied['Cache-Control'] = randomValue(HEADER_VARIATIONS.cacheControl) || 'no-cache';
    }
  }

  return varied;
}

/**
 * Compara dois conjuntos de headers e retorna diferenças
 */
export function compareHeaders(
  headers1: Record<string, string>,
  headers2: Record<string, string>
): {
  different: string[];
  onlyInFirst: string[];
  onlyInSecond: string[];
  identical: string[];
} {
  const allKeys = new Set([...Object.keys(headers1), ...Object.keys(headers2)]);
  
  const result = {
    different: [] as string[],
    onlyInFirst: [] as string[],
    onlyInSecond: [] as string[],
    identical: [] as string[]
  };

  for (const key of allKeys) {
    if (!(key in headers1)) {
      result.onlyInSecond.push(key);
    } else if (!(key in headers2)) {
      result.onlyInFirst.push(key);
    } else if (headers1[key] !== headers2[key]) {
      result.different.push(key);
    } else {
      result.identical.push(key);
    }
  }

  return result;
}

/**
 * Log de headers para debug (mascarando valores sensíveis)
 */
export function logHeaders(
  headers: Record<string, string>,
  label: string = 'Headers'
): void {
  console.log(`[DynamicHeaders] ${label}:`);
  
  for (const [key, value] of Object.entries(headers)) {
    // Mascarar User-Agent (muito longo)
    if (key === 'User-Agent') {
      console.log(`  ${key}: ${value.substring(0, 50)}...`);
    } else {
      console.log(`  ${key}: ${value}`);
    }
  }
}

export default generateDynamicHeaders;

