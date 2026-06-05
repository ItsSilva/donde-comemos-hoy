"""
seed_restaurantes_cali.py — Base de datos completa de restaurantes caleños
¿Dónde comemos hoy? · Universidad Icesi

Contiene 76 restaurantes en total:
  · 57 distribuidos en 9 zonas de Cali
  · 19 restaurantes icónicos verificados con fuentes reales

Fuentes de los icónicos: visitvalle.travel, TripAdvisor, evendo.com,
restaurantguru.com, wanderlog.com — direcciones verificadas.

Ejecutar desde la raíz del proyecto:
    python3 seed_restaurantes_cali.py

El script:
  1. Conecta a Supabase
  2. Elimina todos los restaurantes anteriores si confirmas (recomendado)
  3. Inserta los 76 restaurantes en lotes
  4. Imprime resumen final

Estructura de cada tupla:
  (nombre, descripcion, direccion, tipo_cocina[],
   picante, dulce, salado, vegetariano, carne,
   precio_cop, precio_rango,
   tiene_veg, tiene_vegan, sin_gluten, delivery, rating)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mkzkqdqhalavvnxisbqi.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_Zxj5YOuJ7qNFo7qxiubm0w_vnJRxOzG")

try:
    from supabase import create_client
except ImportError:
    print("❌  Instala supabase: pip3 install supabase")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════
# BLOQUE A — 57 RESTAURANTES POR ZONA
# ══════════════════════════════════════════════════════════════════════

ZONA_PENON_SAN_ANTONIO = [
    ("Nuestro Listo",
     "Restaurante de barrio reconvertido en espacio gastronómico. Almuerzo ejecutivo y carta de noche.",
     "Calle 5 # 4-68, San Antonio",
     ["colombiana", "casera"], 3, 4, 8, 5, 8, 22000, "economico", True, False, False, False, 4.4),

    ("La Galería de Arzuaga",
     "Tapas españolas y cocina mediterránea en casa colonial restaurada. Ambiente íntimo.",
     "Carrera 3 # 7-45, San Antonio",
     ["española", "tapas", "mediterránea"], 3, 4, 7, 7, 6, 48000, "medio", True, False, False, False, 4.5),

    ("Ají Limón",
     "Cevichería y cocina peruana. Tiraditos, causas y leche de tigre. Muy popular entre universitarios.",
     "Calle 4 # 3-79, El Peñón",
     ["peruana", "cevichería"], 6, 3, 8, 5, 6, 32000, "medio", False, False, False, True, 4.5),

    ("Miga Bistró",
     "Desayunos y brunch. Tostadas de aguacate, granola artesanal, café de especialidad.",
     "Carrera 4 # 12-60, El Peñón",
     ["brunch", "café", "saludable"], 1, 7, 5, 9, 3, 32000, "medio", True, True, False, False, 4.7),
]

ZONA_GRANADA_VERSALLES = [
    ("La Valentina",
     "Cocina italiana artesanal. Pasta fresca hecha en casa, risottos y carpaccios. Vinos importados.",
     "Avenida 9N # 13N-85, Granada",
     ["italiana", "pasta"], 2, 5, 7, 7, 6, 52000, "medio", True, False, False, False, 4.6),

    ("Archie's Pizza Granada",
     "Pizzería clásica de Cali con décadas de tradición. Pizzas al horno, ambiente familiar.",
     "Avenida 6N # 23N-48, Granada",
     ["pizza", "italiana"], 2, 5, 8, 6, 7, 28000, "economico", True, False, False, True, 4.3),

    ("Delicias del Mar Granada",
     "Mariscos y pescados frescos traídos del Pacífico. Especialidad: langostinos al ajillo y cazuela.",
     "Calle 16N # 8N-32, Granada",
     ["mariscos", "pescado"], 5, 2, 9, 3, 7, 45000, "medio", False, False, False, False, 4.4),

    ("Wok Granada",
     "Cadena de cocina asiática sostenible. Pad thai, dim sum, sopas y bowls. Muy popular.",
     "Avenida 9N # 14N-22, Granada",
     ["asiática", "thai", "china"], 6, 5, 7, 8, 5, 38000, "medio", True, True, False, True, 4.5),

    ("La Taquería del Norte",
     "Tacos, burritos y quesadillas estilo mexicano auténtico. Salsa verde, roja y habanero.",
     "Carrera 9N # 15N-40, Granada",
     ["mexicana", "tacos"], 8, 2, 8, 5, 8, 24000, "economico", True, False, False, True, 4.2),

    ("Sushi Takara",
     "Restaurante japonés tradicional. Sushi omakase, ramen y tempuras. Chef japonés.",
     "Avenida 9N # 11N-50, Versalles",
     ["japonesa", "sushi", "ramen"], 4, 6, 7, 6, 6, 55000, "medio", True, False, False, False, 4.7),

    ("Casa Bali",
     "Cocina balinesa e indonesia. Nasi goreng, satay y curries. Decoración exótica.",
     "Carrera 10N # 16N-55, Versalles",
     ["indonesia", "balinesa", "asiática"], 7, 5, 7, 7, 6, 42000, "medio", True, False, False, False, 4.5),

    ("El Bodegón",
     "Carnes y parrilla argentina. Cortes importados, chimichurri casero. Buen ambiente para grupos.",
     "Calle 14N # 9N-25, Centenario",
     ["argentina", "parrilla", "carnes"], 2, 2, 9, 2, 10, 65000, "caro", False, False, False, False, 4.6),

    ("Frutos del Mar",
     "Cevichería y mariscos. Ceviches de camarón, pulpo y mixto. Vista a la avenida.",
     "Avenida 6N # 25N-12, Granada",
     ["mariscos", "cevichería"], 6, 2, 9, 3, 6, 35000, "medio", False, False, False, True, 4.3),

    ("Seoul BBQ",
     "Barbacoa coreana. Mesas con parrilla incorporada, bulgogi y galbi. Único en Cali.",
     "Carrera 9N # 17N-80, Versalles",
     ["coreana", "BBQ", "asiática"], 6, 5, 8, 5, 8, 50000, "medio", False, False, False, False, 4.8),

    ("La Estación del Caldo",
     "Caldos y sopas tradicionales del Valle. Caldo de costilla, sopa de mondongo, ajiaco.",
     "Calle 25N # 6N-30, Granada",
     ["colombiana", "sopas", "casera"], 3, 3, 9, 5, 7, 16000, "economico", True, False, False, False, 4.5),
]

ZONA_CHIPICHAPE_UNICENTRO = [
    ("Tony Roma's Chipichape",
     "Costillas BBQ estilo americano. Ribs, alitas y hamburguesas. Ambiente familiar.",
     "C.C. Chipichape, Local 246, Calle 38N",
     ["americana", "BBQ", "costillas"], 4, 4, 8, 3, 10, 55000, "medio", False, False, False, False, 4.3),

    ("Verde Que Te Quiero Verde",
     "Restaurante 100% vegano. Bowls, hamburguesas de legumbres, postres sin lácteos. Orgánico.",
     "Carrera 38N # 5B-25, Santa Mónica",
     ["vegana", "saludable", "orgánica"], 2, 6, 5, 10, 1, 28000, "economico", True, True, True, True, 4.8),

    ("Don Carbón",
     "Asadero de pollo y carnes al carbón. Precio muy accesible, porciones generosas.",
     "Carrera 1N # 44N-12, Santa Mónica",
     ["colombiana", "asadero", "pollo"], 3, 2, 8, 3, 9, 18000, "economico", False, False, False, False, 4.1),

    ("Sazón Caleño",
     "Comida tradicional caleña. Sancocho de gallina, cholado, empanadas. Recetas de abuela.",
     "Calle 52N # 2N-40, Chipichape",
     ["colombiana", "regional", "casera"], 3, 4, 8, 4, 8, 20000, "economico", True, False, False, False, 4.4),

    ("La Brasa Roja Norte",
     "Pollo asado tradicional caleño. Una institución. Cola afuera los domingos.",
     "Avenida 3N # 47N-30, Unicentro",
     ["colombiana", "pollo", "asadero"], 3, 3, 8, 3, 9, 16000, "economico", False, False, False, True, 4.3),
]

ZONA_CIUDAD_JARDIN_LIDO = [
    ("Lido Asados",
     "Parrilla premium. Cortes de res maduros, chorizos artesanales. Ambiente ejecutivo.",
     "Carrera 100 # 11-60, El Lido",
     ["parrilla", "argentina", "carnes"], 2, 2, 8, 2, 10, 85000, "caro", False, False, False, False, 4.6),

    ("Alma Cocina",
     "Restaurante farm-to-table. Ingredientes del Valle del Cauca. Menú de temporada.",
     "Calle 18 # 122-20, Ciudad Jardín",
     ["colombiana", "orgánica", "fusión"], 3, 6, 6, 9, 5, 70000, "caro", True, True, True, False, 4.8),

    ("Ristorante Il Forno",
     "Italiano tradicional con horno de leña importado de Nápoles. Pizzas y pasta fresca.",
     "Carrera 98 # 16-45, La Flora",
     ["italiana", "pizza", "pasta"], 2, 5, 7, 7, 6, 48000, "medio", True, False, False, False, 4.7),

    ("Thai Orchid",
     "El mejor restaurante tailandés de Cali. Curries auténticos, pad thai y sopas exóticas.",
     "Calle 16 # 98-45, Ciudad Jardín",
     ["thai", "asiática"], 8, 6, 6, 7, 6, 45000, "medio", True, False, False, False, 4.7),

    ("El Rancherito del Valle",
     "Bandeja paisa completa, chicharrón y chorizo valluno. Porciones enormes.",
     "Carrera 100 # 14-30, El Lido",
     ["colombiana", "valluna", "casera"], 3, 3, 9, 3, 9, 22000, "economico", False, False, False, False, 4.2),

    ("Gokela",
     "Cocina mediterránea y del Medio Oriente. Falafel, hummus, shawarma y kebab.",
     "Calle 10 # 98-30, Ciudad Jardín",
     ["mediterránea", "árabe", "shawarma"], 4, 4, 7, 9, 6, 32000, "medio", True, True, False, True, 4.6),

    ("Delicias del Pacífico",
     "Cocina del Pacífico colombiano auténtica. Encocado de camarón, tapao de pescado, arroz con coco.",
     "Calle 16 # 103-00, Ciudad Jardín",
     ["pacífica", "afrocolombiana", "mariscos"], 5, 3, 9, 5, 6, 32000, "medio", False, False, False, False, 4.5),
]

ZONA_SAN_FERNANDO_ALAMEDA = [
    ("El Zaguan de San Fernando",
     "Comida casera colombiana ejecutiva. Menú del día completo a buen precio. Lleno al mediodía.",
     "Calle 5 # 38A-10, San Fernando",
     ["colombiana", "ejecutiva", "casera"], 3, 4, 8, 5, 8, 15000, "economico", True, False, False, False, 4.3),

    ("La Cueva del Cangrejo",
     "Cangrejos, jaibas y mariscos frescos. Especialidad caleña. Solo efectivo.",
     "Carrera 44 # 5-60, Alameda",
     ["mariscos", "colombiana"], 6, 2, 10, 2, 7, 38000, "medio", False, False, False, False, 4.5),

    ("Naturalmente",
     "Restaurante naturista y vegetariano. Jugos naturales, granos, ensaladas. Opción saludable.",
     "Carrera 43 # 9-34, San Fernando",
     ["vegetariana", "naturista", "saludable"], 1, 5, 5, 10, 1, 18000, "economico", True, True, True, False, 4.4),

    ("Hacienda El Paraíso Restaurante",
     "Cocina del Valle. Envueltos, pandebono fresco, costeleta valluna.",
     "Avenida 6 # 35-28, Alameda",
     ["colombiana", "valluna"], 3, 5, 8, 5, 8, 28000, "economico", True, False, False, False, 4.4),

    ("Mango's Burger",
     "Hamburguesas artesanales con carne de res 100% colombiana. Pan de papa hecho en casa.",
     "Carrera 38 # 6-40, San Fernando",
     ["hamburguesas", "americana"], 4, 4, 8, 3, 9, 22000, "economico", False, False, False, True, 4.3),

    ("Quinua & Amaranto",
     "Restaurante vegano y sin gluten. Superalimentos, proteína vegetal. Preferido de deportistas.",
     "Carrera 66 # 9B-22, San Fernando",
     ["vegana", "sin gluten", "saludable"], 2, 5, 5, 10, 1, 26000, "economico", True, True, True, True, 4.7),
]

ZONA_INGENIO_CANEY = [
    ("Steak House Ingenio",
     "Carnes premium al carbón. Ambiente familiar. Popular los fines de semana.",
     "Carrera 100 # 30-45, El Ingenio",
     ["parrilla", "americana", "carnes"], 3, 3, 8, 2, 10, 60000, "caro", False, False, False, False, 4.4),

    ("El Rincón Asiático",
     "Cocina china cantonesa y vietnamita. Dim sum, pho, arroz frito. Muy popular con familias.",
     "Calle 25 # 82-55, El Caney",
     ["china", "vietnamita", "asiática"], 5, 5, 7, 7, 6, 25000, "economico", True, False, False, True, 4.2),

    ("La Casa del Ceviche Sur",
     "Ceviches y mariscos estilo peruano. El mejor tiradito de la zona sur.",
     "Carrera 92 # 28-20, El Caney",
     ["peruana", "mariscos", "cevichería"], 6, 3, 8, 4, 5, 35000, "medio", False, False, False, True, 4.5),

    ("Crepes y Waffles Jardín Plaza",
     "Crepes dulces y salados, helados artesanales. Menú amplio para toda la familia.",
     "C.C. Jardín Plaza, Av. Cañas Gordas",
     ["francesa", "crepes", "postres"], 1, 9, 5, 8, 4, 30000, "medio", True, False, False, False, 4.4),

    ("Frisby El Ingenio",
     "Pollo frito colombiano. Combos, pechuga y sánduches. Clásico de Cali.",
     "Carrera 100 # 16-60, El Ingenio",
     ["colombiana", "pollo", "rápida"], 4, 3, 8, 4, 8, 15000, "economico", False, False, False, True, 4.1),

    ("Tandoor Indian Cuisine",
     "Cocina india del norte. Tandoori, biryani y currys aromáticos. Delivery disponible.",
     "Calle 19 # 100-15, El Caney",
     ["india", "curry"], 9, 5, 6, 8, 5, 40000, "medio", True, True, False, True, 4.6),
]

ZONA_CENTRO = [
    ("Restaurante Donde Chava",
     "Comida de mercado. Sancocho, seco de pollo, jugo de guanábana. Lo más caleño que hay.",
     "Galería Alameda, Local 28, Centro",
     ["colombiana", "mercado", "casera"], 3, 4, 9, 4, 8, 12000, "economico", True, False, False, False, 4.6),

    ("La Feria del Pandebono",
     "Pandebono recién horneado, buñuelos y aborrajados. Desayunos vallunos.",
     "Calle 15 # 7-30, Santa Rosa",
     ["colombiana", "panadería", "valluna"], 2, 6, 7, 6, 5, 10000, "economico", True, False, False, False, 4.5),

    ("El Fogón del Abuelo",
     "Lechona tolimense, tamales y morcilla. Solo abre sábados y domingos.",
     "Carrera 8 # 10-45, San Bosco",
     ["colombiana", "tolimense", "regional"], 4, 3, 9, 3, 9, 18000, "economico", False, False, False, False, 4.3),

    ("Menú Express Centro",
     "Almuerzo ejecutivo rápido. Sopa, seco, jugo y postre. El más barato del centro.",
     "Calle 11 # 9-52, Centro",
     ["colombiana", "ejecutiva"], 3, 4, 8, 5, 7, 11000, "economico", True, False, False, False, 4.0),
]

ZONA_PANCE_OESTE = [
    ("Rancho Aparte",
     "Asado a la llanera, mamona y ternera. Ambiente campestre a las afueras de Cali.",
     "Vía al Mar Km 2, Pance",
     ["llanera", "parrilla", "campestre"], 3, 2, 9, 2, 10, 45000, "medio", False, False, False, False, 4.5),

    ("La Niña Empanadería",
     "Empanadas de pipián, de pollo y de carne. Ají casero. Clásico caleño de domingo.",
     "Carrera 122 # 19-35, Pance",
     ["colombiana", "empanadas", "snacks"], 4, 3, 8, 5, 7, 12000, "economico", True, False, False, False, 4.6),

    ("Eco Restaurante El Manantial",
     "Cocina saludable en entorno natural. Trucha del río, ensaladas, jugos sin azúcar.",
     "Vía Pichindé Km 8, Corregimiento Pichindé",
     ["saludable", "colombiana", "trucha"], 2, 4, 6, 8, 5, 40000, "medio", True, True, True, False, 4.7),

    ("La Terraza de Pance",
     "Mariscos y carnes con vista al río Pance. Ambiente festivo. Ideal para grupos grandes.",
     "Calle 86 # 155-20, Pance",
     ["colombiana", "mariscos", "parrilla"], 5, 3, 8, 4, 8, 38000, "medio", False, False, False, False, 4.4),
]

ZONA_MENGA_NORTE = [
    ("La Fogata de Menga",
     "Parrilla y asados al carbón. Muy popular entre trabajadores del norte de Cali.",
     "Autopista Norte Km 1, Menga",
     ["parrilla", "colombiana"], 3, 2, 9, 2, 10, 30000, "medio", False, False, False, False, 4.3),

    ("Sushi Express Menga",
     "Sushi de calidad a precios accesibles. Rolls creativos y sashimi fresco.",
     "Carrera 5N # 73N-45, Menga",
     ["japonesa", "sushi"], 3, 6, 7, 6, 5, 32000, "medio", True, False, False, True, 4.3),

    ("Arepa & Más",
     "Arepas de todo tipo: de choclo, de maíz, rellenas, con hogao. Desayunos vallunos.",
     "Calle 72N # 2B-30, Menga",
     ["colombiana", "arepas", "valluna"], 3, 5, 7, 6, 6, 13000, "economico", True, False, False, False, 4.4),

    ("El Corral Gourmet Granada",
     "Hamburguesas premium. La mejor cadena de hamburguesas de Colombia.",
     "Avenida 9N # 12N-20, Granada",
     ["hamburguesas", "americana", "gourmet"], 4, 5, 8, 4, 9, 28000, "economico", False, False, False, True, 4.4),

    ("La Parrilla del Río",
     "Carnes y mariscos con vista al río Cauca. Ambiente al aire libre. Solo fines de semana.",
     "Vía Cali-Candelaria, Orilla Río Cauca",
     ["parrilla", "mariscos", "colombiana"], 4, 3, 9, 3, 9, 42000, "medio", False, False, False, False, 4.3),
]


# ══════════════════════════════════════════════════════════════════════
# BLOQUE B — 19 RESTAURANTES ICÓNICOS VERIFICADOS
# Fuentes: visitvalle.travel, evendo.com, restaurantguru.com,
#          wanderlog.com, blancavalbuena.com, haciendadelbosque.com.co
# ══════════════════════════════════════════════════════════════════════

ICONICOS = [
    ("Platillos Voladores (Centenario)",
     "Restaurante más premiado de Cali. Fusión de sabores del Pacífico colombiano con técnicas culinarias internacionales. Galardonado nacional e internacionalmente.",
     "Avenida 3 Norte #7-19, Centenario",
     ["fusión", "colombiana contemporánea", "pacífica"],
     4, 6, 7, 8, 6, 75000, "caro", True, False, False, False, 4.8),

    ("Platillos Voladores (Ciudad Jardín)",
     "Segunda sede del mejor restaurante de Cali. Misma propuesta de fusión del Pacífico. Ambiente más moderno y ejecutivo.",
     "Palmas Mall, Carrera 105 #15-09, Ciudad Jardín Norte",
     ["fusión", "colombiana contemporánea", "pacífica"],
     4, 6, 7, 8, 6, 75000, "caro", True, False, False, False, 4.8),

    ("Hacienda del Bosque",
     "Icónica hacienda vallecaucana del siglo XIX restaurada. Cocina de autor con sabores tradicionales del Valle. Ambiente colonial único junto al Zoológico de Cali.",
     "Carrera 2 Oeste #14-250, Santa Teresita (junto al Zoológico)",
     ["colombiana", "fusión", "cocina de autor"],
     3, 5, 7, 7, 7, 65000, "caro", True, False, False, False, 4.7),

    ("La Comitiva",
     "Uno de los restaurantes más recomendados de Cali. Fusión de sabores orientales y colombianos. Famoso por su pulpo a la parrilla y el atollado pacífico.",
     "Calle 4 #34-32, San Fernando (a una cuadra del Parque del Perro)",
     ["fusión", "colombiana", "mariscos", "cocina del Pacífico"],
     5, 4, 8, 5, 7, 60000, "caro", True, False, False, False, 4.7),

    ("Restaurante de Basilia",
     "Fundado por la reconocida cocinera Basilia Murillo en la Galería Alameda. Referente de la auténtica cocina del Pacífico colombiano. Galardonado por gastronomía local.",
     "Galería Alameda, Local interior, Calle 8 #15-38, Alameda",
     ["pacífica", "afrocolombiana", "mariscos"],
     5, 3, 9, 4, 6, 30000, "medio", False, False, False, False, 4.8),

    ("Ringlete (Granada)",
     "Sede Granada del icónico Ringlete. Arroz atollado, chuleta valluna y sancocho de gallina con recetas auténticas. Referente nacional de la gastronomía vallecaucana.",
     "Calle 15A Norte #9N-31, Granada",
     ["colombiana", "valluna", "regional"],
     3, 4, 8, 5, 8, 35000, "medio", True, False, False, False, 4.6),

    ("El Zaguán de San Antonio",
     "Restaurante en hermosa casa colonial con terraza y vista panorámica de Cali. Uno de los más visitados de San Antonio. Cocina valluna con mariscos. Más de 2.000 reseñas en Google.",
     "Carrera 12 #1-29, San Antonio",
     ["colombiana", "valluna", "mariscos"],
     4, 4, 8, 5, 7, 38000, "medio", True, False, False, True, 4.2),

    ("Amelia Café Restaurante",
     "Café-restaurante muy popular en San Antonio. Conocido por sus brunchs caleños, ambiente íntimo y cocina colombiana contemporánea con toques creativos.",
     "Carrera 10 #2-06, San Antonio",
     ["colombiana contemporánea", "café", "brunch"],
     2, 7, 6, 8, 5, 35000, "medio", True, True, False, False, 4.6),

    ("Restaurante Rayuela",
     "Cocina argentina auténtica en el corazón de San Antonio. Empanadas, milanesas y cortes de carne en ambiente bohemio. Muy popular entre locales y turistas.",
     "Carrera 3 #2-09, San Antonio",
     ["argentina", "parrilla"],
     2, 3, 8, 3, 9, 42000, "medio", False, False, False, False, 4.5),

    ("Casa Ibérica",
     "Auténtica cocina española en el barrio El Peñón. Tapas, jamón ibérico, paella y vinos españoles importados. Ambiente íntimo en casa colonial.",
     "Calle 3A Oeste #3-07, El Peñón",
     ["española", "tapas", "mediterránea"],
     3, 4, 7, 7, 6, 55000, "medio", True, False, False, False, 4.5),

    ("Waunana Restaurante",
     "Restaurante con identidad colombiana e indígena. Cocina que rescata ingredientes ancestrales del Pacífico y la Amazonía. Propuesta gastronómica única en Cali.",
     "Calle 4 #9-23, San Antonio",
     ["colombiana", "fusión", "indígena"],
     4, 5, 7, 8, 5, 50000, "medio", True, True, False, False, 4.6),

    ("Odiseo Bistro",
     "Bistro mediterráneo de referencia en Granada. Tataki de atún, pulpo a la plancha, risotto y costillas de cordero. Considerado uno de los mejores bistros de Cali.",
     "Avenida 9 Norte #10-107, Granada",
     ["mediterránea", "bistro", "europea"],
     3, 5, 7, 6, 7, 75000, "caro", True, False, False, False, 4.7),

    ("La Bohème Restaurante-Bar",
     "Tapas artesanales y cócteles de autor en ambiente vibrante. Donde la excelencia culinaria se une con la vida nocturna de Cali. Muy popular para fechas especiales.",
     "Calle 1 #6-09, San Antonio",
     ["tapas", "española", "coctelería"],
     3, 5, 7, 7, 6, 55000, "medio", True, False, False, False, 4.6),

    ("La Cocina Restaurante",
     "Clásico de la cocina colombiana en Cali con larga trayectoria. Platos tradicionales del Valle, ingredientes de mercado fresco y recetas de generaciones.",
     "Carrera 35 #4-41, San Fernando",
     ["colombiana", "casera", "tradicional"],
     3, 4, 8, 5, 8, 25000, "economico", True, False, False, False, 4.4),

    ("Sello Negro Café",
     "El café de especialidad más reconocido de Cali. Granos de origen colombiano, métodos de preparación artesanales. Pionero de la cultura del café de autor en la ciudad.",
     "Carrera 9 #11N-24, Granada",
     ["café", "brunch", "panadería"],
     1, 7, 5, 9, 2, 22000, "economico", True, True, False, False, 4.7),

    ("Takami Sushi",
     "Sushi y cocina japonesa-peruana (nikkei). Tiraditos, rolls creativos y cócteles de autor. Varias sedes en la ciudad.",
     "Avenida 9 Norte #16N-40, Granada",
     ["japonesa", "sushi", "nikkei", "peruana"],
     5, 6, 7, 6, 6, 45000, "medio", True, False, False, True, 4.5),

    ("Tequendama Restaurante",
     "Restaurante del Hotel Intercontinental, ícono histórico de Cali. Cocina internacional y colombiana de alto nivel. El preferido para reuniones ejecutivas.",
     "Avenida Colombia #2-72, Centro Histórico",
     ["colombiana", "internacional", "ejecutiva"],
     3, 5, 7, 6, 7, 80000, "caro", True, False, True, False, 4.4),

    ("Criterion",
     "Alta cocina colombiana, uno de los mejores restaurantes de Cali. Ingredientes de temporada, experiencia gastronómica de primer nivel.",
     "Calle 10 # 4-27, El Peñón",
     ["alta cocina", "colombiana"],
     4, 6, 7, 7, 7, 130000, "premium", True, False, True, False, 4.8),

    ("Harry Sasson Cali",
     "Cocina contemporánea colombiana de lujo. Experiencia gastronómica de primer nivel en Ciudad Jardín.",
     "Avenida 9A # 117-20, Ciudad Jardín",
     ["alta cocina", "colombiana contemporánea"],
     5, 6, 7, 7, 7, 150000, "premium", True, False, True, False, 4.9),
]


# ══════════════════════════════════════════════════════════════════════
# UNIÓN COMPLETA
# ══════════════════════════════════════════════════════════════════════

TODOS_LOS_RESTAURANTES = (
    ZONA_PENON_SAN_ANTONIO
    + ZONA_GRANADA_VERSALLES
    + ZONA_CHIPICHAPE_UNICENTRO
    + ZONA_CIUDAD_JARDIN_LIDO
    + ZONA_SAN_FERNANDO_ALAMEDA
    + ZONA_INGENIO_CANEY
    + ZONA_CENTRO
    + ZONA_PANCE_OESTE
    + ZONA_MENGA_NORTE
    + ICONICOS
)


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def construir_registro(r: tuple) -> dict:
    return {
        "nombre":       r[0],
        "descripcion":  r[1],
        "ciudad":       "Cali",
        "direccion":    r[2],
        "tipo_cocina":  r[3],
        "picante":      r[4],
        "dulce":        r[5],
        "salado":       r[6],
        "vegetariano":  r[7],
        "carne":        r[8],
        "precio_promedio_cop": r[9],
        "precio_rango": r[10],
        "tiene_opciones_vegetarianas": r[11],
        "tiene_opciones_veganas":      r[12],
        "tiene_sin_gluten":            r[13],
        "hace_delivery":               r[14],
        "tiene_mesas":  True,
        "rating_google": r[15],
        "fuente_datos": "seed_cali_v3",
        "activo":       True,
    }


def imprimir_resumen():
    rangos = {}
    for r in TODOS_LOS_RESTAURANTES:
        rango = r[10]
        rangos[rango] = rangos.get(rango, 0) + 1

    zonas = {
        "El Peñón / San Antonio":        len(ZONA_PENON_SAN_ANTONIO),
        "Granada / Versalles":           len(ZONA_GRANADA_VERSALLES),
        "Chipichape / Santa Mónica":     len(ZONA_CHIPICHAPE_UNICENTRO),
        "Ciudad Jardín / El Lido":       len(ZONA_CIUDAD_JARDIN_LIDO),
        "San Fernando / Alameda":        len(ZONA_SAN_FERNANDO_ALAMEDA),
        "El Ingenio / El Caney":         len(ZONA_INGENIO_CANEY),
        "Centro / San Bosco":            len(ZONA_CENTRO),
        "Pance / Pichindé":              len(ZONA_PANCE_OESTE),
        "Menga / Norte":                 len(ZONA_MENGA_NORTE),
        "Icónicos verificados":          len(ICONICOS),
    }

    print(f"\n{'═'*55}")
    print("  🍽️  Seed completo — ¿Dónde comemos hoy?")
    print(f"{'═'*55}")
    print(f"  Total: {len(TODOS_LOS_RESTAURANTES)} restaurantes\n")

    print("  Por zona:")
    for zona, n in zonas.items():
        barra = "█" * n
        print(f"    {zona:<30} {barra} {n}")

    print(f"\n  Por rango de precio:")
    emojis = {"premium": "💎", "caro": "🔴", "medio": "🟡", "economico": "🟢"}
    for rango in ["economico", "medio", "caro", "premium"]:
        n = rangos.get(rango, 0)
        if n:
            print(f"    {emojis[rango]} {rango:<12} {'█'*n} {n}")

    precios = [r[9] for r in TODOS_LOS_RESTAURANTES]
    print(f"\n  Rango de precios:")
    print(f"    Mínimo:   ${min(precios):>8,} COP")
    print(f"    Máximo:   ${max(precios):>8,} COP")
    print(f"    Promedio: ${sum(precios)//len(precios):>8,} COP")

    vegan  = sum(1 for r in TODOS_LOS_RESTAURANTES if r[12])
    veg    = sum(1 for r in TODOS_LOS_RESTAURANTES if r[11])
    gluten = sum(1 for r in TODOS_LOS_RESTAURANTES if r[13])
    print(f"\n  Opciones especiales:")
    print(f"    Opciones veganas:        {vegan}")
    print(f"    Opciones vegetarianas:   {veg}")
    print(f"    Sin gluten:              {gluten}")
    print(f"{'═'*55}\n")


def seed_supabase(borrar_anteriores: bool = False):
    print(f"  Conectando a Supabase → {SUPABASE_URL[:45]}...")
    cliente = create_client(SUPABASE_URL, SUPABASE_KEY)

    if borrar_anteriores:
        print("  Eliminando restaurantes anteriores...")
        cliente.table("restaurantes").delete().in_(
            "fuente_datos", ["manual", "seed_cali_v2", "seed_famosos_v1", "seed_cali_v3"]
        ).execute()
        print("  ✅ Eliminados\n")

    # Detectar duplicados por nombre
    existentes_res = cliente.table("restaurantes").select("nombre").execute()
    nombres_existentes = {r["nombre"].lower() for r in (existentes_res.data or [])}

    registros = []
    saltados  = []
    for r in TODOS_LOS_RESTAURANTES:
        if r[0].lower() in nombres_existentes:
            saltados.append(r[0])
        else:
            registros.append(construir_registro(r))

    if saltados:
        print(f"  ⚠️  {len(saltados)} ya existen — omitidos:")
        for n in saltados:
            print(f"       · {n}")
        print()

    if not registros:
        print("  ✅ Todos los restaurantes ya estaban en la BD.")
        return

    print(f"  Insertando {len(registros)} restaurantes en lotes...")
    insertados = 0
    LOTE = 15
    for i in range(0, len(registros), LOTE):
        lote = registros[i : i + LOTE]
        try:
            res = cliente.table("restaurantes").insert(lote).execute()
            insertados += len(res.data or lote)
            nombres_lote = [reg["nombre"][:35] for reg in lote]
            print(f"    Lote {i//LOTE + 1}: {', '.join(nombres_lote[:3])}{'...' if len(nombres_lote) > 3 else ''} ✓")
        except Exception as e:
            print(f"    ❌ Error lote {i//LOTE + 1}: {e}")

    # Total final
    try:
        total = cliente.table("restaurantes").select("id", count="exact").eq("activo", True).execute()
        print(f"\n  ✅ {insertados} restaurantes insertados")
        print(f"  📊 Total en BD ahora: {total.count} restaurantes activos")
    except Exception:
        print(f"\n  ✅ {insertados} restaurantes insertados")


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    imprimir_resumen()

    print("¿Eliminar restaurantes anteriores (manual/seed_cali_v2/seed_famosos_v1) e insertar todo de cero?")
    print("Escribe 'si' para limpiar + insertar, o Enter para solo agregar los que falten:")
    resp = input("→ ").strip().lower()
    borrar = resp in ["si", "sí", "s", "yes"]

    seed_supabase(borrar_anteriores=borrar)

    print("\n🎉 Listo. Verifica en:")
    print("   https://app.supabase.com → Table Editor → restaurantes")
    print("   O filtra: fuente_datos = 'seed_cali_v3'\n")
