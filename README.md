# 🛡️ Sure Agent

> Make **SURE** your compliance is grounded.

Chatbot de cumplimiento regulatorio impulsado por **Azure AI Foundry**, con interfaz web en **Streamlit** y despliegue local con **Docker**.

---

## ✨ Características

- 💬 **Chat interactivo** con agente de Azure AI Foundry
- ⌨️ **Streaming** de respuestas palabra por palabra (typewriter effect)
- 📎 **Citas con fuentes** — referencias a documentos con nombres de archivo
- 🔄 **Hot-reload** — cambios en el código se reflejan sin reiniciar
- 🐳 **Dockerizado** — un solo comando para levantar todo

---

## 📁 Estructura del Proyecto

```
Sure/
├── app.py                  # UI (Streamlit chat)
├── src/
│   ├── __init__.py
│   ├── config.py           # Variables de entorno
│   ├── auth.py             # Credenciales Azure
│   ├── agent.py            # Cliente AI Foundry
│   └── citations.py        # Procesamiento de citas
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env / .env.example
└── .dockerignore
```

---

## 🚀 Inicio Rápido

### Pre-requisitos

| Herramienta | Verificar |
|---|---|
| Docker Desktop ≥ 24.x | `docker --version` |
| Docker Compose v2 | `docker compose version` |

### 1. Clonar y configurar

```bash
git clone https://github.com/santiagoreyb/Sure.git
cd Sure
cp .env.example .env
```

Edita `.env` con tus credenciales:

```dotenv
AZURE_AI_CONNECTION_STRING=eastus2.api.azureml.ms;TU_SUBSCRIPTION;rg-sure;sure
AZURE_AI_AGENT_ID=asst_XXXXXXXXXXXXXXXXXXXX
```

### 2. Levantar

```bash
docker compose up --build
```

### 3. Autenticación

En los logs de Docker aparecerá:

```
To sign in, open https://login.microsoft.com/device and enter the code XXXXXXX
```

Abre la URL, ingresa el código y selecciona tu cuenta Azure.

### 4. Usar

Abre **http://localhost:8501** y empieza a chatear.

---

## 🔧 Desarrollo

### Hot-Reload

El código fuente se monta como volumen. Cambios en `app.py` o `src/*.py` se reflejan automáticamente sin reiniciar.

> Solo cambios en `requirements.txt` requieren rebuild: `docker compose up --build`

### Comandos útiles

| Acción | Comando |
|---|---|
| Levantar (background) | `docker compose up -d --build` |
| Ver logs | `docker compose logs -f sure-bot` |
| Detener | `docker compose down` |
| Rebuild forzado | `docker compose build --no-cache` |

---

## 🌐 Despliegue en Azure App Service

Para producción, usa **Managed Identity** (sin secretos):

```bash
# Habilitar Managed Identity
az webapp identity assign --name <app-name> --resource-group rg-sure

# Dar acceso al AI Hub
az role assignment create \
    --assignee <principalId> \
    --role "Contributor" \
    --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-sure
```

Solo configura `AZURE_AI_CONNECTION_STRING` y `AZURE_AI_AGENT_ID` en App Service → Configuration → Application Settings.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Frontend | Streamlit |
| Agente IA | Azure AI Foundry (Assistants API) |
| LLM | GPT-4o-mini |
| Autenticación | `DeviceCodeCredential` (local) / `ManagedIdentity` (prod) |
| Contenedor | Docker + Docker Compose |

---

## 📄 Licencia

Proyecto privado – © Sure
