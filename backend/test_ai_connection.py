
import os
import google.generativeai as genai

# API Key hardcoded para teste isolado (a mesma que você configurou)
API_KEY = "AIzaSyB-xy1wUh7HyCFt1HcmzdTatOYw1pcSXPw"

def test_models():
    print(f"Configurando com API Key: {API_KEY[:5]}...")
    genai.configure(api_key=API_KEY)
    
    print("\n1. Listando modelos disponíveis:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
    except Exception as e:
        print(f"ERRO ao listar modelos: {e}")
        return

    print("\n2. Testando geração com 'gemini-1.5-flash':")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Teste de conexão.")
        print(f"SUCESSO: {response.text}")
    except Exception as e:
        print(f"FALHA com gemini-1.5-flash: {e}")

    print("\n2. Testando geração com 'gemini-pro':")
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Teste de conexão.")
        print(f"SUCESSO: {response.text}")
    except Exception as e:
        print(f"FALHA com gemini-pro: {e}")

if __name__ == "__main__":
    test_models()

