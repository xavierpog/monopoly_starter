import json, random, uuid
from pathlib import Path
from typing import Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

CHANCE_CARDS = [
    {"id":"c1",  "text":"Avancez jusqu'au Boulevard. Si vous passez par DÉPART, recevez 200$.", "action":"goto", "dest":39},
    {"id":"c2",  "text":"Avancez jusqu'au DÉPART. Recevez 200$.", "action":"goto", "dest":0},
    {"id":"c3",  "text":"Avancez jusqu'à l'Illinois. Si vous passez par DÉPART, recevez 200$.", "action":"goto", "dest":24},
    {"id":"c4",  "text":"Avancez jusqu'à St-Charles. Si vous passez par DÉPART, recevez 200$.", "action":"goto", "dest":11},
    {"id":"c5",  "text":"Avancez à la gare la plus proche. Payez double loyer si elle est possédée.", "action":"nearest_railroad"},
    {"id":"c6",  "text":"Avancez à la gare la plus proche. Payez double loyer si elle est possédée.", "action":"nearest_railroad"},
    {"id":"c7",  "text":"Avancez à la compagnie la plus proche. Payez 10× le lancer si possédée.", "action":"nearest_utility"},
    {"id":"c8",  "text":"La banque vous verse un dividende de 50$.", "action":"gain", "amount":50},
    {"id":"c9",  "text":"Carte Sortie de Prison gratuite.", "action":"goojf"},
    {"id":"c10", "text":"Reculez de 3 cases.", "action":"back3"},
    {"id":"c11", "text":"Allez en Prison.", "action":"jail"},
    {"id":"c12", "text":"Réparations générales : payez 25$ par maison, 100$ par hôtel.", "action":"repairs", "house":25, "hotel":100},
    {"id":"c13", "text":"Amende pour excès de vitesse : payez 15$.", "action":"lose", "amount":15},
    {"id":"c14", "text":"Avancez jusqu'à la Gare 1. Si vous passez par DÉPART, recevez 200$.", "action":"goto", "dest":5},
    {"id":"c15", "text":"Vous êtes élu Président du Conseil : versez 50$ à chaque joueur.", "action":"pay_all", "amount":50},
    {"id":"c16", "text":"Votre prêt immobilier arrive à maturité : recevez 150$.", "action":"gain", "amount":150},
]

COMMUNITY_CARDS = [
    {"id":"cc1",  "text":"Avancez jusqu'au DÉPART. Recevez 200$.", "action":"goto", "dest":0},
    {"id":"cc2",  "text":"Erreur bancaire en votre faveur : recevez 200$.", "action":"gain", "amount":200},
    {"id":"cc3",  "text":"Honoraires du médecin : payez 50$.", "action":"lose", "amount":50},
    {"id":"cc4",  "text":"Vente d'actions : recevez 50$.", "action":"gain", "amount":50},
    {"id":"cc5",  "text":"Carte Sortie de Prison gratuite.", "action":"goojf"},
    {"id":"cc6",  "text":"Allez en Prison.", "action":"jail"},
    {"id":"cc7",  "text":"Nuit d'opéra : recevez 50$ de chaque joueur.", "action":"collect_all", "amount":50},
    {"id":"cc8",  "text":"Fonds de vacances arrivé à maturité : recevez 100$.", "action":"gain", "amount":100},
    {"id":"cc9",  "text":"Remboursement d'impôt : recevez 20$.", "action":"gain", "amount":20},
    {"id":"cc10", "text":"C'est votre anniversaire : recevez 10$ de chaque joueur.", "action":"collect_all", "amount":10},
    {"id":"cc11", "text":"Assurance-vie arrivée à maturité : recevez 100$.", "action":"gain", "amount":100},
    {"id":"cc12", "text":"Frais d'hôpital : payez 100$.", "action":"lose", "amount":100},
    {"id":"cc13", "text":"Frais de scolarité : payez 150$.", "action":"lose", "amount":150},
    {"id":"cc14", "text":"Honoraires de consultant : recevez 25$.", "action":"gain", "amount":25},
    {"id":"cc15", "text":"Réparations de voirie : payez 40$ par maison, 115$ par hôtel.", "action":"repairs", "house":40, "hotel":115},
    {"id":"cc16", "text":"2e prix au concours de beauté : recevez 10$.", "action":"gain", "amount":10},
]

