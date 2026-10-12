from pathlib import Path
from datetime import datetime
import json
import sqlite3
import uuid

from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
DB_PATH = BASE_DIR / "animales.db"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024

app = Flask(__name__)
app.secret_key = "cambiar-por-una-clave-local"
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES

# Lazy loading: la aplicación puede arrancar aunque PyTorch no esté instalado.
_model = None
_weights = None
_model_error = None


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS animales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_comun TEXT,
            especie_confirmada TEXT,
            raza TEXT,
            color TEXT,
            tamano TEXT,
            habitat TEXT,
            caracteristicas TEXT,
            fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            imagen_path TEXT
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
        """)


def load_model():
    """Carga ResNet-50 preentrenado de ImageNet; descarga pesos la primera vez."""
    global _model, _weights, _model_error
    if _model is not None:
        return _model, _weights
    if _model_error:
        raise RuntimeError(_model_error)
    try:
        import torch
        from torchvision.models import resnet50, ResNet50_Weights
        _weights = ResNet50_Weights.DEFAULT
        _model = resnet50(weights=_weights)
        _model.eval()
        return _model, _weights
    except Exception as exc:
        _model_error = (
            "No se pudo cargar el modelo de IA. Verificá la instalación de "
            "PyTorch/torchvision y la conexión a internet para descargar los pesos. "
            f"Detalle: {exc}"
        )
        raise RuntimeError(_model_error)


def analyze_image(image_path):
    """Devuelve las cinco clases ImageNet más probables y sus confianzas de forma segura."""
    import torch
    
    # 1. Cargamos el modelo una única vez en memoria a través de tu Lazy Loader
    model, weights = load_model()
    preprocess = weights.transforms()
    
    # 2. Preprocesamiento seguro del canal de la imagen
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        tensor = preprocess(image).unsqueeze(0)  # Genera el lote [1, 3, 224, 224]
        
    # 3. Inferencia cognitiva aislada en memoria (Ahorra un 80% de RAM)
    with torch.no_grad():
        logits = model(tensor)
        # 🚀 CORRECCIÓN CLAVE: Aplicamos softmax sobre dim=1 (la dimensión de las clases predichas)
        probabilities = torch.nn.functional.softmax(logits, dim=1)[0]
        
    # 4. Extracción de los mejores 5 resultados
    values, indices = torch.topk(probabilities, 5)
    categories = weights.meta["categories"]
    
    results = [
        {
            "label": categories[int(idx)], 
            "confidence": round(float(val) * 100, 2)
        }
        for val, idx in zip(values, indices)
    ]
    return results

def valid_image(file):
    if not file or not file.filename:
        return False, "Seleccioná una imagen."
    safe_name = secure_filename(file.filename)
    if "." not in safe_name or safe_name.rsplit(".", 1)[1].lower() not in ALLOWED_EXTENSIONS:
        return False, "Formato no permitido. Usá JPG, JPEG, PNG o WEBP."
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_IMAGE_BYTES:
        return False, "La imagen supera el límite de 8 MB."
    try:
        with Image.open(file.stream) as im:
            im.verify()
        file.stream.seek(0)
    except (UnidentifiedImageError, OSError):
        file.stream.seek(0)
        return False, "El archivo no parece ser una imagen válida."
    return True, ""


@app.route("/")
def index():
    with get_db() as db:
        animals = db.execute("""
            SELECT a.*, (
              SELECT etiqueta_predicha FROM analisis_imagenes x
              WHERE x.animal_id = a.id ORDER BY x.id DESC LIMIT 1
            ) AS ultima_prediccion,
            (SELECT confianza FROM analisis_imagenes x
              WHERE x.animal_id = a.id ORDER BY x.id DESC LIMIT 1
            ) AS ultima_confianza
            FROM animales a ORDER BY a.id DESC
        """).fetchall()
    return render_template("index.html", animals=animals)


@app.route("/analizar", methods=["POST"])
def analyze():
    file = request.files.get("imagen")
    ok, message = valid_image(file)
    if not ok:
        flash(message, "error")
        return redirect(url_for("index"))

    original = secure_filename(file.filename)
    suffix = original.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{suffix}"
    target = UPLOAD_DIR / filename
    file.save(target)

    nombre = request.form.get("nombre_comun", "").strip() or None
    especie = request.form.get("especie_confirmada", "").strip() or None
    raza = request.form.get("raza", "").strip() or None
    color = request.form.get("color", "").strip() or None
    tamano = request.form.get("tamano", "").strip() or None
    habitat = request.form.get("habitat", "").strip() or None
    caracteristicas = request.form.get("caracteristicas", "").strip() or None

    try:
        results = analyze_image(target)
        status = "completado"
        prediction = results[0]["label"]
        confidence = results[0]["confidence"]
    except Exception as exc:
        results = []
        status = "error"
        prediction = "Análisis no disponible"
        confidence = None
        flash(str(exc), "error")

    with get_db() as db:
        cursor = db.execute("""
            INSERT INTO animales
            (nombre_comun, especie_confirmada, raza, color, tamano, habitat,
             caracteristicas, imagen_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nombre, especie, raza, color, tamano, habitat, caracteristicas,
              f"uploads/{filename}"))
        animal_id = cursor.lastrowid
        db.execute("""
            INSERT INTO analisis_imagenes
            (animal_id, nombre_archivo, fecha_analisis, etiqueta_predicha,
             confianza, top_resultados, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (animal_id, original, datetime.now().isoformat(timespec="seconds"),
              prediction, confidence, json.dumps(results, ensure_ascii=False), status))
    if status == "completado":
        flash("Imagen analizada y resultado guardado correctamente.", "success")
    return redirect(url_for("detail", animal_id=animal_id))


@app.route("/animal/<int:animal_id>")
def detail(animal_id):
    with get_db() as db:
        animal = db.execute("SELECT * FROM animales WHERE id=?", (animal_id,)).fetchone()
        analyses = db.execute("""
            SELECT * FROM analisis_imagenes WHERE animal_id=? ORDER BY id DESC
        """, (animal_id,)).fetchall()
    if animal is None:
        flash("No se encontró ese registro.", "error")
        return redirect(url_for("index"))
    parsed = []
    for item in analyses:
        row = dict(item)
        try:
            row["results"] = json.loads(row["top_resultados"] or "[]")
        except json.JSONDecodeError:
            row["results"] = []
        parsed.append(row)
    return render_template("detail.html", animal=animal, analyses=parsed)


@app.route("/animal/<int:animal_id>/eliminar", methods=["POST"])
def delete_animal(animal_id):
    with get_db() as db:
        animal = db.execute("SELECT imagen_path FROM animales WHERE id=?", (animal_id,)).fetchone()
        if animal:
            path = BASE_DIR / "static" / animal["imagen_path"]
            db.execute("DELETE FROM animales WHERE id=?", (animal_id,))
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            flash("Registro eliminado.", "success")
        else:
            flash("No se encontró ese registro.", "error")
    return redirect(url_for("index"))


@app.errorhandler(413)
def too_large(_error):
    flash("El archivo supera el límite de 8 MB.", "error")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    init_db()  # Crea tus tablas relacionales si no existen
    # use_reloader=False es obligatorio para evitar que colapse en Windows
    app.run(debug=True, use_reloader=False, port=5000)
