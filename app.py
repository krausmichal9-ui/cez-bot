import asyncio
import threading
import json
import math
from flask import Flask, render_template, request, jsonify, Response
from playwright.async_api import async_playwright

app = Flask(__name__)

# Fronta logů pro streaming do prohlížeče
log_queues = {}

def send_log(session_id, message, type="info"):
    if session_id in log_queues:
        log_queues[session_id].append({"msg": message, "type": type})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/spustit", methods=["POST"])
def spustit():
    data = request.json
    session_id = data.get("session_id", "default")
    log_queues[session_id] = []

    thread = threading.Thread(target=spustit_bota, args=(data, session_id))
    thread.daemon = True
    thread.start()

    return jsonify({"ok": True})

@app.route("/logy/<session_id>")
def logy(session_id):
    """Server-Sent Events endpoint pro live logy"""
    def generate():
        sent = 0
        import time
        while True:
            queue = log_queues.get(session_id, [])
            while sent < len(queue):
                item = queue[sent]
                yield f"data: {json.dumps(item)}\n\n"
                sent += 1
                if item.get("type") == "done" or item.get("type") == "error":
                    return
            time.sleep(0.3)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

def spustit_bota(data, session_id):
    asyncio.run(bot_async(data, session_id))

async def bot_async(data, session_id):
    log = lambda msg, t="info": send_log(session_id, msg, t)

    try:
        log("🚀 Spouštím prohlížeč...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,  # na serveru bez GUI
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            context = await browser.new_context(viewport={"width": 1400, "height": 900})
            page = await context.new_page()

            log("🌐 Otvírám formulář ČEZ Geoportál...")
            await page.goto("https://geoportal.cezdistribuce.cz/geoportal.ses/ves.aspx")
            await page.wait_for_load_state("networkidle")

            # ── Krok 1: Jméno a příjmení ─────────────────────────
            log("✏️  Vyplňuji jméno a příjmení...")
            await page.locator("input[id*='Jmeno'], input[id*='jmeno']").first.fill(data["jmeno"])
            await page.locator("input[id*='Prijmeni'], input[id*='prijmeni']").first.fill(data["prijmeni"])
            await page.click("input[value*='Pokračovat'], button:has-text('Pokračovat')")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1000)
            log("✅ Jméno a příjmení vyplněno", "success")

            # ── Krok 2: Adresa a polygon ──────────────────────────
            log("📍 Zadávám adresu zájmového území...")
            addr_input = page.locator("input.ui-autocomplete-input, input[id*='txtAdresa']").first
            await addr_input.fill(data["adresa"])
            await page.wait_for_timeout(1500)

            suggestion = page.locator(".ui-autocomplete li, .ui-menu-item").first
            try:
                await suggestion.wait_for(timeout=4000)
                await suggestion.click()
                log("✅ Adresa nalezena a vybrána", "success")
            except:
                await addr_input.press("Enter")
                log("⚠️  Adresa zadána bez autocomplete", "warning")

            await page.wait_for_timeout(2000)

            # Kreslení polygonu
            log("🖊️  Kreslím polygon na mapě...")
            polygon_btn = page.locator("a[title*='olygon'], .drawPolygon, [title='Nakreslit polygon']").first
            try:
                await polygon_btn.wait_for(timeout=3000)
                await polygon_btn.click()
            except:
                map_el = page.locator(".olMap, canvas, #map, .ol-viewport").first
                box = await map_el.bounding_box()
                if box:
                    await page.mouse.click(box["x"] + box["width"] - 70, box["y"] + 30)

            await page.wait_for_timeout(800)
            await kresli_polygon(page, 120)
            log("✅ Polygon zakreslen", "success")

            await page.click("input[value*='Pokračovat'], button:has-text('Pokračovat')")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1000)

            # ── Krok 3: Údaje o žádosti ───────────────────────────
            log("📋 Vyplňuji údaje o žádosti...")
            typ_select = page.locator("select[id*='Zadosti'], select[id*='zadosti'], select[id*='Typ']").first
            await typ_select.select_option(label="Informativní")

            nazev_input = page.locator("input[id*='Stavby'], input[id*='stavby'], input[id*='Nazev']").first
            await nazev_input.fill(data.get("nazev_stavby", "Rodinný dům"))

            doruceni_select = page.locator("select[id*='Doruceni'], select[id*='doruceni']").first
            await doruceni_select.select_option(label="Žádost o Sdělení - zaslání elektronicky")

            email_input = page.locator("input[id*='Email'], input[id*='email'], input[type='email']").first
            await email_input.fill(data["email"])

            # Zaškrtni ČEZ Distribuce
            try:
                row = page.locator("td:has-text('Distribuce'), label:has-text('Distribuce')").first
                cb = row.locator("input[type='checkbox']").first
                if not await cb.is_checked():
                    await cb.click()
            except:
                pass

            log("✅ Údaje o žádosti vyplněny", "success")

            await page.click("input[value*='Pokračovat'], button:has-text('Pokračovat')")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1000)

            # Screenshot rekapitulace
            log("📸 Pořizuji screenshot rekapitulace...")
            screenshot = await page.screenshot(full_page=False, type="png")
            import base64
            img_b64 = base64.b64encode(screenshot).decode()
            log(f"SCREENSHOT:{img_b64}", "screenshot")

            log("⏸️  Formulář je vyplněný! Otevři odkaz níže a ručně odešli žádost.", "pause")
            log(f"🔗 URL: {page.url}", "url")

            # Drž prohlížeč chvíli otevřený
            await page.wait_for_timeout(30000)
            await browser.close()
            log("✅ Hotovo!", "done")

    except Exception as e:
        import traceback
        log(f"❌ Chyba: {str(e)}", "error")
        log(traceback.format_exc(), "error")

async def kresli_polygon(page, presah_px):
    map_el = page.locator(".olMap, canvas, #map, .ol-viewport").first
    try:
        box = await map_el.bounding_box()
    except:
        return
    if not box:
        return

    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    px = min(presah_px, 180)

    body = [
        (cx - px, cy - px),
        (cx + px, cy - px),
        (cx + px, cy + px),
        (cx - px, cy + px),
    ]
    for x, y in body:
        await page.mouse.click(x, y)
        await page.wait_for_timeout(300)
    await page.mouse.dblclick(body[0][0], body[0][1])
    await page.wait_for_timeout(500)

if __name__ == "__main__":
import os
port = int(os.environ.get("PORT", 5000))
import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port, debug=False)
