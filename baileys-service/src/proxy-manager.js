/**
 * WHAGO Proxy Manager
 * 
 * Módulo isolado para gerenciamento de proxies.
 * Suporta múltiplos provedores: Smartproxy, IPRoyal, Bright Data, Oxylabs, etc.
 * 
 * Configuração via variáveis de ambiente (.env):
 * - PROXY_ENABLED=true/false
 * - PROXY_TYPE=http/socks5
 * - PROXY_HOST=gate.smartproxy.com
 * - PROXY_PORT=7000
 * - PROXY_USERNAME=seu_usuario
 * - PROXY_PASSWORD=sua_senha
 * - PROXY_COUNTRY=BR (opcional)
 * - PROXY_SESSION_ID=whago_session (opcional, para IP sticky)
 */

const { SocksProxyAgent } = require('socks-proxy-agent');
const { HttpsProxyAgent } = require('https-proxy-agent');

class ProxyManager {
  constructor() {
    this.enabled = process.env.PROXY_ENABLED === 'true';
    this.type = process.env.PROXY_TYPE || 'http';
    this.host = process.env.PROXY_HOST || '';
    this.port = process.env.PROXY_PORT || '';
    this.username = process.env.PROXY_USERNAME || '';
    this.password = process.env.PROXY_PASSWORD || '';
    this.country = process.env.PROXY_COUNTRY || '';
    this.sessionId = process.env.PROXY_SESSION_ID || `whago_${Date.now()}`;
    
    this.agent = null;
    
    if (this.enabled) {
      this._initialize();
    }
  }

  /**
   * Inicializa o proxy agent com base nas configurações
   * @private
   */
  _initialize() {
    if (!this.host || !this.port) {
      console.warn('⚠️ Proxy habilitado mas credenciais incompletas. Proxy desabilitado.');
      this.enabled = false;
      return;
    }

    try {
      const proxyUrl = this._buildProxyUrl();
      
      if (this.type === 'socks5') {
        this.agent = new SocksProxyAgent(proxyUrl);
        console.log('✅ Proxy SOCKS5 inicializado:', this._getSafeUrl());
      } else {
        this.agent = new HttpsProxyAgent(proxyUrl);
        console.log('✅ Proxy HTTP/HTTPS inicializado:', this._getSafeUrl());
      }
    } catch (error) {
      console.error('❌ Erro ao inicializar proxy:', error.message);
      this.enabled = false;
    }
  }

  /**
   * Constrói a URL do proxy com autenticação
   * @private
   * @returns {string} URL completa do proxy
   */
  _buildProxyUrl() {
    const protocol = this.type === 'socks5' ? 'socks5' : 'http';
    
    // Monta username com parâmetros adicionais (country, session)
    let username = this.username;
    
    // Smartproxy: user-USERNAME-country-BR-session-SESSION_ID
    if (this.country) {
      username = `${username}-country-${this.country}`;
    }
    if (this.sessionId) {
      username = `${username}-session-${this.sessionId}`;
    }

    // Formato: protocol://username:password@host:port
    if (this.username && this.password) {
      return `${protocol}://${encodeURIComponent(username)}:${encodeURIComponent(this.password)}@${this.host}:${this.port}`;
    }
    
    // Sem autenticação
    return `${protocol}://${this.host}:${this.port}`;
  }

  /**
   * Retorna URL do proxy sem expor senha (para logs)
   * @private
   * @returns {string} URL sanitizada
   */
  _getSafeUrl() {
    const protocol = this.type === 'socks5' ? 'socks5' : 'http';
    return `${protocol}://${this.username}:****@${this.host}:${this.port}`;
  }

  /**
   * Retorna o agent configurado para uso no Baileys
   * @returns {Object|null} Agent do proxy ou null se desabilitado
   */
  getAgent() {
    return this.enabled ? this.agent : null;
  }

  /**
   * Verifica se o proxy está habilitado
   * @returns {boolean}
   */
  isEnabled() {
    return this.enabled;
  }

  /**
   * Retorna informações do proxy (sem expor senha)
   * @returns {Object}
   */
  getInfo() {
    return {
      enabled: this.enabled,
      type: this.type,
      host: this.host,
      port: this.port,
      username: this.username,
      country: this.country,
      sessionId: this.sessionId,
      url: this.enabled ? this._getSafeUrl() : null
    };
  }

  /**
   * Testa a conexão do proxy (opcional, para debug)
   * @returns {Promise<boolean>}
   */
  async testConnection() {
    if (!this.enabled) {
      console.log('ℹ️ Proxy desabilitado, teste ignorado.');
      return true;
    }

    try {
      const https = require('https');
      const url = 'https://api.ipify.org?format=json';
      
      return new Promise((resolve, reject) => {
        const options = {
          agent: this.agent,
          timeout: 10000
        };

        https.get(url, options, (res) => {
          let data = '';
          res.on('data', (chunk) => data += chunk);
          res.on('end', () => {
            try {
              const json = JSON.parse(data);
              console.log('✅ Proxy funcionando! IP público:', json.ip);
              resolve(true);
            } catch (e) {
              reject(new Error('Resposta inválida do teste de proxy'));
            }
          });
        }).on('error', (err) => {
          console.error('❌ Teste de proxy falhou:', err.message);
          reject(err);
        });
      });
    } catch (error) {
      console.error('❌ Erro ao testar proxy:', error.message);
      return false;
    }
  }

  /**
   * Atualiza o session ID (útil para rotação de IP)
   * @param {string} newSessionId
   */
  updateSessionId(newSessionId) {
    this.sessionId = newSessionId;
    if (this.enabled) {
      this._initialize(); // Reinicializa com novo session ID
    }
  }

  /**
   * Desabilita o proxy temporariamente
   */
  disable() {
    this.enabled = false;
    this.agent = null;
    console.log('⚠️ Proxy desabilitado manualmente.');
  }

  /**
   * Reabilita o proxy
   */
  enable() {
    this.enabled = true;
    this._initialize();
  }
}

// Exporta instância singleton
module.exports = new ProxyManager();

