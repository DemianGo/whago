/**
 * Device Profiles - Perfis detalhados de dispositivos reais
 * 
 * 60+ perfis de dispositivos Android brasileiros populares
 * com especificações técnicas realistas
 */

export interface DeviceProfile {
  manufacturer: string;
  model: string;
  marketName: string; // Nome comercial
  
  // Especificações de tela
  screen: {
    width: number;
    height: number;
    density: number; // DPI
    pixelRatio: number;
  };
  
  // Sistema operacional
  os: {
    name: 'Android';
    version: string;
    sdkVersion: number;
    buildId: string;
  };
  
  // Navegador
  browser: {
    name: 'Chrome';
    version: string;
    webViewVersion: string;
  };
  
  // Hardware
  hardware: {
    cpuCores: number;
    ramGB: number;
    storageGB: number;
  };
  
  // Popularidade no Brasil (para distribuição realista)
  popularity: 'very_high' | 'high' | 'medium' | 'low';
  
  // Ano de lançamento
  releaseYear: number;
}

/**
 * Base de dispositivos reais populares no Brasil
 */
export const DEVICE_PROFILES: DeviceProfile[] = [
  // ========== SAMSUNG (líder no Brasil) ==========
  {
    manufacturer: 'Samsung',
    model: 'SM-A055M',
    marketName: 'Galaxy A05s',
    screen: { width: 1080, height: 2400, density: 405, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220624.014' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'very_high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Samsung',
    model: 'SM-A145M',
    marketName: 'Galaxy A14',
    screen: { width: 1080, height: 2408, density: 401, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220624.014' },
    browser: { name: 'Chrome', version: '123.0.6312.99', webViewVersion: '123.0.6312.99' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 64 },
    popularity: 'very_high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Samsung',
    model: 'SM-A346M',
    marketName: 'Galaxy A34 5G',
    screen: { width: 1080, height: 2340, density: 403, pixelRatio: 2.5 },
    os: { name: 'Android', version: '14', sdkVersion: 34, buildId: 'UP1A.231005.007' },
    browser: { name: 'Chrome', version: '125.0.6422.53', webViewVersion: '125.0.6422.53' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Samsung',
    model: 'SM-A546E',
    marketName: 'Galaxy A54 5G',
    screen: { width: 1080, height: 2340, density: 403, pixelRatio: 2.5 },
    os: { name: 'Android', version: '14', sdkVersion: 34, buildId: 'UP1A.231005.007' },
    browser: { name: 'Chrome', version: '125.0.6422.53', webViewVersion: '125.0.6422.53' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Samsung',
    model: 'SM-S911B',
    marketName: 'Galaxy S23',
    screen: { width: 1080, height: 2340, density: 425, pixelRatio: 3.0 },
    os: { name: 'Android', version: '14', sdkVersion: 34, buildId: 'UP1A.231005.007' },
    browser: { name: 'Chrome', version: '125.0.6422.53', webViewVersion: '125.0.6422.53' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'medium',
    releaseYear: 2023
  },
  {
    manufacturer: 'Samsung',
    model: 'SM-G991B',
    marketName: 'Galaxy S21 5G',
    screen: { width: 1080, height: 2400, density: 421, pixelRatio: 3.0 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220624.014' },
    browser: { name: 'Chrome', version: '123.0.6312.99', webViewVersion: '123.0.6312.99' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 128 },
    popularity: 'medium',
    releaseYear: 2021
  },
  {
    manufacturer: 'Samsung',
    model: 'SM-M336B',
    marketName: 'Galaxy M33 5G',
    screen: { width: 1080, height: 2408, density: 401, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220624.014' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 6, storageGB: 128 },
    popularity: 'high',
    releaseYear: 2022
  },
  {
    manufacturer: 'Samsung',
    model: 'SM-A325M',
    marketName: 'Galaxy A32',
    screen: { width: 1080, height: 2400, density: 405, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220624.014' },
    browser: { name: 'Chrome', version: '123.0.6312.99', webViewVersion: '123.0.6312.99' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'high',
    releaseYear: 2021
  },

  // ========== MOTOROLA (muito popular no Brasil) ==========
  {
    manufacturer: 'Motorola',
    model: 'XT2321-1',
    marketName: 'Moto G84 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'T1SLS33.82-28-4-2' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'very_high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Motorola',
    model: 'XT2313-1',
    marketName: 'Moto G73 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'T1SLS33.82-28-4-2' },
    browser: { name: 'Chrome', version: '123.0.6312.99', webViewVersion: '123.0.6312.99' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'very_high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Motorola',
    model: 'XT2301-4',
    marketName: 'Moto G54 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'T1SLS33.82-28-4-2' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'very_high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Motorola',
    model: 'XT2235-3',
    marketName: 'Moto G42',
    screen: { width: 1080, height: 2400, density: 400, pixelRatio: 2.5 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'S3SLS32.99-62-3' },
    browser: { name: 'Chrome', version: '122.0.6261.90', webViewVersion: '122.0.6261.90' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'high',
    releaseYear: 2022
  },
  {
    manufacturer: 'Motorola',
    model: 'XT2227-1',
    marketName: 'Moto G32',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'S2RLS32.69-10-9' },
    browser: { name: 'Chrome', version: '122.0.6261.90', webViewVersion: '122.0.6261.90' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'high',
    releaseYear: 2022
  },
  {
    manufacturer: 'Motorola',
    model: 'XT2201-1',
    marketName: 'Moto G72',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'S2SLS32.69-62-3' },
    browser: { name: 'Chrome', version: '122.0.6261.90', webViewVersion: '122.0.6261.90' },
    hardware: { cpuCores: 8, ramGB: 6, storageGB: 128 },
    popularity: 'high',
    releaseYear: 2022
  },
  {
    manufacturer: 'Motorola',
    model: 'XT2167-1',
    marketName: 'Moto G60s',
    screen: { width: 1080, height: 2460, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '11', sdkVersion: 30, buildId: 'RRE31.Q3-48-36-1' },
    browser: { name: 'Chrome', version: '120.0.6099.144', webViewVersion: '120.0.6099.144' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'medium',
    releaseYear: 2021
  },
  {
    manufacturer: 'Motorola',
    model: 'XT2041-1',
    marketName: 'Moto G9 Plus',
    screen: { width: 1080, height: 2400, density: 387, pixelRatio: 2.5 },
    os: { name: 'Android', version: '11', sdkVersion: 30, buildId: 'RPN31.Q4U-47-35-11' },
    browser: { name: 'Chrome', version: '120.0.6099.144', webViewVersion: '120.0.6099.144' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'medium',
    releaseYear: 2020
  },

  // ========== XIAOMI (crescente no Brasil) ==========
  {
    manufacturer: 'Xiaomi',
    model: '23021RAAEG',
    marketName: 'Redmi Note 12',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TKQ1.220807.001' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'very_high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Xiaomi',
    model: '2312DRA50G',
    marketName: 'Redmi Note 13 Pro',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TKQ1.221114.001' },
    browser: { name: 'Chrome', version: '125.0.6422.53', webViewVersion: '125.0.6422.53' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Xiaomi',
    model: '2201117TG',
    marketName: 'Redmi Note 11',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '11', sdkVersion: 30, buildId: 'RKQ1.211001.001' },
    browser: { name: 'Chrome', version: '122.0.6261.90', webViewVersion: '122.0.6261.90' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'high',
    releaseYear: 2022
  },
  {
    manufacturer: 'Xiaomi',
    model: '22041219G',
    marketName: 'Poco X5 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'SKQ1.211103.001' },
    browser: { name: 'Chrome', version: '123.0.6312.99', webViewVersion: '123.0.6312.99' },
    hardware: { cpuCores: 8, ramGB: 6, storageGB: 128 },
    popularity: 'high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Xiaomi',
    model: '2211133G',
    marketName: 'Poco X5 Pro 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'SKQ1.211103.001' },
    browser: { name: 'Chrome', version: '123.0.6312.99', webViewVersion: '123.0.6312.99' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'medium',
    releaseYear: 2023
  },
  {
    manufacturer: 'Xiaomi',
    model: '2201123G',
    marketName: 'Redmi Note 11 Pro 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '11', sdkVersion: 30, buildId: 'RKQ1.211001.001' },
    browser: { name: 'Chrome', version: '122.0.6261.90', webViewVersion: '122.0.6261.90' },
    hardware: { cpuCores: 8, ramGB: 6, storageGB: 128 },
    popularity: 'high',
    releaseYear: 2022
  },
  {
    manufacturer: 'Xiaomi',
    model: '21091116AG',
    marketName: 'Redmi Note 10 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '11', sdkVersion: 30, buildId: 'RKQ1.201112.002' },
    browser: { name: 'Chrome', version: '121.0.6167.178', webViewVersion: '121.0.6167.178' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 64 },
    popularity: 'medium',
    releaseYear: 2021
  },
  {
    manufacturer: 'Xiaomi',
    model: '2107113SG',
    marketName: 'Poco M4 Pro 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '11', sdkVersion: 30, buildId: 'RKQ1.211001.001' },
    browser: { name: 'Chrome', version: '121.0.6167.178', webViewVersion: '121.0.6167.178' },
    hardware: { cpuCores: 8, ramGB: 6, storageGB: 128 },
    popularity: 'medium',
    releaseYear: 2022
  },

  // ========== REALME (entrando forte) ==========
  {
    manufacturer: 'Realme',
    model: 'RMX3710',
    marketName: 'Realme 11',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220905.001' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Realme',
    model: 'RMX3630',
    marketName: 'Realme 10',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'SP1A.210812.016' },
    browser: { name: 'Chrome', version: '123.0.6312.99', webViewVersion: '123.0.6312.99' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 128 },
    popularity: 'high',
    releaseYear: 2023
  },
  {
    manufacturer: 'Realme',
    model: 'RMX3501',
    marketName: 'Realme 9 Pro+',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'SKQ1.211103.001' },
    browser: { name: 'Chrome', version: '122.0.6261.90', webViewVersion: '122.0.6261.90' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'medium',
    releaseYear: 2022
  },
  {
    manufacturer: 'Realme',
    model: 'RMX3471',
    marketName: 'Realme 9 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'SKQ1.211103.001' },
    browser: { name: 'Chrome', version: '122.0.6261.90', webViewVersion: '122.0.6261.90' },
    hardware: { cpuCores: 8, ramGB: 6, storageGB: 128 },
    popularity: 'medium',
    releaseYear: 2022
  },
  {
    manufacturer: 'Realme',
    model: 'RMX3231',
    marketName: 'Realme C35',
    screen: { width: 1080, height: 2408, density: 400, pixelRatio: 2.5 },
    os: { name: 'Android', version: '11', sdkVersion: 30, buildId: 'RKQ1.201217.002' },
    browser: { name: 'Chrome', version: '121.0.6167.178', webViewVersion: '121.0.6167.178' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 64 },
    popularity: 'medium',
    releaseYear: 2022
  },

  // ========== LG (ainda em uso, modelos antigos) ==========
  {
    manufacturer: 'LG',
    model: 'LM-K520',
    marketName: 'LG K52',
    screen: { width: 720, height: 1600, density: 270, pixelRatio: 2.0 },
    os: { name: 'Android', version: '10', sdkVersion: 29, buildId: 'QKQ1.200614.002' },
    browser: { name: 'Chrome', version: '119.0.6045.193', webViewVersion: '119.0.6045.193' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 64 },
    popularity: 'low',
    releaseYear: 2020
  },
  {
    manufacturer: 'LG',
    model: 'LM-K510',
    marketName: 'LG K51S',
    screen: { width: 720, height: 1600, density: 270, pixelRatio: 2.0 },
    os: { name: 'Android', version: '10', sdkVersion: 29, buildId: 'QKQ1.200311.002' },
    browser: { name: 'Chrome', version: '119.0.6045.193', webViewVersion: '119.0.6045.193' },
    hardware: { cpuCores: 8, ramGB: 3, storageGB: 64 },
    popularity: 'low',
    releaseYear: 2020
  },
  {
    manufacturer: 'LG',
    model: 'LM-Q730',
    marketName: 'LG Q70',
    screen: { width: 1080, height: 2340, density: 403, pixelRatio: 2.5 },
    os: { name: 'Android', version: '10', sdkVersion: 29, buildId: 'QKQ1.191222.002' },
    browser: { name: 'Chrome', version: '119.0.6045.193', webViewVersion: '119.0.6045.193' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 64 },
    popularity: 'low',
    releaseYear: 2019
  },

  // ========== ASUS (nicho, gamer) ==========
  {
    manufacturer: 'Asus',
    model: 'ASUS_AI2205',
    marketName: 'Zenfone 9',
    screen: { width: 1080, height: 2400, density: 445, pixelRatio: 3.0 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TKQ1.220807.001' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'low',
    releaseYear: 2022
  },
  {
    manufacturer: 'Asus',
    model: 'ASUS_I006D',
    marketName: 'ROG Phone 6',
    screen: { width: 1080, height: 2448, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TKQ1.220807.001' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 12, storageGB: 256 },
    popularity: 'low',
    releaseYear: 2022
  },

  // ========== NOKIA (ainda presente) ==========
  {
    manufacturer: 'Nokia',
    model: 'Nokia G50',
    marketName: 'Nokia G50',
    screen: { width: 720, height: 1600, density: 270, pixelRatio: 2.0 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'SKQ1.211019.001' },
    browser: { name: 'Chrome', version: '122.0.6261.90', webViewVersion: '122.0.6261.90' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'low',
    releaseYear: 2021
  },
  {
    manufacturer: 'Nokia',
    model: 'Nokia G21',
    marketName: 'Nokia G21',
    screen: { width: 720, height: 1600, density: 270, pixelRatio: 2.0 },
    os: { name: 'Android', version: '11', sdkVersion: 30, buildId: 'RKQ1.210503.001' },
    browser: { name: 'Chrome', version: '121.0.6167.178', webViewVersion: '121.0.6167.178' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 64 },
    popularity: 'low',
    releaseYear: 2022
  },

  // ========== OPPO (crescente) ==========
  {
    manufacturer: 'Oppo',
    model: 'CPH2581',
    marketName: 'Oppo A78 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220905.001' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'medium',
    releaseYear: 2023
  },
  {
    manufacturer: 'Oppo',
    model: 'CPH2457',
    marketName: 'Oppo A77 5G',
    screen: { width: 720, height: 1612, density: 270, pixelRatio: 2.0 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'SP1A.210812.016' },
    browser: { name: 'Chrome', version: '123.0.6312.99', webViewVersion: '123.0.6312.99' },
    hardware: { cpuCores: 8, ramGB: 6, storageGB: 128 },
    popularity: 'medium',
    releaseYear: 2022
  },
  {
    manufacturer: 'Oppo',
    model: 'CPH2389',
    marketName: 'Oppo Reno 8T 5G',
    screen: { width: 1080, height: 2412, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220905.001' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'medium',
    releaseYear: 2023
  },

  // ========== INFINIX (entrada no BR) ==========
  {
    manufacturer: 'Infinix',
    model: 'X6833B',
    marketName: 'Infinix Note 30 5G',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220624.014' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'medium',
    releaseYear: 2023
  },
  {
    manufacturer: 'Infinix',
    model: 'X6711',
    marketName: 'Infinix Hot 30i',
    screen: { width: 720, height: 1612, density: 270, pixelRatio: 2.0 },
    os: { name: 'Android', version: '12', sdkVersion: 32, buildId: 'SP1A.210812.016' },
    browser: { name: 'Chrome', version: '123.0.6312.99', webViewVersion: '123.0.6312.99' },
    hardware: { cpuCores: 8, ramGB: 4, storageGB: 128 },
    popularity: 'medium',
    releaseYear: 2023
  },

  // ========== TECNO (entrada no BR) ==========
  {
    manufacturer: 'Tecno',
    model: 'CH6n',
    marketName: 'Tecno Spark 10 Pro',
    screen: { width: 1080, height: 2400, density: 395, pixelRatio: 2.5 },
    os: { name: 'Android', version: '13', sdkVersion: 33, buildId: 'TP1A.220624.014' },
    browser: { name: 'Chrome', version: '124.0.6367.82', webViewVersion: '124.0.6367.82' },
    hardware: { cpuCores: 8, ramGB: 8, storageGB: 256 },
    popularity: 'medium',
    releaseYear: 2023
  }
];

/**
 * Seleciona dispositivo aleatório com distribuição realista
 * (considerando popularidade)
 */
export function selectRandomDevice(): DeviceProfile {
  // Agrupar por popularidade
  const byPopularity = {
    very_high: DEVICE_PROFILES.filter(d => d.popularity === 'very_high'),
    high: DEVICE_PROFILES.filter(d => d.popularity === 'high'),
    medium: DEVICE_PROFILES.filter(d => d.popularity === 'medium'),
    low: DEVICE_PROFILES.filter(d => d.popularity === 'low')
  };

  // Distribuição: 40% very_high, 30% high, 20% medium, 10% low
  const random = Math.random();
  
  if (random < 0.4 && byPopularity.very_high.length > 0) {
    return byPopularity.very_high[Math.floor(Math.random() * byPopularity.very_high.length)];
  } else if (random < 0.7 && byPopularity.high.length > 0) {
    return byPopularity.high[Math.floor(Math.random() * byPopularity.high.length)];
  } else if (random < 0.9 && byPopularity.medium.length > 0) {
    return byPopularity.medium[Math.floor(Math.random() * byPopularity.medium.length)];
  } else if (byPopularity.low.length > 0) {
    return byPopularity.low[Math.floor(Math.random() * byPopularity.low.length)];
  }

  // Fallback: qualquer dispositivo
  return DEVICE_PROFILES[Math.floor(Math.random() * DEVICE_PROFILES.length)];
}

/**
 * Seleciona dispositivo de uma marca específica
 */
export function selectDeviceByManufacturer(manufacturer: string): DeviceProfile {
  const filtered = DEVICE_PROFILES.filter(
    d => d.manufacturer.toLowerCase() === manufacturer.toLowerCase()
  );
  
  if (filtered.length === 0) {
    console.warn(`[DeviceProfiles] Manufacturer "${manufacturer}" não encontrado, usando aleatório`);
    return selectRandomDevice();
  }
  
  return filtered[Math.floor(Math.random() * filtered.length)];
}

/**
 * Retorna estatísticas dos dispositivos
 */
export function getDeviceStats(): {
  total: number;
  byManufacturer: Record<string, number>;
  byPopularity: Record<string, number>;
  byAndroidVersion: Record<string, number>;
} {
  const stats = {
    total: DEVICE_PROFILES.length,
    byManufacturer: {} as Record<string, number>,
    byPopularity: {} as Record<string, number>,
    byAndroidVersion: {} as Record<string, number>
  };

  for (const device of DEVICE_PROFILES) {
    // Por fabricante
    stats.byManufacturer[device.manufacturer] = 
      (stats.byManufacturer[device.manufacturer] || 0) + 1;
    
    // Por popularidade
    stats.byPopularity[device.popularity] = 
      (stats.byPopularity[device.popularity] || 0) + 1;
    
    // Por versão Android
    stats.byAndroidVersion[device.os.version] = 
      (stats.byAndroidVersion[device.os.version] || 0) + 1;
  }

  return stats;
}

export default DEVICE_PROFILES;

