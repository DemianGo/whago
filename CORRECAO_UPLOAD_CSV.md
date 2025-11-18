# ✅ Correção: Upload de CSV de Contatos para Campanhas

## 🐛 Problema Identificado

O sistema **não processava arquivos CSV sem cabeçalho**, resultando em:
- 0 contatos válidos
- 0 inválidos
- 0 duplicados

### Exemplo de arquivo problemático:
```csv
+5511964416417,+5511963076830
```

## 🔧 Solução Implementada

O código agora **detecta automaticamente** se o CSV possui cabeçalho ou não:

### ✅ Lógica de Detecção:
1. Verifica se a primeira linha contém palavras-chave: `numero`, `number`, `telefone`, `phone`, `nome`, `name`
2. **Se encontrar** → Processa como CSV com cabeçalho (`csv.DictReader`)
3. **Se NÃO encontrar** → Processa como CSV simples, cada campo é um número (`csv.reader`)

## 📋 Formatos Suportados

### Formato 1: CSV sem cabeçalho (NOVO! ✅)
```csv
+5511964416417,+5511963076830
+5511999999999,+5511888888888
```

**Comportamento:**
- Cada campo (separado por vírgula) é tratado como um número de telefone
- Nome e empresa ficam como `null`
- Total de contatos: **4**

---

### Formato 2: CSV com cabeçalho (já suportado)
```csv
numero,nome,empresa
+5511964416417,João Silva,Empresa A
+5511963076830,Maria Santos,Empresa B
```

**Comportamento:**
- Usa as colunas: `numero`/`number`/`telefone`/`phone` para o número
- `nome`/`name` para o nome
- `empresa`/`company` para a empresa
- Outras colunas viram variáveis customizadas
- Total de contatos: **2**

---

### Formato 3: CSV com uma coluna (sem cabeçalho)
```csv
+5511964416417
+5511963076830
+5511999999999
```

**Comportamento:**
- Cada linha é um número de telefone
- Total de contatos: **3**

---

### Formato 4: CSV multilinha com cabeçalho
```csv
numero,nome,empresa,cidade,produto
+5511964416417,João Silva,Empresa A,São Paulo,Produto X
+5511963076830,Maria Santos,Empresa B,Rio de Janeiro,Produto Y
```

**Comportamento:**
- `cidade` e `produto` viram variáveis customizadas
- Podem ser usadas em templates com `{{cidade}}` e `{{produto}}`
- Total de contatos: **2**

## 🧪 Teste

### Arquivo de teste criado:
```bash
# Sem cabeçalho
/tmp/test_phones.csv
+5511964416417,+5511963076830

# Com cabeçalho
/tmp/test_phones_with_header.csv
numero,nome
+5511964416417,João Silva
+5511963076830,Maria Santos
```

## 📝 Alterações no Código

**Arquivo:** `backend/app/services/campaign_service.py`  
**Método:** `upload_contacts()`

### Mudanças:
1. ✅ Detecção automática de cabeçalho
2. ✅ Suporte para CSV sem cabeçalho
3. ✅ Processamento de múltiplos números por linha
4. ✅ Compatibilidade mantida com formato antigo

### Palavras-chave de cabeçalho detectadas:
- `numero`, `number` → Número de telefone
- `telefone`, `phone` → Número de telefone (alternativa)
- `nome`, `name` → Nome do contato
- `empresa`, `company` → Empresa
- Outras colunas → Variáveis customizadas

## 🎯 Resultado Esperado

Ao fazer upload do arquivo `phone.csv` com conteúdo:
```
+5511964416417,+5511963076830
```

O sistema agora exibe:
```
✅ 2 contatos válidos · 0 inválidos · 0 duplicados
```

E o botão **"Enviar Campanha"** fica habilitado!

---

## 🚀 Status

✅ **Correção aplicada**  
✅ **Backend reiniciado**  
✅ **Pronto para teste no frontend**

