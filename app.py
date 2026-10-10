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
            "Falta el parámetro SKU en la URL. Ejemplo: /?sku=631708"
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
    # Obtenemos un buildId fresco, con respaldo fijo por si la home se pone pesada
    build_id = "yIwmJ6bE4IQPRstVmEt5r"
    try:
      home_res = scraper.get(
          "https://www.homedepot.com.mx/", headers=headers, timeout=5
      )
      match_nd = re.search(r'"buildId"\s*:\s*"([^"]+)"', home_res.text)
      if match_nd:
        build_id = match_nd.group(1)
    except:
      pass

    # Headers específicos para Next.js JSON
    json_headers = headers.copy()
    json_headers["Accept"] = "application/json, text/plain, */*"
    json_headers["X-Nextjs-Data"] = "1"

    # Paso 1: Consultar el JSON del SKU con la tienda 8734
    url_paso1 = f"https://www.homedepot.com.mx/_next/data/{build_id}/default/s/{sku}.json?keyword={sku}&storeId=8734"
    res1 = scraper.get(url_paso1, headers=json_headers, timeout=10)

    if res1.status_code != 200:
      return jsonify({
          "status": "error",
          "sku": sku,
          "mensaje": f"El SKU {sku} no existe o no está disponible en Home Depot.",
      }), 404

    data1 = res1.json()
    redirect_path = data1.get("pageProps", {}).get("__N_REDIRECT", "")

    if not redirect_path:
      return jsonify({
          "status": "error",
          "sku": sku,
          "mensaje": f"No se encontró la ruta del producto para el SKU {sku}",
      }), 404

    # Paso 2: Consultar el JSON final del producto con la redirección obtenida
    if redirect_path.startswith("/"):
      url_paso2 = f"https://www.homedepot.com.mx/_next/data/{build_id}/default{redirect_path}.json?storeId=8734"
    else:
      url_paso2 = f"https://www.homedepot.com.mx/_next/data/{build_id}/default/{redirect_path}.json?storeId=8734"

    res2 = scraper.get(url_paso2, headers=json_headers, timeout=10)

    if res2.status_code != 200:
      return jsonify({
          "status": "error",
          "sku": sku,
          "mensaje": "Error al obtener los detalles del producto",
      }), 500

    json_texto = res2.text

    # Aislar el bloque exacto del SKU para evitar agarrar precios de otros lados
    bloque_producto = ""
    pos_sku = json_texto.find(f'"{sku}"')
    if pos_sku != -1:
      inicio = max(0, pos_sku - 500)
      fin = min(len(json_texto), pos_sku + 1500)
      bloque_producto = json_texto[inicio:fin]
    else:
      bloque_producto = json_texto

    # Búsqueda del precio estrictamente dentro del bloque
    match_precio = re.search(
        r'"usage"\s*:\s*"Offer"[^}]*?"value"\s*:\s*"?([0-9\.]+)"?',
        bloque_producto,
    )
    if not match_precio:
      match_precio = re.search(
          r'"currency"\s*:\s*"MXN"[^}]*?"value"\s*:\s*"?([0-9\.]+)"?',
          bloque_producto,
      )
    if not match_precio:
      match_precio = re.search(
          r'"value"\s*:\s*"?([0-9\.]+)"?[^}]*?"usage"\s*:\s*"Offer"',
          bloque_producto,
      )
    if not match_precio:
      match_precio = re.search(
          r'"8734"[^}]*?"mxn"\s*:\s*"?([0-9\.]+)"?', bloque_producto
      )
    if not match_precio:
      match_precio = re.search(
          r'"internetPrice"\s*:\s*"?([0-9\.]+)"?', bloque_producto
      )

    precio_reynosa = (
        f"${match_precio.group(1)} MXN"
        if match_precio
        else "No disponible en Reynosa"
    )

    # Extraer nombre
    match_nombre = re.search(
        r'"sellerId"\s*:\s*"[^"]+"\s*,\s*"name"\s*:\s*"([^"]+)"', bloque_producto
    )
    if not match_nombre:
      match_nombre = re.search(r'"name"\s*:\s*"([^"]+)"', bloque_producto)

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
        "enlace": f"https://www.homedepot.com.mx{redirect_path}",
    })

  except Exception as e:
    return jsonify({"status": "error", "sku": sku, "mensaje": str(e)}), 500


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
