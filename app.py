import os
import re
from flask import Flask, jsonify, request
import cloudscraper

app = Flask(__name__)


@app.route("/")
def obtener_precio():
  sku = request.args.get("sku", "209374")
  build_id = "yIwmJ6bE4IQPRstVmEt5r"

  scraper = cloudscraper.create_scraper()
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/124.0.0.0 Safari/537.36"
      ),
      "Accept": "application/json, text/plain, */*",
      "X-Nextjs-Data": "1",
      "Referer": "https://www.homedepot.com.mx/",
  }

  try:
    # Paso 1: Consultar JSON inicial del SKU
    url_paso1 = f"https://www.homedepot.com.mx/_next/data/{build_id}/default/s/{sku}.json?keyword={sku}"
    res1 = scraper.get(url_paso1, headers=headers)

    if res1.status_code != 200:
      return jsonify({"error": f"Error en paso 1: {res1.status_code}"}), 500

    data1 = res1.json()
    redirect_path = data1.get("pageProps", {}).get("__N_REDIRECT", "")

    if not redirect_path:
      return jsonify({"error": "No se encontró la redirección __N_REDIRECT"}), 404

    # Paso 2: Consultar el JSON final pegando la ruta obtenida correctamente
    if redirect_path.startswith("/"):
      url_paso2 = f"https://www.homedepot.com.mx/_next/data/{build_id}/default{redirect_path}.json"
    else:
      url_paso2 = f"https://www.homedepot.com.mx/_next/data/{build_id}/default/{redirect_path}.json"

    res2 = scraper.get(url_paso2, headers=headers)

    if res2.status_code != 200:
      return jsonify({"error": f"Error en paso 2: {res2.status_code}"}), 500

    json_texto = res2.text

    # Extraer precio de la tienda 8734 (Reynosa)
    match_precio = re.search(
        r'"8734"\s*:\s*\{[^}]*"mxn"\s*:\s*"?([0-9\.]+)"?', json_texto
    )
    precio_reynosa = (
        f"${match_precio.group(1)} MXN"
        if match_precio
        else "No disponible"
    )

    # Extraer nombre
    match_nombre = re.search(r'"name"\s*:\s*"([^"]+)"', json_texto)
    nombre_prod = match_nombre.group(1) if match_nombre else "Producto Home Depot"

    # Extraer imagen
    match_img = re.search(r'"image"\s*:\s*\["([^"]+)"', json_texto)
    imagen_url = (
        match_img.group(1)
        if match_img
        else f"https://cdn.homedepot.com.mx/productos/{sku}/{sku}-d.jpg"
    )

    return jsonify({
        "status": "exito",
        "sku": sku,
        "nombre": nombre_prod,
        "precio_reynosa": precio_reynosa,
        "imagen": imagen_url,
        "enlace": f"https://www.homedepot.com.mx{redirect_path}",
    })

  except Exception as e:
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
