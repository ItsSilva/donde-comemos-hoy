# Fix Supabase persistence

Cambios aplicados:

- `/recomendar` y `/recomendar/auto` ahora guardan:
  - `usuarios`
  - `perfiles_usuario`
  - `grupo_miembros`
  - `grupos`
  - `recomendaciones`
  - `sesiones`

- `guardar_recomendacion()` ahora devuelve los IDs insertados.
- El frontend recibe `recomendacion_id` por restaurante.
- Cada tarjeta de restaurante ahora tiene un formulario de feedback rápido que guarda en `feedback`.

Para probar:
1. Detén Flask si estaba corriendo: `Ctrl + C`
2. Vuelve a correr: `python app.py`
3. Abre `http://localhost:5000`
4. Carga demo o crea integrantes
5. Haz clic en `Recomendar lugar`
6. Revisa en Supabase: `usuarios`, `perfiles_usuario`, `grupo_miembros`, `grupos`, `recomendaciones`, `sesiones`
7. En una tarjeta, envía feedback y revisa la tabla `feedback`
