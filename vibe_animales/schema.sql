PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS animales (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 nombre_comun TEXT, especie_confirmada TEXT, raza TEXT, color TEXT,
 tamano TEXT, habitat TEXT, caracteristicas TEXT,
 fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, imagen_path TEXT
);
CREATE TABLE IF NOT EXISTS analisis_imagenes (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 animal_id INTEGER NOT NULL,
 nombre_archivo TEXT NOT NULL,
 fecha_analisis TEXT NOT NULL,
 etiqueta_predicha TEXT NOT NULL,
 confianza REAL,
 top_resultados TEXT,
 estado TEXT NOT NULL,
 FOREIGN KEY (animal_id) REFERENCES animales(id) ON DELETE CASCADE
);
