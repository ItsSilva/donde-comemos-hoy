-- ╔══════════════════════════════════════════════════════════════════╗
-- ║   ¿DÓNDE COMEMOS HOY? — Esquema de Base de Datos Supabase       ║
-- ║   Sistema de Recomendación Grupal de Restaurantes               ║
-- ╚══════════════════════════════════════════════════════════════════╝

-- ─────────────────────────────────────────────────────────────────
-- 1. USUARIOS
--    Cada persona que interactúa con el sistema (vía web o Telegram)
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre          TEXT NOT NULL,
    telegram_id     BIGINT UNIQUE,          -- ID de Telegram (si entra por bot)
    canal_origen    TEXT DEFAULT 'web',     -- 'web' | 'telegram'
    creado_en       TIMESTAMPTZ DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────
-- 2. PERFIL DE PREFERENCIAS DEL USUARIO
--    Vector de preferencias gastronómicas (escala 1–10)
--    Dimensiones: picante, dulce, salado, vegetariano, carne,
--                 rapido, economico, romantico, familiar, social
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS perfiles_usuario (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id      UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    -- Preferencias de sabor/tipo (1-10)
    picante         NUMERIC(4,2) DEFAULT 5,
    dulce           NUMERIC(4,2) DEFAULT 5,
    salado          NUMERIC(4,2) DEFAULT 5,
    vegetariano     NUMERIC(4,2) DEFAULT 5,
    carne           NUMERIC(4,2) DEFAULT 5,
    -- Preferencias de contexto
    precio_max_cop  INTEGER DEFAULT 30000,  -- presupuesto por persona en COP
    distancia_max_m INTEGER DEFAULT 2000,   -- metros de distancia aceptable
    -- Restricciones dietarias
    es_vegetariano  BOOLEAN DEFAULT FALSE,
    es_vegano       BOOLEAN DEFAULT FALSE,
    sin_gluten      BOOLEAN DEFAULT FALSE,
    sin_lactosa     BOOLEAN DEFAULT FALSE,
    sin_mariscos    BOOLEAN DEFAULT FALSE,
    -- Preferencias de ambiente
    acepta_delivery BOOLEAN DEFAULT TRUE,
    prefiere_sentarse BOOLEAN DEFAULT TRUE,
    -- Metadatos de confianza
    num_interacciones INTEGER DEFAULT 0,    -- cuántas veces ha usado el sistema
    creado_en       TIMESTAMPTZ DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(usuario_id)
);

-- ─────────────────────────────────────────────────────────────────
-- 3. GRUPOS
--    Una sesión grupal donde varios usuarios buscan restaurante
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS grupos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre          TEXT,                   -- nombre opcional del grupo
    canal_origen    TEXT DEFAULT 'web',     -- 'web' | 'telegram'
    chat_id         BIGINT,                 -- chat_id de Telegram si aplica
    metodo_agregacion TEXT DEFAULT 'promedio', -- método elegido para esta sesión
    estado          TEXT DEFAULT 'activo',  -- 'activo' | 'completado' | 'cancelado'
    creado_en       TIMESTAMPTZ DEFAULT NOW(),
    completado_en   TIMESTAMPTZ
);

-- ─────────────────────────────────────────────────────────────────
-- 4. MIEMBROS DEL GRUPO
--    Qué usuarios pertenecen a cada grupo en una sesión
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS grupo_miembros (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grupo_id        UUID NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
    usuario_id      UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    -- Restricciones para ESTA sesión (pueden diferir del perfil base)
    presupuesto_sesion INTEGER,            -- NULL = usa el del perfil
    distancia_sesion   INTEGER,            -- NULL = usa el del perfil
    peso_voto       NUMERIC(4,2) DEFAULT 1.0, -- cuánto pesa este usuario (1.0 = igual)
    unido_en        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(grupo_id, usuario_id)
);

