import json
import os
import time
import requests
from datetime import datetime

# ==========================================
# CONFIG
# ==========================================

OUTPUT_FILE = "live_data.json"
TEMP_FILE = "live_data.tmp.json"
BACKUP_FILE = "live_data.backup.json"

FUENTES_DOLAR = [
    "https://dolarapi.com/v1/dolares/tarjeta",
    "https://api.bluelytics.com.ar/v2/latest"
]

HEADERS = {
    "User-Agent": "ImportoK-Bot/1.0"
}

DEFAULT_DATA = {
    "version": 1,
    "updated_at": 0,
    "ultima_actualizacion": "offline",

    "dolar_tarjeta": 1846.0,
    "dolar_oficial": 1320.0,
    "dolar_mep": 1450.0,

    "fuente_dolar": "fallback"
}

# ==========================================
# HELPERS
# ==========================================

def log(msg):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ahora}] {msg}")


def validar_cotizacion(valor):
    return 500 <= valor <= 5000


def cargar_cache():

    if os.path.exists(OUTPUT_FILE):

        try:

            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:
            log(f"[CACHE ERROR] {e}")

    return DEFAULT_DATA.copy()


# ==========================================
# APIs DÓLAR
# ==========================================

def obtener_dolar():

    for url in FUENTES_DOLAR:

        try:

            log(f"Consultando API: {url}")

            respuesta = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

            respuesta.raise_for_status()

            content_type = respuesta.headers.get(
                "Content-Type",
                ""
            )

            if "application/json" not in content_type:
                raise ValueError("La API no devolvió JSON")

            data = respuesta.json()

            # ======================================
            # DOLARAPI
            # ======================================

            if "venta" in data:

                dolar = float(data["venta"])

                if not validar_cotizacion(dolar):
                    raise ValueError("Cotización inválida")

                return {
                    "dolar_tarjeta": dolar,
                    "fuente_dolar": "dolarapi"
                }

            # ======================================
            # BLUELYTICS
            # ======================================

            elif "oficial" in data:

                oficial = float(
                    data["oficial"]["value_sell"]
                )

                blue = float(
                    data["blue"]["value_sell"]
                )

                if not validar_cotizacion(oficial):
                    raise ValueError("Cotización inválida")

                return {
                    "dolar_tarjeta": oficial,
                    "dolar_oficial": oficial,
                    "dolar_mep": blue,
                    "fuente_dolar": "bluelytics"
                }

        except Exception as e:

            log(f"[ERROR] {url} -> {e}")

    return None


# ==========================================
# GUARDADO SEGURO
# ==========================================

def guardar_json_seguro(data):

    try:

        # backup del archivo anterior
        if os.path.exists(OUTPUT_FILE):

            try:
                os.replace(
                    OUTPUT_FILE,
                    BACKUP_FILE
                )

            except Exception as e:
                log(f"[BACKUP ERROR] {e}")

        # escritura temporal
        with open(
            TEMP_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        # reemplazo atómico
        os.replace(
            TEMP_FILE,
            OUTPUT_FILE
        )

        log("💾 JSON guardado correctamente")

    except Exception as e:

        log(f"[SAVE ERROR] {e}")


# ==========================================
# MAIN
# ==========================================

def ejecutar_bot():

    log("🤖 Iniciando actualización ImportoK")

    cache = cargar_cache()

    datos_dolar = obtener_dolar()

    # ======================================
    # SI LA API RESPONDE BIEN
    # ======================================

    if datos_dolar:

        cache.update(datos_dolar)

        cache["updated_at"] = int(time.time())

        cache["ultima_actualizacion"] = (
            datetime.now().isoformat()
        )

        cache["version"] = 1

        log("✅ Cotización actualizada")

    # ======================================
    # SI FALLAN TODAS LAS APIs
    # ======================================

    else:

        log(
            "⚠️ Todas las APIs fallaron. "
            "Se mantiene cache anterior."
        )

    guardar_json_seguro(cache)

    log("🏁 Finalizó ejecución")


# ==========================================
# ENTRYPOINT
# ==========================================

if __name__ == "__main__":
    ejecutar_bot()