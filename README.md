# Sistema de Detecção de Veículos de Emergência - Frontend

Frontend web para o Sistema de Identificação Inteligente de Veículos de Emergência (IIVE), desenvolvido com Flask e integrado com a API de detecção de veículos.

## 📋 Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Ambiente virtual Python (venv)

## 🚀 Instalação e Execução

### 1. Clonar ou Descompactar o Projeto

```bash
cd emergency_vehicle_frontend
```

### 2. Criar e Ativar o Ambiente Virtual

**No Linux/macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**No Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar as Dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env` e configure conforme necessário:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:

```
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=sua-chave-secreta-aqui
API_BASE_URL=http://localhost:8000/api/v1
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### 5. Executar a Aplicação

```bash
python app.py
```

A aplicação estará disponível em `http://localhost:5000`

## 🔐 Credenciais Padrão

Para fazer login, utilize as credenciais do usuário administrador criado no backend:

- **Email:** admin@example.com
- **Senha:** admin123

> **Nota:** Certifique-se de que o backend está rodando em `http://localhost:8000` antes de iniciar o frontend.


## 🎯 Funcionalidades Principais

### 1. Autenticação
- Login com email e senha
- Gerenciamento de sessões com JWT
- Logout seguro

### 2. Detecção de Veículos
- **Upload de Imagem:** Detectar veículos de emergência em imagens estáticas
- **Upload de Vídeo:** Processar vídeos e acompanhar o status do processamento

### 3. Gerenciamento de Funcionários
- Listar todos os funcionários
- Visualizar detalhes de um funcionário
- Editar informações de um funcionário
- Deletar funcionários (apenas administradores)

### 4. Relatórios
- **Relatório de Tráfego:** Estatísticas de detecções por período
- **Relatório de Detecções:** Análise detalhada de detecções por tipo de veículo

## 📄 Licença

Este projeto é parte do trabalho de conclusão de curso e está disponível para fins educacionais e de pesquisa.