-- ─────────────────────────────────────────────────────────────────
-- 5. RESTAURANTES (Base de datos externa enriquecida)
--    Vectores de características en las mismas dimensiones que los
--    perfiles de usuario para poder hacer crossover directo
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS restaurantes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre          TEXT NOT NULL,
    descripcion     TEXT,
    -- Ubicación
    direccion       TEXT,
    ciudad          TEXT DEFAULT 'Cali',
    latitud         NUMERIC(10,7),
    longitud        NUMERIC(10,7),
    -- Características de sabor (1-10, mismo espacio vectorial que perfiles)
    picante         NUMERIC(4,2) DEFAULT 5,
    dulce           NUMERIC(4,2) DEFAULT 5,
    salado          NUMERIC(4,2) DEFAULT 5,
    vegetariano     NUMERIC(4,2) DEFAULT 5,  -- qué tan bueno para vegetarianos
    carne           NUMERIC(4,2) DEFAULT 5,
    -- Características de precio y contexto
    precio_promedio_cop INTEGER,            -- precio promedio por persona
    precio_rango    TEXT,                   -- 'economico'|'medio'|'caro'|'premium'
    -- Tipos de cocina (etiquetas)
    tipo_cocina     TEXT[],                 -- ['colombiana','italiana','sushi',...]
    -- Restricciones dietarias que soporta
    tiene_opciones_vegetarianas BOOLEAN DEFAULT FALSE,
    tiene_opciones_veganas      BOOLEAN DEFAULT FALSE,
    tiene_sin_gluten            BOOLEAN DEFAULT FALSE,
    -- Logística
    hace_delivery   BOOLEAN DEFAULT TRUE,
    tiene_mesas     BOOLEAN DEFAULT TRUE,
    horario_apertura TIME,
    horario_cierre  TIME,
    -- Calificaciones
    rating_google   NUMERIC(3,2),           -- 1.0 - 5.0
    num_resenas     INTEGER DEFAULT 0,
    -- Metadatos
    activo          BOOLEAN DEFAULT TRUE,
    fuente_datos    TEXT DEFAULT 'manual',  -- 'manual'|'google_places'|'rappi'
    creado_en       TIMESTAMPTZ DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────
-- 6. RECOMENDACIONES
--    Log de cada recomendación hecha (para retroalimentación y
--    reentrenamiento del sistema)
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recomendaciones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grupo_id        UUID NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
    restaurante_id  UUID NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    posicion_ranking INTEGER NOT NULL,      -- 1=primera opción, 2=segunda...
    score_similitud  NUMERIC(6,4),          -- similitud coseno del grupo
    score_satisfaccion_min NUMERIC(6,4),    -- score del miembro menos satisfecho
    metodo_usado    TEXT,
    perfil_n_usado  JSONB,                  -- snapshot del vector N del grupo
    creado_en       TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────
-- 7. FEEDBACK
--    Retroalimentación del usuario después de ir al restaurante
--    → Permite aprendizaje continuo del sistema
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recomendacion_id UUID NOT NULL REFERENCES recomendaciones(id) ON DELETE CASCADE,
    usuario_id      UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fue_al_restaurante BOOLEAN,            -- ¿realmente fueron?
    calificacion    INTEGER CHECK (calificacion BETWEEN 1 AND 5),
    comentario      TEXT,
    -- Ajuste de perfil implícito basado en la experiencia
    delta_picante   NUMERIC(4,2),
    delta_dulce     NUMERIC(4,2),
    delta_salado    NUMERIC(4,2),
    delta_vegetariano NUMERIC(4,2),
    delta_carne     NUMERIC(4,2),
    canal_feedback  TEXT DEFAULT 'web',
    creado_en       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(recomendacion_id, usuario_id)
);

-- ─────────────────────────────────────────────────────────────────
-- 8. SESIONES DE INTERACCIÓN
--    Para tracing de conversaciones en web y Telegram
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sesiones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grupo_id        UUID REFERENCES grupos(id) ON DELETE SET NULL,
    usuario_id      UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    canal           TEXT NOT NULL,          -- 'web' | 'telegram'
    estado_conversacion TEXT DEFAULT 'inicio', -- etapa del flujo conversacional
    contexto_json   JSONB,                  -- estado acumulado de la conversación
    creado_en       TIMESTAMPTZ DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────
