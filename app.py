import json, random, uuid
from pathlib import Path
from typing import Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

PROPERTIES = {
    1:{"name":"Méditerranée","price":60,"rent":2},   3:{"name":"Baltic","price":60,"rent":4},
    6:{"name":"Oriental","price":100,"rent":6},       9:{"name":"Connecticut","price":120,"rent":8},
    11:{"name":"St-Charles","price":140,"rent":10},  14:{"name":"Virginia","price":160,"rent":12},
    16:{"name":"St-James","price":180,"rent":14},    19:{"name":"New York","price":200,"rent":16},
    21:{"name":"Kentucky","price":220,"rent":18},    24:{"name":"Illinois","price":240,"rent":20},
    26:{"name":"Atlantic","price":260,"rent":22},    29:{"name":"Marvin","price":280,"rent":24},
    31:{"name":"Pacific","price":300,"rent":26},     34:{"name":"Pennsylvanie","price":320,"rent":28},
    37:{"name":"Park","price":350,"rent":35},        39:{"name":"Boulevard","price":400,"rent":50},
    5:{"name":"Gare 1","price":200,"rent":25},       15:{"name":"Gare 2","price":200,"rent":25},
    25:{"name":"Gare 3","price":200,"rent":25},      35:{"name":"Gare 4","price":200,"rent":25},
}
SPECIAL = {0:"DÉPART",2:"Caisse",4:"Taxes -200$",7:"Chance",10:"Prison",
           17:"Caisse",20:"Parc Gratuit",22:"Chance",30:"→Prison",33:"Caisse",
           36:"Chance",38:"Luxe -100$"}

rooms: Dict[str, dict] = {}
conns: Dict[str, Set[WebSocket]] = {}

def new_room(rid):
    rooms[rid] = {"players": {}, "order": [], "turn": 0, "started": False, "owned": {}}
    conns[rid] = set()

def add_player(rid, pid, name):
    icons = ["🔴", "🔵", "🟢", "🟡"]
    rooms[rid]["players"][pid] = {
        "id": pid, "name": name, "money": 1500, "pos": 0,
        "icon": icons[len(rooms[rid]["players"]) % 4], "bankrupt": False
    }
    rooms[rid]["order"].append(pid)

def do_move(rid, pid):
    room, player = rooms[rid], rooms[rid]["players"][pid]
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    new_pos = (player["pos"] + d1 + d2) % 40
    msgs = [f"🎲 {player['name']} fait {d1}+{d2} → case {new_pos}"]
    if new_pos < player["pos"]:
        player["money"] += 200
        msgs.append("✅ Passage DÉPART +200$")
    player["pos"] = new_pos
    if new_pos == 30:
        player["pos"] = 10
        msgs.append("🚔 En prison!")
    elif new_pos in PROPERTIES:
        p = PROPERTIES[new_pos]
        owner = room["owned"].get(new_pos)
        if owner is None:
            msgs.append(f"🏠 {p['name']} à vendre ({p['price']}$) — cliquez Acheter")
        elif owner != pid:
            o = room["players"][owner]
            player["money"] -= p["rent"]
            o["money"] += p["rent"]
            msgs.append(f"💸 Loyer {p['rent']}$ → {o['name']}")
            if player["money"] <= 0:
                player["bankrupt"] = True
                msgs.append(f"💀 {player['name']} en faillite!")
        else:
            msgs.append(f"🏠 Votre propriété : {p['name']}")
    elif new_pos in SPECIAL:
        msgs.append(f"⭐ {SPECIAL[new_pos]}")
        if new_pos == 4:  player["money"] -= 200
        elif new_pos == 38: player["money"] -= 100
    return msgs

def do_buy(rid, pid):
    room, player = rooms[rid], rooms[rid]["players"][pid]
    pos = player["pos"]
    if pos not in PROPERTIES: return "❌ Pas achetable."
    if pos in room["owned"]: return "❌ Déjà vendu."
    p = PROPERTIES[pos]
    if player["money"] < p["price"]: return f"❌ Pas assez d'argent ({p['price']}$ requis)."
    player["money"] -= p["price"]
    room["owned"][pos] = pid
    return f"✅ {player['name']} achète {p['name']} pour {p['price']}$"

def get_state(rid):
    room = rooms[rid]
    cur = room["order"][room["turn"] % len(room["order"])] if room["order"] else None
    return {"event": "state", "players": list(room["players"].values()),
            "turn": cur, "owned": {str(k): v for k, v in room["owned"].items()},
            "started": room["started"]}

async def broadcast(rid, data):
    dead = set()
    for ws in conns[rid]:
        try: await ws.send_json(data)
        except: dead.add(ws)
    conns[rid] -= dead

@app.get("/")
async def index():
    return HTMLResponse(Path("index.html").read_text(encoding="utf-8"))

@app.websocket("/ws/{rid}/{name}")
async def ws_ep(ws: WebSocket, rid: str, name: str):
    await ws.accept()
    if rid not in rooms:
        new_room(rid)
    pid = str(uuid.uuid4())[:8]
    add_player(rid, pid, name)
    conns[rid].add(ws)
    await ws.send_json({"event": "joined", "pid": pid})
    await broadcast(rid, {"event": "chat", "msg": f"👤 {name} a rejoint!"})
    await broadcast(rid, get_state(rid))
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            cmd, room = msg.get("cmd"), rooms[rid]
            if cmd == "start" and not room["started"] and len(room["players"]) >= 2:
                room["started"] = True
                await broadcast(rid, {"event": "chat", "msg": "🎮 La partie commence!"})
                await broadcast(rid, get_state(rid))
            elif cmd == "roll":
                cur = room["order"][room["turn"] % len(room["order"])]
                if pid != cur:
                    await ws.send_json({"event": "chat", "msg": "⚠️ Pas votre tour."})
                    continue
                for m in do_move(rid, pid):
                    await broadcast(rid, {"event": "chat", "msg": m})
                room["turn"] += 1
                await broadcast(rid, get_state(rid))
            elif cmd == "buy":
                cur = room["order"][(room["turn"] - 1) % len(room["order"])]
                if pid != cur:
                    await ws.send_json({"event": "chat", "msg": "⚠️ Pas votre tour."})
                    continue
                await broadcast(rid, {"event": "chat", "msg": do_buy(rid, pid)})
                await broadcast(rid, get_state(rid))
            elif cmd == "chat":
                n = room["players"][pid]["name"]
                await broadcast(rid, {"event": "chat", "msg": f"💬 {n}: {msg.get('text','')}"})
    except WebSocketDisconnect:
        conns[rid].discard(ws)
        if pid in rooms.get(rid, {}).get("players", {}):
            await broadcast(rid, {"event": "chat", "msg": f"👋 {rooms[rid]['players'][pid]['name']} a quitté."})
