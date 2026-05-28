# Guía de Integración n8n + Telegram Bot
# ¿Dónde comemos hoy? · v2

## Arquitectura general

```
Usuario en Telegram
       │  escribe mensaje
       ▼
[Telegram Trigger — n8n]
       │  extrae chat_id, user_id, username, texto
       ▼
[HTTP Request — n8n]  ──POST──▶  http://localhost:5000/telegram/mensaje
       │                          Body: {chat_id, user_id, username, texto}
       │
       │  Respuesta: {respuesta, chat_id, listo}
       ▼
[Telegram → Send Message — n8n]
       │  Chat ID: {{ $json.chat_id }}
       │  Text:    {{ $json.respuesta }}
       ▼
Usuario recibe la respuesta
```

---

## Paso 1 — Crear el bot en Telegram

1. Abre Telegram y busca **@BotFather**
2. Envía `/newbot`
3. Dale un nombre: `Dónde comemos hoy`
4. Dale un username: `donde_comemos_hoy_bot` (debe terminar en `bot`)
5. Copia el **token** que te da BotFather — lo necesitas en n8n

---

## Paso 2 — Configurar credencial de Telegram en n8n

1. En n8n: **Settings → Credentials → New → Telegram API**
2. Pega el token del bot
3. Guarda como `Telegram Bot Token`

---

## Paso 3 — Crear el flujo en n8n

Crea un flujo nuevo con estos 3 nodos:

---

### Nodo 1: Telegram Trigger

| Campo | Valor |
|-------|-------|
| Credential | Telegram Bot Token |
| Event | Message |
| Updates | message |

---

### Nodo 2: HTTP Request (llama a Flask)

| Campo | Valor |
|-------|-------|
| Method | POST |
| URL | `http://localhost:5000/telegram/mensaje` |
| Body Content Type | JSON |
| Specify Body | Using JSON |

**Body JSON:**
```json
{
  "chat_id":  "={{ $json.message.chat.id }}",
  "user_id":  "={{ $json.message.from.id }}",
  "username": "={{ $json.message.from.first_name }}",
  "texto":    "={{ $json.message.text }}"
}
```

> ⚠️ Si Flask corre en otro puerto o servidor, cambia la URL.
> Para producción en Railway/Render: `https://tu-app.railway.app/telegram/mensaje`

---

### Nodo 3: Telegram — Send Message

| Campo | Valor |
|-------|-------|
| Credential | Telegram Bot Token |
| Operation | Send Message |
| Chat ID | `={{ $json.chat_id }}` |
| Text | `={{ $json.respuesta }}` |
| Parse Mode | Markdown |

---

## Paso 4 — Activar el flujo

1. Haz clic en **Active** (toggle arriba a la derecha)
2. Asegúrate de que Flask esté corriendo: `python app.py`
3. Prueba en Telegram escribiendo `/start` al bot

---

## Paso 5 — Exponer Flask a internet (para que n8n cloud lo alcance)

### Opción A — ngrok (para desarrollo / demo)
```bash
ngrok http 5000
```
Copia la URL HTTPS que te da ngrok (ej: `https://abc123.ngrok.io`)
y úsala en el Nodo 2 en lugar de `localhost:5000`.

### Opción B — n8n local (si n8n corre en la misma máquina)
Usa directamente `http://localhost:5000` — no necesitas ngrok.

### Opción C — Railway / Render (producción)
Haz deploy de `app.py` en Railway o Render y usa la URL pública.

---

## Flujo completo de conversación

```
Usuario:  /start
Bot:      ¡Bienvenidos! ¿Cómo se llama el grupo?

Usuario:  Almuerzo de trabajo
Bot:      ✅ Grupo: Almuerzo de trabajo
          ¿Cuántas personas van? (1 a 8)

Usuario:  3
Bot:      Perfecto, 3 personas 👍
          Integrante 1 de 3
          ¿Cuál es su nombre?

Usuario:  Camila
Bot:      Hola Camila 👋 (1/3)
          🌶️ ¿Cuánto te gusta lo picante? (1-10)

Usuario:  3
Bot:      🍰 ¿Qué tanto disfrutas los sabores dulces? (1-10)

[... 3 preguntas más ...]

Bot:      💰 ¿Cuánto estás dispuesto a gastar por persona?

Usuario:  28000
Bot:      ⚠️ ¿Tienes alguna restricción alimentaria?

Usuario:  vegetariano
Bot:      ✅ Camila registrada
          Integrante 2 de 3 ...

[... repite para Juan y Sofi ...]

Bot:      📋 Grupo: Almuerzo de trabajo (3 personas)
          [resumen del grupo]
          ¿Quieres que busque restaurantes?

Usuario:  sí
Bot:      🎉 ¡Recomendaciones!
          🥇 Verde Vital ...
          🥈 Terracita Mediterránea ...
          🥉 Café Botánico ...

[... días después ...]

Usuario:  /feedback
Bot:      ⭐ ¿A cuál restaurante fueron?
          1. Verde Vital
          2. Terracita Mediterránea
          3. Café Botánico

Usuario:  1
Bot:      ¿Cómo calificarías la visita? (1-5)

Usuario:  5
Bot:      ¿Algún comentario?

Usuario:  Excelente, la ensalada de quinoa increíble
Bot:      ✅ ¡Gracias por tu feedback!
```

---

## Reconfiguración de integrantes (criterio del 30%)

En cualquier momento antes de confirmar el grupo:

```
Usuario:  /modificar Camila
Bot:      Vamos a actualizar el perfil de Camila.
          🌶️ ¿Cuánto te gusta lo picante? (1-10)
[... flujo completo de nuevo para Camila ...]
Bot:      [vuelve al resumen del grupo actualizado]
```

---

## Verificación rápida del endpoint

```bash
curl -X POST http://localhost:5000/telegram/mensaje \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 999, "user_id": 999, "username": "Test", "texto": "/start"}'
```

Respuesta esperada:
```json
{
  "chat_id": 999,
  "listo": false,
  "respuesta": "🍽️ *¡Bienvenidos a ¿Dónde comemos hoy?!*..."
}
```

---

## Estructura de archivos relevante

```
donde_comemos/
├── api/
│   ├── servidor.py          ← API REST (endpoints web)
│   └── telegram_handler.py  ← Handler Telegram (este módulo)
├── app.py                   ← Punto de entrada (registra ambos blueprints)
└── scripts/
    └── n8n_webhook.md       ← Esta guía
```

---

## Checklist para la demo

- [ ] Bot creado en BotFather y token copiado
- [ ] Credencial Telegram configurada en n8n
- [ ] Flujo n8n con 3 nodos (Trigger → HTTP Request → Send Message)
- [ ] Flask corriendo: `python app.py`
- [ ] Flask accesible desde n8n (ngrok si es necesario)
- [ ] Prueba completa: `/start` → grupo de 3 personas → recomendación
- [ ] Prueba de `/modificar` → cambia un integrante → nueva recomendación
- [ ] Prueba de `/feedback` → guarda en Supabase
- [ ] Portal web también funcionando en `http://localhost:5000`