-- ÍNDICES para consultas frecuentes
-- ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_usuarios_telegram_id   ON usuarios(telegram_id);
CREATE INDEX IF NOT EXISTS idx_perfiles_usuario_id    ON perfiles_usuario(usuario_id);
CREATE INDEX IF NOT EXISTS idx_grupo_miembros_grupo   ON grupo_miembros(grupo_id);
CREATE INDEX IF NOT EXISTS idx_grupo_miembros_usuario ON grupo_miembros(usuario_id);
CREATE INDEX IF NOT EXISTS idx_recomendaciones_grupo  ON recomendaciones(grupo_id);
CREATE INDEX IF NOT EXISTS idx_feedback_usuario       ON feedback(usuario_id);
CREATE INDEX IF NOT EXISTS idx_restaurantes_ciudad    ON restaurantes(ciudad);
CREATE INDEX IF NOT EXISTS idx_restaurantes_activo    ON restaurantes(activo);
CREATE INDEX IF NOT EXISTS idx_sesiones_canal         ON sesiones(canal);

-- ─────────────────────────────────────────────────────────────────
-- FUNCIÓN: Actualizar timestamp automáticamente
-- ─────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION actualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_usuarios_updated
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp();

CREATE OR REPLACE TRIGGER trg_perfiles_updated
    BEFORE UPDATE ON perfiles_usuario
    FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp();

CREATE OR REPLACE TRIGGER trg_restaurantes_updated
    BEFORE UPDATE ON restaurantes
    FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp();

CREATE OR REPLACE TRIGGER trg_sesiones_updated
    BEFORE UPDATE ON sesiones
    FOR EACH ROW EXECUTE FUNCTION actualizar_timestamp();

-- ─────────────────────────────────────────────────────────────────
-- DATOS SEMILLA — Restaurantes de Cali (base externa)
--    Vectores alineados con perfiles de usuario:
--    [picante, dulce, salado, vegetariano, carne]
-- ─────────────────────────────────────────────────────────────────
INSERT INTO restaurantes (nombre, descripcion, ciudad, tipo_cocina,
    picante, dulce, salado, vegetariano, carne,
    precio_promedio_cop, precio_rango,
    tiene_opciones_vegetarianas, tiene_opciones_veganas,
    hace_delivery, tiene_mesas, rating_google, fuente_datos)