PROPERTIES = {
    1:{"name":"Méditerranée","price":60,"rent":2},   3:{"name":"Baltic","price":60,"rent":4},
    6:{"name":"Oriental","price":100,"rent":6},       8:{"name":"Vermont","price":100,"rent":6},
    9:{"name":"Connecticut","price":120,"rent":8},
    11:{"name":"St-Charles","price":140,"rent":10},  13:{"name":"États","price":140,"rent":10},
    14:{"name":"Virginia","price":160,"rent":12},
    16:{"name":"St-James","price":180,"rent":14},    18:{"name":"Tennessee","price":180,"rent":14},
    19:{"name":"New York","price":200,"rent":16},
    21:{"name":"Kentucky","price":220,"rent":18},    23:{"name":"Indiana","price":220,"rent":18},
    24:{"name":"Illinois","price":240,"rent":20},
    26:{"name":"Atlantic","price":260,"rent":22},    27:{"name":"Ventnor","price":260,"rent":22},
    29:{"name":"Marvin","price":280,"rent":24},
    31:{"name":"Pacific","price":300,"rent":26},     32:{"name":"Caroline N.","price":300,"rent":26},
    34:{"name":"Pennsylvanie","price":320,"rent":28},
    37:{"name":"Park","price":350,"rent":35},        39:{"name":"Boulevard","price":400,"rent":50},
    5:{"name":"Gare 1","price":200,"rent":25},       15:{"name":"Gare 2","price":200,"rent":25},
    25:{"name":"Gare 3","price":200,"rent":25},      35:{"name":"Gare 4","price":200,"rent":25},
    12:{"name":"Cie Électrique","price":150,"rent":0,"utility":True},
    28:{"name":"Cie des Eaux","price":150,"rent":0,"utility":True},
}
SPECIAL = {0:"DÉPART",2:"Caisse",4:"Taxes -200$",7:"Chance",10:"Prison",
           17:"Caisse",20:"Parc Gratuit",22:"Chance",30:"→Prison",33:"Caisse",
           36:"Chance",38:"Luxe -100$"}

rooms: Dict[str, dict] = {}
conns: Dict[str, Set[WebSocket]] = {}

def new_room(rid):
    chance = CHANCE_CARDS[:]
    community = COMMUNITY_CARDS[:]
    random.shuffle(chance)
    random.shuffle(community)
    rooms[rid] = {
        "players": {}, "order": [], "turn": 0, "started": False, "owned": {},
        "pending_buy": None, "pending_trade": None,
        "chance_deck": chance, "community_deck": community,
        "goojf": {},  # pid -> count
    }
    conns[rid] = set()

def draw_card(deck):
    card = deck.pop(0)
    deck.append(card)
    return card

RAILROADS = [5, 15, 25, 35]
UTILITIES  = [12, 28]

def nearest(pos, targets):
    return min(targets, key=lambda t: (t - pos) % 40)

