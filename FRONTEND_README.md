# Frontend — ¿Dónde comemos hoy?

Portal web visual para el proyecto final. Está hecho como SPA simple con HTML, CSS y JavaScript, conectada a la API Flask existente.

## Archivos nuevos

```txt
frontend/
├── index.html
├── styles.css
└── script.js
```

También se actualizó `api/servidor.py` para servir la página en `/`.

## Cómo correrlo

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Corre el servidor:

```bash
python app.py
```

3. Abre el portal:

```txt
http://localhost:5000
```

## Qué hace

- Captura integrantes del grupo.
- Permite ajustar preferencias en las cinco dimensiones del motor:
  - picante
  - dulce
  - salado
  - vegetariano
  - carne
- Permite restricciones alimentarias.
- Permite seleccionar método de agregación:
  - mayoría ponderada
  - promedio
  - mínima miseria
  - media satisfacción
- Hace `POST /recomendar`.
- Muestra perfil N, ranking de restaurantes, score grupal y satisfacción mínima.
- Hace `POST /comparar-metodos` para apoyar la reflexión crítica.

## Estilo visual

Inspirado en la referencia compartida:
- Paleta principal burgundy, crema, rosa suave, azul claro y verde oliva.
- Tipografía editorial para títulos.
- Tarjetas redondeadas, botones tipo pill, navegación inferior móvil.
- Sensación mobile-first / app de estilo moodboard.
