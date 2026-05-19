# n8n_webhook.md — Guía de Integración con n8n + Telegram Bot
# ¿Dónde comemos hoy?

## Resumen del flujo

```
Usuario en Telegram
      │
      ▼
[Telegram Trigger - n8n]
      │  chat_id, user_id, username, texto
      ▼
[HTTP Request - n8n]  ──POST──▶  http://SERVIDOR:5000/telegram/mensaje
      │                           {chat_id, user_id, username, texto}
      │  respuesta: {respuesta, chat_id, listo}
      ▼
[Telegram → Send Message]
      │  Chat ID: {{ $json.chat_id }}
      │  Text:    {{ $json.respuesta }}
      ▼
Usuario recibe la respuesta
```

## Configuración en n8n

### Nodo 1: Telegram Trigger
- Tipo: Telegram Trigger
- Event: Message
- Token: (tu bot token de @BotFather)

### Nodo 2: HTTP Request
- Método: POST
- URL: `http://TU_SERVIDOR:5000/telegram/mensaje`
- Body Type: JSON
- Body:
```json
{
  "chat_id":  "{{ $json.message.chat.id }}",
  "user_id":  "{{ $json.message.from.id }}",
  "username": "{{ $json.message.from.first_name }}",
  "texto":    "{{ $json.message.text }}"
}
```

### Nodo 3: Telegram - Send Message
- Operation: Send Message
- Chat ID: `{{ $json.chat_id }}`
- Text: `{{ $json.respuesta }}`
- Parse Mode: Markdown

## Portal Web (n8n como proxy)

Si el frontend web no llama directo a Flask, puede pasar por n8n:

### Nodo Webhook (n8n)
- Path: /donde-comemos
- HTTP Method: POST

### Nodo HTTP Request (a Flask)
- URL: `http://SERVIDOR:5000/recomendar/auto`
- Body: `{{ $json.body }}`

### Nodo Respond to Webhook
- Response Body: `{{ $json }}`

---

## Estructura completa del proyecto

```
donde_comemos/
├── core/
│   └── motor_recomendacion.py    ← Algoritmos de recomendación
├── data/
│   └── base_datos.py             ← Capa Supabase
├── api/
│   ├── servidor.py               ← Flask REST API (Web)
│   └── telegram_handler.py       ← Handler Telegram (n8n)
├── scripts/
│   └── n8n_webhook.md            ← Esta guía
├── supabase_schema.sql           ← SQL para ejecutar en Supabase
├── demo.py                       ← Demo y pruebas
├── requirements.txt              ← Dependencias
└── .env.example                  ← Variables de entorno
```