def apply_card(rid, pid, card, roll):
    room, player = rooms[rid], rooms[rid]["players"][pid]
    msgs = [f"🃏 {card['text']}"]
    action = card["action"]

    if action == "gain":
        player["money"] += card["amount"]
    elif action == "lose":
        player["money"] -= card["amount"]
        if player["money"] <= 0:
            player["bankrupt"] = True; msgs.append(f"💀 {player['name']} en faillite!")
    elif action == "goto":
        dest = card["dest"]
        if dest <= player["pos"] and dest != player["pos"]:
            player["money"] += 200; msgs.append("✅ Passage DÉPART +200$")
        player["pos"] = dest
        if dest == 0:
            player["money"] += 200; msgs.append("✅ Passage DÉPART +200$")
    elif action == "back3":
        player["pos"] = (player["pos"] - 3) % 40
    elif action == "jail":
        player["pos"] = 10
        msgs.append("🚔 En prison!")
    elif action == "goojf":
        room["goojf"][pid] = room["goojf"].get(pid, 0) + 1
        msgs.append("🎫 Carte Sortie de Prison conservée.")
    elif action == "pay_all":
        amt = card["amount"]
        others = [p for p in room["players"].values() if p["id"] != pid and not p["bankrupt"]]
        total = amt * len(others)
        player["money"] -= total
        for o in others: o["money"] += amt
        if player["money"] <= 0:
            player["bankrupt"] = True; msgs.append(f"💀 {player['name']} en faillite!")
    elif action == "collect_all":
        amt = card["amount"]
        others = [p for p in room["players"].values() if p["id"] != pid and not p["bankrupt"]]
        for o in others:
            o["money"] -= amt; player["money"] += amt
    elif action == "repairs":
        # No houses/hotels yet → no charge
        pass
    elif action == "nearest_railroad":
        dest = nearest(player["pos"], RAILROADS)
        if dest <= player["pos"]:
            player["money"] += 200; msgs.append("✅ Passage DÉPART +200$")
        player["pos"] = dest
        owner = room["owned"].get(dest)
        if owner and owner != pid:
            rent = PROPERTIES[dest]["rent"] * 2
            player["money"] -= rent; room["players"][owner]["money"] += rent
            msgs.append(f"💸 Double loyer {rent}$ → {room['players'][owner]['name']}")
            if player["money"] <= 0:
                player["bankrupt"] = True; msgs.append(f"💀 {player['name']} en faillite!")
        elif owner is None:
            msgs.append(f"🏠 {PROPERTIES[dest]['name']} à vendre — cliquez Acheter")
            return msgs, dest
    elif action == "nearest_utility":
        dest = nearest(player["pos"], UTILITIES)
        if dest <= player["pos"]:
            player["money"] += 200; msgs.append("✅ Passage DÉPART +200$")
        player["pos"] = dest
        owner = room["owned"].get(dest)
        if owner and owner != pid:
            rent = roll * 10
            player["money"] -= rent; room["players"][owner]["money"] += rent
            msgs.append(f"💸 {rent}$ (10× dés) → {room['players'][owner]['name']}")
            if player["money"] <= 0:
                player["bankrupt"] = True; msgs.append(f"💀 {player['name']} en faillite!")
        elif owner is None:
            msgs.append(f"🏠 {PROPERTIES[dest]['name']} à vendre — cliquez Acheter")
            return msgs, dest

    return msgs, None  # None = no pending buy

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
    roll = d1 + d2
    new_pos = (player["pos"] + roll) % 40
    msgs = [f"🎲 {player['name']} fait {d1}+{d2} → case {new_pos}"]
    if new_pos < player["pos"]:
        player["money"] += 200
        msgs.append("✅ Passage DÉPART +200$")
    player["pos"] = new_pos
    pending_buy_pos = None

    if new_pos == 30:
        player["pos"] = 10
        msgs.append("🚔 En prison!")
    elif new_pos in (7, 22, 36):
        card = draw_card(room["chance_deck"])
        card_msgs, buy_pos = apply_card(rid, pid, card, roll)
        msgs += card_msgs
        pending_buy_pos = buy_pos
    elif new_pos in (2, 17, 33):
        card = draw_card(room["community_deck"])
        card_msgs, buy_pos = apply_card(rid, pid, card, roll)
        msgs += card_msgs
        pending_buy_pos = buy_pos
    elif new_pos in PROPERTIES:
        p = PROPERTIES[new_pos]
        owner = room["owned"].get(new_pos)
        if owner is None:
            msgs.append(f"🏠 {p['name']} à vendre ({p['price']}$) — cliquez Acheter")
            pending_buy_pos = new_pos
        elif owner != pid:
            o = room["players"][owner]
            if p.get("utility"):
                both = all(room["owned"].get(u) == owner for u in (12, 28))
                rent = roll * (10 if both else 4)
            else:
                rent = p["rent"]
            player["money"] -= rent
            o["money"] += rent
            msgs.append(f"💸 Loyer {rent}$ → {o['name']}")
            if player["money"] <= 0:
                player["bankrupt"] = True
                msgs.append(f"💀 {player['name']} en faillite!")
        else:
            msgs.append(f"🏠 Votre propriété : {p['name']}")
    elif new_pos in SPECIAL:
        msgs.append(f"⭐ {SPECIAL[new_pos]}")
        if new_pos == 4:  player["money"] -= 200
        elif new_pos == 38: player["money"] -= 100

    return msgs, pending_buy_pos

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
            "started": room["started"], "pending_buy": room.get("pending_buy"),
            "pending_trade": room.get("pending_trade")}

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
                msgs, pending_buy_pos = do_move(rid, pid)
                for m in msgs:
                    await broadcast(rid, {"event": "chat", "msg": m})
                if pending_buy_pos is not None and pending_buy_pos not in room["owned"]:
                    room["pending_buy"] = pid
                else:
                    room["turn"] += 1
                await broadcast(rid, get_state(rid))
            elif cmd == "buy":
                if room.get("pending_buy") != pid:
                    await ws.send_json({"event": "chat", "msg": "⚠️ Pas votre tour."})
                    continue
                await broadcast(rid, {"event": "chat", "msg": do_buy(rid, pid)})
                room["pending_buy"] = None
                room["turn"] += 1
                await broadcast(rid, get_state(rid))
            elif cmd == "skip_buy":
                if room.get("pending_buy") != pid:
                    continue
                room["pending_buy"] = None
                room["turn"] += 1
                await broadcast(rid, get_state(rid))
            elif cmd == "trade_offer":
                to = msg.get("to")
                if to not in room["players"] or to == pid:
                    await ws.send_json({"event": "chat", "msg": "❌ Joueur invalide."})
                    continue
                room["pending_trade"] = {
                    "from": pid, "to": to,
                    "offer_money": int(msg.get("offer_money", 0)),
                    "offer_props": [int(x) for x in msg.get("offer_props", [])],
                    "req_money":   int(msg.get("req_money", 0)),
                    "req_props":   [int(x) for x in msg.get("req_props", [])],
                }
                from_name = room["players"][pid]["name"]
                to_name   = room["players"][to]["name"]
                await broadcast(rid, {"event": "chat", "msg": f"🤝 {from_name} propose un échange à {to_name}."})
                await broadcast(rid, get_state(rid))
            elif cmd == "trade_accept":
                t = room.get("pending_trade")
                if not t or t["to"] != pid:
                    continue
                giver, taker = room["players"][t["from"]], room["players"][t["to"]]
                # Validate
                if giver["money"] < t["offer_money"] or taker["money"] < t["req_money"]:
                    await broadcast(rid, {"event": "chat", "msg": "❌ Fonds insuffisants pour l'échange."})
                    room["pending_trade"] = None
                    await broadcast(rid, get_state(rid))
                    continue
                if any(room["owned"].get(p) != t["from"] for p in t["offer_props"]) or \
                   any(room["owned"].get(p) != t["to"]   for p in t["req_props"]):
                    await broadcast(rid, {"event": "chat", "msg": "❌ Propriété invalide dans l'échange."})
                    room["pending_trade"] = None
                    await broadcast(rid, get_state(rid))
                    continue
                # Execute
                giver["money"] -= t["offer_money"];  taker["money"] += t["offer_money"]
                taker["money"] -= t["req_money"];    giver["money"] += t["req_money"]
                for p in t["offer_props"]: room["owned"][p] = t["to"]
                for p in t["req_props"]:   room["owned"][p] = t["from"]
                room["pending_trade"] = None
                await broadcast(rid, {"event": "chat", "msg": f"✅ Échange accepté entre {giver['name']} et {taker['name']}!"})
                await broadcast(rid, get_state(rid))
            elif cmd == "trade_reject":
                t = room.get("pending_trade")
                if not t or t["to"] != pid:
                    continue
                room["pending_trade"] = None
                await broadcast(rid, {"event": "chat", "msg": f"❌ Échange refusé par {room['players'][pid]['name']}."})
                await broadcast(rid, get_state(rid))
            elif cmd == "chat":
                n = room["players"][pid]["name"]
                await broadcast(rid, {"event": "chat", "msg": f"💬 {n}: {msg.get('text','')}"})
    except WebSocketDisconnect:
        conns[rid].discard(ws)
        if pid in rooms.get(rid, {}).get("players", {}):
            await broadcast(rid, {"event": "chat", "msg": f"👋 {rooms[rid]['players'][pid]['name']} a quitté."})
