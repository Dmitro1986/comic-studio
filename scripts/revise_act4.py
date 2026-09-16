#!/usr/bin/env python3
import json, urllib.request, time

sid = "2a60eb6a"

# Revise feedback — array of strings (NOT a single string)
feedback = [
    "ПОВНИЙ ПЕРЕГЕНЕРАЦІЙНИЙ ЦИКЛ. image_style має бути cartoon (як вказано в original task), зараз рендер вийшов у photorealistic cinematic стилі — це ламає всю серію Акт 1-3, яка була в cartoon. Потрібен яскравий комедійний cartoon, чіткі контури, спрощені форми, трохи гротеск. Caption style — bubble (словесні бульбашки), не memo-стікери.",

    "ПАНЕЛЬ 1 (Фойє Опери): епічна розкіш — золоті ліпнини, кришталеві люстри, натовп у вечірніх сукнях і чорних смокінгах, оркестранти з Моцартом. У центрі — Адрі в білому смокінгу з ВЕЛИКОЮ БРУДНОЮ ПЛЯМОЮ на спині, тримає тарілку ікри, незворушний як аристократ. Поруч Дженні у бузковій оксамитовій сукні з келихом шампанського. Підпис (bubble) має бути ТОЧНО: 'Барон у своїй стихії.'",

    "ПАНЕЛЬ 2 (Прохають піти): крупний план — розкішно вбраний розпорядник у фраку нахилився до Адрі і шепоче на вухо з витонченою посмішкою. Адрі тримає тарілку ікри, кам'яне незворушне обличчя як у справжнього аристократа. Підпис (bubble) має бути ТОЧНО: 'Шановний барон. Вас просять залишити.'",

    "ПАНЕЛЬ 3 (На бровах): вулиця Відні, ніч. Адрі і Дженні 'повзуть на бровах' геть від Опери — п'яні, щасливі, царственні. Адрі тримає в зубах останній пиріжок з ікрою, Дженні спирається на його руку. Cartoon style з явним комедійним гротеском. Підпис (bubble) має бути ТОЧНО: 'На бровах. Здобиччю.'",

    "ОБОВ'ЯЗКОВО: image_style='cartoon' — НЕ photorealistic, НЕ cinematic. Прості контури, яскраві кольори, комедійний гротеск. Caption style має бути bubble (словесні бульбашки), не memo. Підписи ТОЧНО як вказано: 'Барон у своїй стихії.' / 'Шановний барон. Вас просять залишити.' / 'На бровах. Здобиччю.' Рівно 3 панелі, не більше."
]

# Revise
body = json.dumps({"feedback": feedback, "image_style": "cartoon", "caption_style": "bubble"}).encode()
req = urllib.request.Request(
    f"http://127.0.0.1:3000/api/scenarios/{sid}/revise",
    data=body, headers={"Content-Type": "application/json"}, method="POST"
)
with urllib.request.urlopen(req, timeout=60) as r:
    print("REVISE:", json.loads(r.read()))

# Poll revision_status
print("Polling revision_status...")
start = time.time()
while time.time() - start < 180:
    with urllib.request.urlopen(f"http://127.0.0.1:3000/api/scenarios/{sid}", timeout=30) as r:
        d = json.loads(r.read())
    rev = d.get("revision_status", "")
    print(f"[{int(time.time()-start)}s] revision_status={rev}, status={d.get('status')}")
    if rev == "revision_succeeded":
        break
    if rev == "revision_failed":
        raise SystemExit("REVISE FAILED")
    time.sleep(8)

# Approve + render
req = urllib.request.Request(f"http://127.0.0.1:3000/api/scenarios/{sid}/approve", data=b"", method="POST")
with urllib.request.urlopen(req, timeout=30) as r:
    print("APPROVE:", json.loads(r.read()))

req = urllib.request.Request(
    f"http://127.0.0.1:3000/api/scenarios/{sid}/render",
    data=json.dumps({"mode": "initial"}).encode(),
    headers={"Content-Type": "application/json"}, method="POST"
)
with urllib.request.urlopen(req, timeout=30) as r:
    print("RENDER:", json.loads(r.read()))

# Poll rendered
print("Polling render...")
start = time.time()
while time.time() - start < 180:
    with urllib.request.urlopen(f"http://127.0.0.1:3000/api/scenarios/{sid}", timeout=30) as r:
        d = json.loads(r.read())
    print(f"[{int(time.time()-start)}s] status={d.get('status')}")
    if d.get("status") == "rendered":
        break
    time.sleep(10)

# Verify
with urllib.request.urlopen(f"http://127.0.0.1:3000/api/scenarios/{sid}", timeout=30) as r:
    d = json.loads(r.read())
print("FINAL:")
print("  status:", d.get("status"))
print("  image_style:", d.get("image_style"))
print("  caption_style:", d.get("caption_style"))
for i, p in enumerate(d.get("panels", []), 1):
    print(f"  PANEL {i}: {p.get('caption', '<none>')}")
print("DONE sid=", sid)
