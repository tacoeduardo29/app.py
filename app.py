import os
import re
from flask import Flask, jsonify, request
import cloudscraper

app = Flask(__name__)


@app.route("/")
def obtener_precio():
  # Leemos directo el parámetro GET sin ningún valor por defecto
  sku = (
      request.args.get("sku") or request.args.get("sku1") or ""
  ).strip()

  if not sku:
    return jsonify({
        "status": "error",
        "mensaje": (
            "Falta el parámetro SKU en la URL. Ejemplo: /?sku=209374 o"
            " /?sku1=209374"
        ),
    }), 400

  scraper = cloudscraper.create_scraper()
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/124.0.0.0 Safari/537.36"
      ),
      "Accept": (
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
      ),
      "Accept-Language": "es-MX,es;q=0.9",
      "Referer": "https://www.homedepot.com.mx/",
      "Cookie": "currentStore=8734; storeId=8734;",
  }

  try:
    # Búsqueda directa en Home Depot usando la tienda 8734
    url_busqueda = (
        f"https://www.homedepot.com.mx/s?keyword={sku}&storeId=8734"
    )
    res = scraper.get(url_busqueda, headers=headers, timeout=12)

    if res.status_code != 200:
      return jsonify({
          "status": "error",
          "sku": sku,
          "mensaje": (
              f"No se pudo conectar con Home Depot para el SKU {sku}"
          ),
      }), 404

    json_texto = res.text

    # Validar si el SKU realmente existe en el contenido devuelto
    if sku not in json_texto:
      return jsonify({
          "status": "error",
          "sku": sku,
          "mensaje": f"El SKU {sku} no existe o no está disponible en Home Depot.",
      }), 404

    # Búsqueda robusta del precio
    match_precio = re.search(
        r'"usage"\s*:\s*"Offer"[^}]*?"value"\s*:\s*"?([0-9\.]+)"?', json_texto
    )
    if not match_precio:
      match_precio = re.search(
          r'"currency"\s*:\s*"MXN"[^}]*?"value"\s*:\s*"?([0-9\.]+)"?',
          json_texto,
      )
    if not match_precio:
      match_precio = re.search(
          r'"value"\s*:\s*"?([0-9\.]+)"?[^}]*?"usage"\s*:\s*"Offer"', json_texto
      )
    if not match_precio:
      match_precio = re.search(
          r'"8734"[^}]*?"mxn"\s*:\s*"?([0-9\.]+)"?', json_texto
      )
    if not match_precio:
      match_precio = re.search(
          r'"internetPrice"\s*:\s*"?([0-9\.]+)"?', json_texto
      )

    precio_reynosa = (
        f"${match_precio.group(1)} MXN"
        if match_precio
        else "No disponible en Reynosa"
    )

    # Extraer nombre ubicado después del sellerId
    match_nombre = re.search(
        r'"sellerId"\s*:\s*"[^"]+"\s*,\s*"name"\s*:\s*"([^"]+)"', json_texto
    )
    if not match_nombre:
      match_nombre = re.search(r'"name"\s*:\s*"([^"]+)"', json_texto)

    nombre_prod = (
        match_nombre.group(1) if match_nombre else "Producto Home Depot"
    )

    # Imagen directa basada en el SKU recibido por GET
    imagen_url = f"https://cdn.homedepot.com.mx/productos/{sku}/{sku}-d.jpg"

    return jsonify({
        "status": "exito",
        "sku": sku,
        "tienda": "8734 (Reynosa)",
        "nombre": nombre_prod,
        "precio": precio_reynosa,
        "imagen": imagen_url,
        "enlace": f"https://www.homedepot.com.mx/s?keyword={sku}",
    })

  except Exception as e:
    return jsonify({"status": "error", "sku": sku, "mensaje": str(e)}), 500


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
