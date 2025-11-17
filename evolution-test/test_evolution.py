#!/usr/bin/env python3
"""
TESTE EVOLUTION API - Módulo Independente
Testa Evolution API com TODAS as camadas de proteção
"""

import os
import sys
import time
import json
import uuid
import random
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

PROXY_HOST = os.getenv("PROXY_HOST", "gw.dataimpulse.com")
PROXY_PORT = os.getenv("PROXY_PORT", "824")
PROXY_USER = os.getenv("PROXY_USER", "b0d7c401317486d2c3e8__cr.br")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "f60a2f1e36dcd0b4")
PROXY_TYPE = os.getenv("PROXY_TYPE", "socks5")

EVOLUTION_URL = os.getenv("SERVER_URL", "http://localhost:8080")
EVOLUTION_KEY = os.getenv("AUTHENTICATION_API_KEY", "evolution-test-key-2025")

FINGERPRINTS_FILE = "fingerprints.json"
REPORT_FILE = "test_report.json"

# ============================================================================
# CLASSES DE RELATÓRIO
# ============================================================================

class TestReport:
    def __init__(self):
        self.timestamp = datetime.now().isoformat()
        self.steps = []
        self.metrics = {
            "proxy_validated": False,
            "fingerprint_applied": False,
            "instance_created": False,
            "qr_generated": False,
            "error_405_occurred": False,
            "connection_successful": False,
            "message_sent": False
        }
        self.errors = []
        self.conclusion = "INCONCLUSIVO"
    
    def add_step(self, step: str, status: str, details: str = ""):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "details": details
        }
        self.steps.append(entry)
        print(f"[{status}] {step}: {details}")
    
    def add_error(self, error: str):
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "error": error
        })
        print(f"❌ ERRO: {error}")
    
    def set_conclusion(self, conclusion: str):
        self.conclusion = conclusion
        print(f"\n🎯 CONCLUSÃO: {conclusion}\n")
    
    def save(self):
        report = {
            "timestamp": self.timestamp,
            "steps": self.steps,
            "metrics": self.metrics,
            "errors": self.errors,
            "conclusion": self.conclusion
        }
        with open(REPORT_FILE, "w") as f:
            json.dump(report, f, indent=2)
        print(f"📄 Relatório salvo: {REPORT_FILE}")
        return report

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def load_fingerprints() -> list:
    """Carrega fingerprints do arquivo JSON"""
    try:
        with open(FINGERPRINTS_FILE, "r") as f:
            data = json.load(f)
            return data.get("devices", [])
    except Exception as e:
        print(f"❌ Erro ao carregar fingerprints: {e}")
        return []

def get_random_fingerprint() -> Dict:
    """Seleciona um fingerprint aleatório"""
    devices = load_fingerprints()
    if not devices:
        return {}
    return random.choice(devices)

def generate_session_id() -> str:
    """Gera ID de sessão único"""
    return f"evolution_test_{uuid.uuid4().hex[:8]}"

def build_proxy_url(session_id: str) -> str:
    """Constrói URL do proxy (DataImpulse não suporta session ID)"""
    # DataImpulse não suporta rotação via -session_X, usar credencial direta
    return f"{PROXY_TYPE}://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"

def test_proxy_connection(proxy_url: str) -> Tuple[bool, str]:
    """Testa se o proxy está funcionando"""
    try:
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        response = requests.get(
            "https://api.ipify.org?format=json",
            proxies=proxies,
            timeout=10
        )
        if response.status_code == 200:
            ip = response.json().get("ip", "unknown")
            return True, ip
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

# ============================================================================
# FUNÇÕES EVOLUTION API
# ============================================================================

def check_evolution_health() -> bool:
    """Verifica se Evolution API está rodando"""
    try:
        response = requests.get(f"{EVOLUTION_URL}/", timeout=10)
        return response.status_code == 200
    except:
        return False

