import os
import re
from flask import Flask, jsonify, request
import cloudscraper

app = Flask(__name__)


@app.route("/")
def obtener_precio():
  sku = (
      request.args.get("sku")
      or request.args.get("sku1")
      or ""
  ).strip()

  if not sku:
    return jsonify({
        "status": "error",
        "mensaje": (
            "Falta el parámetro SKU en la URL. Ejemplo: /?sku=209374"
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
    # Usamos la URL oficial de búsqueda con tienda fija 8734
    url = f"https://www.homedepot.com.mx/s?keyword={sku}&storeId=8734"
    res = scraper.get(url, headers=headers, timeout=12)

    if res.status_code != 200:
      return jsonify({
          "status": "error",
          "sku": sku,
          "mensaje": f"Error de conexión con Home Depot (Status {res.status_code})",
      }), 500

    html = res.text

    # Validar si el SKU se encuentra en el contenido
    if sku not in html:
      return jsonify({
          "status": "error",
          "sku": sku,
          "mensaje": f"El SKU {sku} no existe o no está disponible en Home Depot.",
      }), 404

    # Extraer el bloque que rodea al SKU para evitar cruzar precios de otros productos
    bloque = ""
    pos = html.find(sku)
    if pos != -1:
      bloque = html[max(0, pos - 600) : min(len(html), pos + 1800)]
    else:
      bloque = html

    # Buscar el precio en formato de oferta o valor dentro del bloque
    match_precio = re.search(
        r'"usage"\s*:\s*"Offer"[^}]*?"value"\s*:\s*"?([0-9\.]+)"?', bloque
    )
    if not match_precio:
      match_precio = re.search(
          r'"value"\s*:\s*"?([0-9\.]+)"?[^}]*?"usage"\s*:\s*"Offer"', bloque
      )
    if not match_precio:
      match_precio = re.search(
          r'"currency"\s*:\s*"MXN"[^}]*?"value"\s*:\s*"?([0-9\.]+)"?', bloque
      )
    if not match_precio:
      match_precio = re.search(
          r'8734[^}]{0,150}"mxn"\s*:\s*"?([0-9\.]+)"?', bloque
      )
    if not match_precio:
      match_precio = re.search(r'"internetPrice"\s*:\s*"?([0-9\.]+)"?', bloque)

    precio = (
        f"${match_precio.group(1)} MXN"
        if match_precio
        else "No disponible en Reynosa"
    )

    # Extraer el nombre del producto
    match_nombre = re.search(
        r'"sellerId"\s*:\s*"[^"]+"\s*,\s*"name"\s*:\s*"([^"]+)"', bloque
    )
    if not match_nombre:
      match_nombre = re.search(r'"name"\s*:\s*"([^"]+)"', bloque)

    nombre = match_nombre.group(1) if match_nombre else f"Producto SKU {sku}"

    # Imagen oficial directa
    imagen = f"https://cdn.homedepot.com.mx/productos/{sku}/{sku}-d.jpg"

    return jsonify({
        "status": "exito",
        "sku": sku,
        "tienda": "8734 (Reynosa)",
        "nombre": nombre,
        "precio": precio,
        "imagen": imagen,
        "enlace": f"https://www.homedepot.com.mx/s?keyword={sku}",
    })

  except Exception as e:
    return jsonify({"status": "error", "sku": sku, "mensaje": str(e)}), 500


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