VALUES
    ('La Estación de los Carros',   'Parrilla y cortes en ambiente retro',          'Cali', ARRAY['colombiana','parrilla'],        3, 2, 8, 2, 10, 45000, 'medio',   FALSE, FALSE, FALSE, TRUE,  4.5, 'manual'),
    ('Verde Vital',                  'Restaurante vegano y vegetariano saludable',   'Cali', ARRAY['vegana','saludable'],            2, 5, 5, 10, 1,  22000, 'economico', TRUE, TRUE,  TRUE,  TRUE,  4.6, 'manual'),
    ('El Buen Gusto',               'Comida casera colombiana tradicional',          'Cali', ARRAY['colombiana'],                   4, 4, 7, 5, 8,  18000, 'economico', TRUE, FALSE, FALSE, TRUE,  4.3, 'manual'),
    ('Sushi Maki Cali',             'Sushi y fusión japonesa',                       'Cali', ARRAY['japonesa','sushi'],             4, 6, 7, 6, 6,  38000, 'medio',   TRUE, FALSE, TRUE,  TRUE,  4.4, 'manual'),
    ('Picante & Fuego',             'Cocina mexicana auténtica y picante',           'Cali', ARRAY['mexicana'],                     9, 3, 7, 6, 7,  28000, 'economico', TRUE, FALSE, TRUE,  TRUE,  4.2, 'manual'),
    ('La Cucina di Roma',           'Pasta artesanal e italiana clásica',            'Cali', ARRAY['italiana'],                     2, 5, 7, 7, 6,  35000, 'medio',   TRUE, FALSE, TRUE,  TRUE,  4.5, 'manual'),
    ('Fogón Vallecaucano',          'Sancocho y platos típicos del Valle',           'Cali', ARRAY['colombiana','regional'],        3, 3, 8, 4, 9,  16000, 'economico', FALSE, FALSE, FALSE, TRUE,  4.1, 'manual'),
    ('Dulce Mar',                    'Mariscos frescos y ceviches',                  'Cali', ARRAY['mariscos','pescado'],           5, 2, 8, 3, 7,  32000, 'medio',   FALSE, FALSE, FALSE, TRUE,  4.4, 'manual'),
    ('Street Burger Co.',           'Hamburguesas artesanales estilo gourmet',       'Cali', ARRAY['hamburguesas','americana'],     4, 4, 8, 3, 9,  24000, 'economico', FALSE, FALSE, TRUE,  TRUE,  4.3, 'manual'),
    ('Namaste India',               'Cocina hindú auténtica, rica en especias',      'Cali', ARRAY['india'],                        8, 5, 6, 8, 5,  30000, 'medio',   TRUE, TRUE,  FALSE, TRUE,  4.6, 'manual'),
    ('El Rincón del Taco',          'Tacos y burritos estilo Guadalajara',           'Cali', ARRAY['mexicana','tacos'],             7, 2, 8, 5, 8,  20000, 'economico', TRUE, FALSE, TRUE,  TRUE,  4.2, 'manual'),
    ('Terracita Mediterránea',      'Hummus, falafel, kebab y platillos griegos',    'Cali', ARRAY['mediterranea','arabe'],         3, 4, 7, 8, 6,  29000, 'medio',   TRUE, TRUE,  FALSE, TRUE,  4.5, 'manual'),
    ('Wok House',                   'Wok asiático con opciones thai y chino',        'Cali', ARRAY['asiatica','thai','china'],      6, 5, 7, 7, 6,  26000, 'economico', TRUE, FALSE, TRUE,  TRUE,  4.3, 'manual'),
    ('Grillmaster',                 'Asados a la leña, costillas y chorizos',        'Cali', ARRAY['parrilla','americana'],         3, 2, 9, 1, 10, 40000, 'medio',   FALSE, FALSE, FALSE, TRUE,  4.4, 'manual'),
    ('Café Botánico',               'Brunch saludable, bowls y ensaladas',           'Cali', ARRAY['saludable','brunch'],           1, 6, 5, 9, 3,  22000, 'economico', TRUE, TRUE,  FALSE, TRUE,  4.7, 'manual'),
    ('Pizzería Nápoles',            'Pizza al horno de leña, estilo napolitano',     'Cali', ARRAY['italiana','pizza'],             2, 5, 7, 6, 7,  27000, 'economico', TRUE, FALSE, TRUE,  TRUE,  4.4, 'manual'),
    ('Thai Garden',                 'Curries thai, pad thai y sopas exóticas',       'Cali', ARRAY['thai'],                         7, 6, 6, 7, 6,  31000, 'medio',   TRUE, FALSE, FALSE, TRUE,  4.5, 'manual'),
    ('Asadero El Criollo',          'Pollo asado y bandeja paisa completa',          'Cali', ARRAY['colombiana','asadero'],         3, 2, 8, 3, 9,  15000, 'economico', FALSE, FALSE, FALSE, TRUE,  4.1, 'manual'),
    ('Crepes & Pancakes',           'Crepes dulces y salados, desayunos festivos',   'Cali', ARRAY['francesa','crepes'],            2, 8, 5, 7, 4,  23000, 'economico', TRUE, FALSE, TRUE,  TRUE,  4.3, 'manual'),
    ('El Samán Grill',              'Cortes premium, vinos y ambiente ejecutivo',    'Cali', ARRAY['parrilla','premium'],           2, 2, 8, 2, 10, 65000, 'premium',  FALSE, FALSE, FALSE, TRUE,  4.7, 'manual')
ON CONFLICT DO NOTHING;
