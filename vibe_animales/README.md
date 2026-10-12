# Vibe Coding: Procesamiento de imágenes de animales

Aplicación académica con Flask, SQLite, Pillow y ResNet-50 preentrenado de ImageNet.

## Requisitos

- Python 3.10 o superior (recomendado 3.11).
- Conexión a Internet en la primera ejecución del modelo para descargar los pesos.
- En Windows, instalá PyTorch y torchvision desde las instrucciones oficiales si `pip install` no encuentra una combinación compatible: https://pytorch.org/get-started/locally/

## Instalación en Windows (PowerShell)

1. Descomprimí el proyecto y abrí una terminal dentro de la carpeta `vibe_animales`.
2. Creá un entorno virtual:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   Si PowerShell bloquea la activación, podés ejecutar `.\.venv\Scripts\python.exe` en lugar de activar el entorno.

3. Actualizá pip e instalá dependencias:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Ejecutá la aplicación:

   ```powershell
   python app.py
   ```

5. Abrí en el navegador la dirección que aparece en la terminal, normalmente http://127.0.0.1:5000

## Instalación en macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Luego abrí http://127.0.0.1:5000.

## Cómo probar

1. Seleccioná una foto de un animal en formato JPG, PNG o WEBP (máximo 8 MB).
2. Opcionalmente completá los campos descriptivos.
3. Pulsá **Analizar y guardar**.
4. La primera ejecución puede tardar porque se descargan los pesos del modelo.
5. Se mostrará la predicción y las cinco clases principales. El registro queda guardado en `animales.db`.
6. Volvé al catálogo para abrir los detalles o eliminar un registro.

## Base de datos

La aplicación crea `animales.db` automáticamente al iniciar. Las tablas son:

- `animales`: datos descriptivos, campos manuales y ruta de la imagen.
- `analisis_imagenes`: predicción, confianza, fecha, estado y top 5 de clases; cada análisis se relaciona con un animal.

Podés inspeccionar la base con DB Browser for SQLite o con el comando:

```bash
python -c "import sqlite3; c=sqlite3.connect('animales.db'); print(c.execute('SELECT * FROM animales').fetchall()); print(c.execute('SELECT * FROM analisis_imagenes').fetchall())"
```

## Cómo funciona la IA y limitaciones

Se usa ResNet-50 con pesos preentrenados en ImageNet. El modelo devuelve etiquetas visuales de sus 1.000 categorías, algunas de las cuales corresponden a razas o tipos de animales. No es un clasificador taxonómico especializado: puede equivocarse, especialmente con fotos oscuras, animales pequeños o categorías que no conoce. El porcentaje es la probabilidad estimada para esa clase entre las categorías del modelo; no equivale a certeza científica.

Los datos escritos en el formulario se guardan como información aportada por la persona; la predicción del modelo se guarda por separado. Si no se pueden instalar/cargar los componentes de IA, la aplicación conserva el registro y muestra el error en el detalle.

## Estructura

```text
vibe_animales/
├── app.py
├── requirements.txt
├── README.md
├── animales.db            # se crea al ejecutar
├── templates/
│   ├── index.html
│   └── detail.html
└── static/
    ├── style.css
    └── uploads/            # fotos subidas
```

## Pruebas manuales recomendadas

- Subir una imagen JPG válida y confirmar que aparece en el catálogo.
- Abrir el detalle y comprobar las cinco predicciones y sus porcentajes.
- Subir PNG y WEBP.
- Probar un PDF o TXT: debe rechazarse.
- Probar una imagen mayor a 8 MB: debe rechazarse.
- Eliminar un registro y verificar que desaparezca de la lista.
- Reiniciar la aplicación y confirmar que los registros persisten en SQLite.

## Nota de seguridad

Esta aplicación está pensada para ejecución local y demostración académica. Antes de publicarla en Internet, cambiá `app.secret_key`, desactivá `debug=True`, añadí autenticación y revisá las políticas de almacenamiento de imágenes.