def create_instance(
    instance_name: str,
    fingerprint: Dict,
    proxy_url: str,
    report: TestReport
) -> Tuple[bool, Optional[Dict]]:
    """Cria instância Evolution com proteções"""
    
    report.add_step("Criando instância", "⏳", f"Nome: {instance_name}")
    
    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_KEY
    }
    
    payload = {
        "instanceName": instance_name,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
        "proxy": proxy_url,
        "chatwoot_account_id": None,
        "chatwoot_token": None,
        "chatwoot_url": None,
        "chatwoot_sign_msg": False,
        "chatwoot_reopen_conversation": False,
        "chatwoot_conversation_pending": False
    }
    
    # Aplicar User-Agent do fingerprint
    if fingerprint.get("user_agent"):
        headers["User-Agent"] = fingerprint["user_agent"]
        report.metrics["fingerprint_applied"] = True
    
    try:
        response = requests.post(
            f"{EVOLUTION_URL}/instance/create",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            report.add_step("Instância criada", "✅", f"Hash: {data.get('hash', 'N/A')}")
            report.metrics["instance_created"] = True
            return True, data
        else:
            report.add_error(f"Falha ao criar instância: HTTP {response.status_code} - {response.text}")
            return False, None
            
    except Exception as e:
        report.add_error(f"Exceção ao criar instância: {e}")
        return False, None

def fetch_qrcode(instance_name: str, report: TestReport) -> Tuple[bool, Optional[str]]:
    """Busca QR Code da instância"""
    
    report.add_step("Buscando QR Code", "⏳", "Aguardando geração...")
    
    headers = {
        "apikey": EVOLUTION_KEY
    }
    
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            time.sleep(3)  # Rate limiting
            
            response = requests.get(
                f"{EVOLUTION_URL}/instance/connect/{instance_name}",
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Verificar erro 405
                if "405" in str(data) or "405" in response.text:
                    report.metrics["error_405_occurred"] = True
                    report.add_error("ERRO 405 DETECTADO!")
                    return False, None
                
                # QR Code encontrado
                if data.get("code") or data.get("base64"):
                    qr_code = data.get("code") or data.get("base64")
                    report.add_step("QR Code gerado", "✅", f"Tamanho: {len(qr_code)} chars")
                    report.metrics["qr_generated"] = True
                    return True, qr_code
                    
            elif response.status_code == 405:
                report.metrics["error_405_occurred"] = True
                report.add_error("ERRO 405 NA RESPOSTA HTTP!")
                return False, None
                
        except Exception as e:
            if "405" in str(e):
                report.metrics["error_405_occurred"] = True
                report.add_error(f"ERRO 405 NA EXCEÇÃO: {e}")
                return False, None
            report.add_error(f"Tentativa {attempt + 1}/{max_attempts}: {e}")
    
    report.add_error("QR Code não gerado após 10 tentativas")
    return False, None

def check_connection_status(instance_name: str, report: TestReport) -> bool:
    """Verifica status da conexão"""
    
    headers = {
        "apikey": EVOLUTION_KEY
    }
    
    try:
        response = requests.get(
            f"{EVOLUTION_URL}/instance/connectionState/{instance_name}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            state = data.get("state", "unknown")
            
            if state == "open":
                report.add_step("Conexão estabelecida", "✅", f"Estado: {state}")
                report.metrics["connection_successful"] = True
                return True
            else:
                report.add_step("Status da conexão", "⏳", f"Estado: {state}")
                return False
                
    except Exception as e:
        report.add_error(f"Erro ao verificar conexão: {e}")
    
    return False

def delete_instance(instance_name: str, report: TestReport):
    """Remove instância (limpeza)"""
    
    headers = {
        "apikey": EVOLUTION_KEY
    }
    
    try:
        response = requests.delete(
            f"{EVOLUTION_URL}/instance/delete/{instance_name}",
            headers=headers,
            timeout=15
        )
        
        if response.status_code in [200, 204]:
            report.add_step("Instância removida", "✅", "Limpeza concluída")
        else:
            report.add_step("Remoção de instância", "⚠️", f"HTTP {response.status_code}")
            
    except Exception as e:
        report.add_error(f"Erro ao remover instância: {e}")

# ============================================================================
# FUNÇÃO PRINCIPAL DE TESTE
# ============================================================================

def run_full_test():
    """Executa teste completo com Evolution API"""
    
    print("=" * 80)
    print("🧪 TESTE EVOLUTION API - MÓDULO INDEPENDENTE")
    print("=" * 80)
    print()
    
    report = TestReport()
    instance_name = None
    
    try:
        # ====================================================================
        # ETAPA 1: Verificar Evolution API
        # ====================================================================
        report.add_step("Verificando Evolution API", "⏳", EVOLUTION_URL)
        
        if not check_evolution_health():
            report.add_error("Evolution API não está respondendo!")
            report.set_conclusion("FALHA: Evolution API offline")
            return report.save()
        
        report.add_step("Evolution API online", "✅", "Servidor respondendo")
        
        # ====================================================================
        # ETAPA 2: Carregar Fingerprint
        # ====================================================================
        report.add_step("Carregando fingerprint", "⏳", "")
        
        fingerprint = get_random_fingerprint()
        if not fingerprint:
            report.add_error("Falha ao carregar fingerprints!")
            report.set_conclusion("FALHA: Fingerprints não disponíveis")
            return report.save()
        
        device_info = f"{fingerprint['manufacturer']} {fingerprint['model']}"
        report.add_step("Fingerprint selecionado", "✅", device_info)
        
        # ====================================================================
        # ETAPA 3: Gerar Session ID e Proxy
        # ====================================================================
        session_id = generate_session_id()
        proxy_url = build_proxy_url(session_id)
        
        report.add_step("Session ID gerado", "✅", session_id)
        report.add_step("Proxy URL construída", "✅", f"{PROXY_HOST}:{PROXY_PORT}")
        
        # ====================================================================
        # ETAPA 4: Validar Proxy
        # ====================================================================
        report.add_step("Validando proxy", "⏳", "Testando conectividade...")
        
        proxy_ok, proxy_result = test_proxy_connection(proxy_url)
        
        if not proxy_ok:
            report.add_error(f"PROXY NÃO FUNCIONA: {proxy_result}")
            report.set_conclusion("FALHA: Proxy DataImpulse com credenciais inválidas")
            return report.save()
        
        report.add_step("Proxy validado", "✅", f"IP: {proxy_result}")
        report.metrics["proxy_validated"] = True
        
        # ====================================================================
        # ETAPA 5: Delay de Segurança (Rate Limiting)
        # ====================================================================
        report.add_step("Rate limiting", "⏳", "Aguardando 30 segundos...")
        time.sleep(30)
        report.add_step("Rate limiting", "✅", "Delay aplicado")
        
        # ====================================================================
        # ETAPA 6: Criar Instância Evolution
        # ====================================================================
        instance_name = session_id
        
        success, instance_data = create_instance(
            instance_name,
            fingerprint,
            proxy_url,
            report
        )
        
        if not success:
            report.set_conclusion("FALHA: Não foi possível criar instância")
            return report.save()
        
        # ====================================================================
        # ETAPA 7: Buscar QR Code
        # ====================================================================
        qr_success, qr_code = fetch_qrcode(instance_name, report)
        
        if not qr_success:
            if report.metrics["error_405_occurred"]:
                report.set_conclusion("FALHA: ERRO 405 PERSISTE COM EVOLUTION API")
            else:
                report.set_conclusion("INCONCLUSIVO: QR Code não gerado, mas sem erro 405")
            return report.save()
        
        # ====================================================================
        # ETAPA 8: Aguardar Conexão (60 segundos)
        # ====================================================================
        report.add_step("Aguardando conexão", "⏳", "Escaneie o QR Code...")
        
        print("\n" + "=" * 80)
        print("📱 ESCANEIE O QR CODE NO WHATSAPP:")
        print("=" * 80)
        print(f"\nQR Code (primeiros 100 chars): {qr_code[:100]}...")
        print("\nAguardando 60 segundos para conexão...\n")
        
        for i in range(12):  # 12 x 5s = 60s
            time.sleep(5)
            
            if check_connection_status(instance_name, report):
                report.set_conclusion("✅ SUCESSO: Evolution API resolveu o problema!")
                return report.save()
            
            print(f"⏳ Aguardando... {(i + 1) * 5}s")
        
        # ====================================================================
        # CONCLUSÃO: Timeout
        # ====================================================================
        report.add_step("Timeout de conexão", "⏳", "60 segundos sem scan")
        report.set_conclusion("INCONCLUSIVO: QR Code gerado mas não foi escaneado")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Teste interrompido pelo usuário")
        report.add_error("Teste interrompido pelo usuário")
        report.set_conclusion("INTERROMPIDO")
        
    except Exception as e:
        print(f"\n\n❌ EXCEÇÃO CRÍTICA: {e}")
        report.add_error(f"Exceção crítica: {e}")
        report.set_conclusion(f"FALHA: {e}")
        
    finally:
        # Limpeza
        if instance_name:
            print("\n🧹 Limpando instância...")
            delete_instance(instance_name, report)
        
        return report.save()

# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    report = run_full_test()
    
    print("\n" + "=" * 80)
    print("📊 RELATÓRIO FINAL")
    print("=" * 80)
    print(json.dumps(report, indent=2))
    
    sys.exit(0 if report["conclusion"].startswith("✅") else 1)

