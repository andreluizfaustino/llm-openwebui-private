# 🤖 Private AI Workspace

A fully self-hosted private AI platform built on [Open WebUI](https://github.com/open-webui/open-webui) and [Ollama](https://ollama.com), with a built-in 4-step web setup wizard.

> Everything runs **locally** — no data ever leaves your machine.

---

## What is it

This project packages Open WebUI + Ollama in a Docker Compose environment with an integrated setup wizard that guides the initial configuration:

- Language model (LLM) selection and download
- GPU configuration (NVIDIA, AMD, or CPU-only)
- Access mode (public, login-required, or open registration)

After setup, the wizard redirects to a service monitoring dashboard.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose v2
- For GPU acceleration:
  - **NVIDIA**: drivers installed + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
  - **AMD**: ROCm drivers installed

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/andreluizfaustino/llm-openwebui-private.git
cd llm-openwebui-private

# 2. Copy the initial configuration file
cp config/open-webui.env.example config/open-webui.env

# 3. Start the containers
docker compose up -d
```

Wait about 30–60 seconds for all services to start, then open:

```
http://localhost:3000
```

The setup wizard will open automatically.

---

## Usage

### Setup Wizard (4 steps)

| Step | What it does |
|------|-------------|
| **1 — Welcome** | Introduces the project and checks services |
| **2 — Models** | Selects and downloads LLM models via Ollama |
| **3 — Settings** | Configures GPU, keep-alive, and access mode |
| **4 — Confirm** | Applies settings and waits for Open WebUI to restart |

### Access modes

| Mode | Behaviour |
|------|-----------|
| **Public** | Direct access without login, default user created automatically |
| **Login required** | Requires an account; registration disabled (pre-created accounts only) |
| **Registration enabled** | Anyone can create an account |

> **Note:** If Open WebUI shows a 404 after setup in public mode, open it in a private/incognito window. This happens when the browser has a stale session cookie from a previous installation.

### Dashboard

After setup, visit `http://localhost:3000` to monitor service status, installed models, and active settings.

---

## Reset to factory defaults

To fully reset (deletes all data and downloaded models):

```bash
docker compose down -v
docker compose up -d
```

---

## Default ports

| Service | Port |
|---------|------|
| Setup wizard / Dashboard | `3000` |
| Open WebUI | `8080` |
| Ollama API | `11434` |

Ports can be changed via environment variables before starting:

```bash
SETUP_PORT=3001 WEBUI_PORT=8081 docker compose up -d
```

---

## Project structure

```
├── docker-compose.yml            # Service orchestration
├── config/
│   └── open-webui.env.example    # Config template (copy to open-webui.env)
└── setup/                        # Setup wizard app (FastAPI)
    └── src/
        ├── routers/              # API endpoints and pages
        ├── services/             # Business logic (Docker, Ollama, WebUI)
        └── templates/            # HTML interface (Jinja2 + Tailwind)
```

---

## License

MIT

---
---

# 🤖 Private AI Workspace

Plataforma de IA privada e auto-hospedada com [Open WebUI](https://github.com/open-webui/open-webui) e [Ollama](https://ollama.com), configurável via assistente de instalação web em 4 etapas.

> Toda a execução é **local**: nenhum dado sai da sua máquina.

---

## O que é

Este projeto empacota Open WebUI + Ollama em um ambiente Docker Compose com um assistente de instalação integrado que guia a configuração inicial:

- Seleção e download de modelos de linguagem (LLMs)
- Configuração de GPU (NVIDIA, AMD ou CPU)
- Definição do modo de acesso (público, login obrigatório ou com cadastro)

Após a instalação, o assistente redireciona para um dashboard de monitoramento dos serviços.

---

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) com Docker Compose v2
- Para aceleração por GPU:
  - **NVIDIA**: drivers instalados + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
  - **AMD**: drivers ROCm instalados

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/andreluizfaustino/llm-openwebui-private.git
cd llm-openwebui-private

# 2. Copie o arquivo de configuração inicial
cp config/open-webui.env.example config/open-webui.env

# 3. Suba os containers
docker compose up -d
```

Aguarde cerca de 30–60 segundos para todos os serviços iniciarem e acesse:

```
http://localhost:3000
```

O assistente de instalação abrirá automaticamente.

---

## Como usar

### Assistente de instalação (4 etapas)

| Etapa | O que faz |
|-------|-----------|
| **1 — Boas-vindas** | Apresenta o projeto e verifica os serviços |
| **2 — Modelos** | Seleciona e baixa modelos LLM via Ollama |
| **3 — Configurações** | Define GPU, keep-alive e modo de acesso |
| **4 — Confirmação** | Aplica as configurações e aguarda o Open WebUI reiniciar |

### Modos de acesso

| Modo | Comportamento |
|------|--------------|
| **Público** | Acesso direto sem login, usuário padrão criado automaticamente |
| **Login obrigatório** | Requer conta, cadastro desabilitado (apenas contas pré-criadas) |
| **Cadastro habilitado** | Qualquer pessoa pode criar uma conta |

> **Nota:** Se o Open WebUI mostrar 404 após o setup em modo público, abra em uma janela anônima/privada. Isso ocorre quando o browser tem um cookie de sessão antigo de uma instalação anterior.

### Dashboard

Após a instalação, acesse `http://localhost:3000` para monitorar o status dos serviços, modelos instalados e configurações ativas.

---

## Reiniciar do zero

Para resetar completamente (apaga todos os dados e modelos):

```bash
docker compose down -v
docker compose up -d
```

---

## Portas padrão

| Serviço | Porta |
|---------|-------|
| Assistente de instalação / Dashboard | `3000` |
| Open WebUI | `8080` |
| Ollama API | `11434` |

As portas podem ser alteradas via variáveis de ambiente antes de subir os containers:

```bash
SETUP_PORT=3001 WEBUI_PORT=8081 docker compose up -d
```

---

## Estrutura do projeto

```
├── docker-compose.yml              # Orquestração dos serviços
├── config/
│   └── open-webui.env.example      # Template de configuração (copie para open-webui.env)
└── setup/                          # Aplicação do assistente de instalação (FastAPI)
    └── src/
        ├── routers/                # Endpoints da API e páginas
        ├── services/               # Lógica de negócio (Docker, Ollama, WebUI)
        └── templates/              # Interface HTML (Jinja2 + Tailwind)
```

---

## Licença

MIT
