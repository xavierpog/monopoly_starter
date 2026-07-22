import json, random, uuid, asyncio, time
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

# rents = [base, 1h, 2h, 3h, 4h, hotel]
PROPERTIES = {
    1: {"name":"Méditerranée", "price":60,  "rents":[2,  10, 30,  90,  160, 250]},
    3: {"name":"Baltic",       "price":60,  "rents":[4,  20, 60,  180, 320, 450]},
    6: {"name":"Oriental",     "price":100, "rents":[6,  30, 90,  270, 400, 550]},
    8: {"name":"Vermont",      "price":100, "rents":[6,  30, 90,  270, 400, 550]},
    9: {"name":"Connecticut",  "price":120, "rents":[8,  40, 100, 300, 450, 600]},
   11: {"name":"St-Charles",   "price":140, "rents":[10, 50, 150, 450, 625, 750]},
   13: {"name":"États",        "price":140, "rents":[10, 50, 150, 450, 625, 750]},
   14: {"name":"Virginia",     "price":160, "rents":[12, 60, 180, 500, 700, 900]},
   16: {"name":"St-James",     "price":180, "rents":[14, 70, 200, 550, 750, 950]},
   18: {"name":"Tennessee",    "price":180, "rents":[14, 70, 200, 550, 750, 950]},
   19: {"name":"New York",     "price":200, "rents":[16, 80, 220, 600, 800,1000]},
   21: {"name":"Kentucky",     "price":220, "rents":[18, 90, 250, 700, 875,1050]},
   23: {"name":"Indiana",      "price":220, "rents":[18, 90, 250, 700, 875,1050]},
   24: {"name":"Illinois",     "price":240, "rents":[20,100, 300, 750, 925,1100]},
   26: {"name":"Atlantic",     "price":260, "rents":[22,110, 330, 800, 975,1150]},
   27: {"name":"Ventnor",      "price":260, "rents":[22,110, 330, 800, 975,1150]},
   29: {"name":"Marvin",       "price":280, "rents":[24,120, 360, 850,1025,1200]},
   31: {"name":"Pacific",      "price":300, "rents":[26,130, 390, 900,1100,1275]},
   32: {"name":"Caroline N.",  "price":300, "rents":[26,130, 390, 900,1100,1275]},
   34: {"name":"Pennsylvanie", "price":320, "rents":[28,150, 450,1000,1200,1400]},
   37: {"name":"Park",         "price":350, "rents":[35,175, 500,1100,1300,1500]},
   39: {"name":"Boulevard",    "price":400, "rents":[50,200, 600,1400,1700,2000]},
    5: {"name":"Gare 1",       "price":200, "rents":[25,25,25,25,25,25]},
   15: {"name":"Gare 2",       "price":200, "rents":[25,25,25,25,25,25]},
   25: {"name":"Gare 3",       "price":200, "rents":[25,25,25,25,25,25]},
   35: {"name":"Gare 4",       "price":200, "rents":[25,25,25,25,25,25]},
   12: {"name":"Cie Électrique","price":150,"rents":[0,0,0,0,0,0],"utility":True},
   28: {"name":"Cie des Eaux", "price":150, "rents":[0,0,0,0,0,0],"utility":True},
}

# Groupes de couleurs : pos → groupe
COLOR_GROUPS = {
    1:"brown",  3:"brown",
    6:"cyan",   8:"cyan",   9:"cyan",
   11:"pink",  13:"pink",  14:"pink",
   16:"orange",18:"orange",19:"orange",
   21:"red",   23:"red",   24:"red",
   26:"yellow",27:"yellow",29:"yellow",
   31:"green", 32:"green", 34:"green",
   37:"dblue", 39:"dblue",
}
GROUP_MEMBERS = {}
for pos, grp in COLOR_GROUPS.items():
    GROUP_MEMBERS.setdefault(grp, []).append(pos)

HOUSE_PRICE = {"brown":50,"cyan":50,"pink":100,"orange":100,"red":150,"yellow":150,"green":200,"dblue":200}
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
        "goojf": {}, "houses": {}, "game_over": False, "winner": None,
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
            msgs += do_bankruptcy(rid, pid)
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
            msgs += do_bankruptcy(rid, pid)
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
                msgs += do_bankruptcy(rid, pid)
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
                msgs += do_bankruptcy(rid, pid)
        elif owner is None:
            msgs.append(f"🏠 {PROPERTIES[dest]['name']} à vendre — cliquez Acheter")
            return msgs, dest

    return msgs, None  # None = no pending buy

def add_player(rid, pid, name):
    icons = ["🔴", "🔵", "🟢", "🟡"]
    rooms[rid]["players"][pid] = {
        "id": pid, "name": name, "money": 1500, "pos": 0,
        "icon": icons[len(rooms[rid]["players"]) % 4], "bankrupt": False,
        "in_jail": False, "jail_turns": 0, "doubles_streak": 0,
    }
    rooms[rid]["order"].append(pid)

def do_move(rid, pid):
    room, player = rooms[rid], rooms[rid]["players"][pid]
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    roll = d1 + d2
    doubles = (d1 == d2)
    msgs = [f"🎲 {player['name']} fait {d1}+{d2}{'  🎯 Double!' if doubles else ''}"]
    pending_buy_pos = None

    # --- Cas : joueur en prison ---
    if player["in_jail"]:
        if doubles:
            player["in_jail"] = False
            player["jail_turns"] = 0
            player["doubles_streak"] = 0
            msgs.append("🔓 Double! Vous sortez de prison!")
        else:
            player["jail_turns"] += 1
            if player["jail_turns"] >= 3:
                player["money"] -= 50
                player["in_jail"] = False
                player["jail_turns"] = 0
                msgs.append("🚔 3 tours en prison — 50$ payés automatiquement, vous sortez.")
            else:
                msgs.append(f"🚔 Pas de double — vous restez en prison ({player['jail_turns']}/3 tours).")
                return msgs, None  # tour terminé, pas de déplacement
    else:
        # --- Vérifier 3 doubles consécutifs ---
        if doubles:
            player["doubles_streak"] += 1
            if player["doubles_streak"] >= 3:
                player["pos"] = 10
                player["in_jail"] = True
                player["doubles_streak"] = 0
                msgs.append("🚔 3 doubles de suite — En prison!")
                return msgs, None
        else:
            player["doubles_streak"] = 0

    new_pos = (player["pos"] + roll) % 40
    msgs[0] += f" → case {new_pos}"
    if new_pos < player["pos"]:
        player["money"] += 200
        msgs.append("✅ Passage DÉPART +200$")
    player["pos"] = new_pos

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
                h = room.get("houses", {}).get(new_pos, 0)
                base_rent = p["rents"][h]
                # Double loyer si monopole sans maisons
                grp = COLOR_GROUPS.get(new_pos)
                if h == 0 and grp and all(room["owned"].get(m) == owner for m in GROUP_MEMBERS[grp]):
                    base_rent *= 2
                rent = base_rent
            player["money"] -= rent
            o["money"] += rent
            msgs.append(f"💸 Loyer {rent}$ → {o['name']}")
            if player["money"] <= 0:
                msgs += do_bankruptcy(rid, pid)
        else:
            msgs.append(f"🏠 Votre propriété : {p['name']}")
    elif new_pos in SPECIAL:
        msgs.append(f"⭐ {SPECIAL[new_pos]}")
        if new_pos == 4:
            player["money"] -= 200
            if player["money"] <= 0: msgs += do_bankruptcy(rid, pid)
        elif new_pos == 38:
            player["money"] -= 100
            if player["money"] <= 0: msgs += do_bankruptcy(rid, pid)

    return msgs, pending_buy_pos

def do_bankruptcy(rid, pid):
    room = rooms[rid]
    player = room["players"][pid]
    player["bankrupt"] = True
    player["money"] = 0
    # Retirer les maisons du joueur
    for pos in list(room.get("houses", {}).keys()):
        if room["owned"].get(pos) == pid:
            del room["houses"][pos]
    # Retourner les propriétés à la banque
    for pos in list(room["owned"].keys()):
        if room["owned"][pos] == pid:
            del room["owned"][pos]
    # Retirer de l'ordre de jeu
    if pid in room["order"]:
        room["order"].remove(pid)
    if room["order"] and room["turn"] >= len(room["order"]):
        room["turn"] %= len(room["order"])
    msgs = [f"💀 {player['name']} est en faillite! Ses propriétés retournent à la banque."]
    active = [p for p in room["players"].values() if not p["bankrupt"]]
    if len(active) == 1:
        room["game_over"] = True
        room["winner"] = active[0]["id"]
        msgs.append(f"🏆 {active[0]['name']} remporte la partie!")
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

def get_auction_state(room):
    a = room.get("pending_auction")
    if not a:
        return None
    return {
        "pos": a["pos"],
        "pos_name": PROPERTIES[a["pos"]]["name"],
        "from_pid": a["from_pid"],
        "deadline": a["deadline"],
        "eligible": a["eligible"],
        "submitted": list(a["bids"].keys()),
    }

def get_state(rid):
    room = rooms[rid]
    cur = room["order"][room["turn"] % len(room["order"])] if room["order"] else None
    return {"event": "state", "players": list(room["players"].values()),
            "turn": cur, "owned": {str(k): v for k, v in room["owned"].items()},
            "started": room["started"], "pending_buy": room.get("pending_buy"),
            "pending_trade": room.get("pending_trade"),
            "houses": {str(k): v for k, v in room.get("houses", {}).items()},
            "pending_auction": get_auction_state(room),
        "game_over": room.get("game_over", False),
        "winner": room.get("winner")}

async def end_auction(rid):
    room = rooms.get(rid)
    if not room or not room.get("pending_auction"):
        return
    a = room["pending_auction"]
    room["pending_auction"] = None
    bids = a["bids"]  # pid -> amount
    # Fill missing bids as 0
    for p in a["eligible"]:
        if p not in bids:
            bids[p] = 0
    if not bids or all(v == 0 for v in bids.values()):
        await broadcast(rid, {"event": "chat", "msg": f"🔨 Enchère terminée — aucune offre. {PROPERTIES[a['pos']]['name']} reste disponible."})
        room["turn"] += 1
        await broadcast(rid, get_state(rid))
        return
    winner_pid = max(bids, key=lambda p: bids[p])
    winner_amount = bids[winner_pid]
    winner = room["players"][winner_pid]
    # Reveal all bids
    reveal = " | ".join(f"{room['players'][p]['icon']} {room['players'][p]['name']}: {bids[p]}$" for p in bids)
    await broadcast(rid, {"event": "chat", "msg": f"🔨 Résultats enchère : {reveal}"})
    if winner["money"] < winner_amount:
        await broadcast(rid, {"event": "chat", "msg": f"❌ {winner['name']} n'a pas assez d'argent. Terrain non vendu."})
    else:
        winner["money"] -= winner_amount
        room["owned"][a["pos"]] = winner_pid
        await broadcast(rid, {"event": "chat", "msg": f"🏆 {winner['name']} remporte {PROPERTIES[a['pos']]['name']} pour {winner_amount}$!"})
    room["turn"] += 1
    await broadcast(rid, get_state(rid))

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
            elif cmd == "pay_jail":
                cur = room["order"][room["turn"] % len(room["order"])]
                if pid != cur:
                    await ws.send_json({"event":"chat","msg":"⚠️ Pas votre tour."})
                    continue
                player = room["players"][pid]
                if not player["in_jail"]:
                    await ws.send_json({"event":"chat","msg":"❌ Vous n'êtes pas en prison."})
                    continue
                if player["money"] < 50:
                    await ws.send_json({"event":"chat","msg":"❌ Pas assez d'argent (50$ requis)."})
                    continue
                player["money"] -= 50
                player["in_jail"] = False
                player["jail_turns"] = 0
                await broadcast(rid, {"event":"chat","msg":f"🔓 {player['name']} paie 50$ et sort de prison!"})
                await broadcast(rid, get_state(rid))
            elif cmd == "auction":
                if room.get("pending_buy") != pid:
                    continue
                pos = rooms[rid]["players"][pid]["pos"]
                room["pending_buy"] = None
                eligible = [p for p in room["order"] if p != pid and not room["players"][p]["bankrupt"]]
                room["pending_auction"] = {
                    "pos": pos,
                    "from_pid": pid,
                    "eligible": eligible,
                    "bids": {},
                    "deadline": time.time() + 60,
                    "task": None,
                }
                p_name = PROPERTIES[pos]["name"]
                await broadcast(rid, {"event": "chat", "msg": f"🔨 Enchère lancée pour {p_name}! 60 secondes pour miser."})
                await broadcast(rid, get_state(rid))
                task = asyncio.create_task(asyncio.sleep(60))
                room["pending_auction"]["task"] = task
                async def run_auction(r=rid, t=task):
                    try:
                        await t
                        await end_auction(r)
                    except asyncio.CancelledError:
                        pass
                asyncio.create_task(run_auction())
            elif cmd == "bid":
                a = room.get("pending_auction")
                if not a or pid not in a["eligible"] or pid in a["bids"]:
                    continue
                amount = max(0, int(msg.get("amount", 0)))
                a["bids"][pid] = amount
                label = f"{amount}$" if amount > 0 else "passe"
                await broadcast(rid, {"event": "chat", "msg": f"📝 {room['players'][pid]['name']} a misé ({label})."})
                await broadcast(rid, get_state(rid))
                if set(a["eligible"]) == set(a["bids"].keys()):
                    if a.get("task"):
                        a["task"].cancel()
                    await end_auction(rid)
            elif cmd == "build_house":
                pos = int(msg.get("pos", -1))
                grp = COLOR_GROUPS.get(pos)
                if not grp:
                    await ws.send_json({"event":"chat","msg":"❌ Pas constructible."})
                    continue
                if room["owned"].get(pos) != pid:
                    await ws.send_json({"event":"chat","msg":"❌ Vous ne possédez pas cette propriété."})
                    continue
                if not all(room["owned"].get(m) == pid for m in GROUP_MEMBERS[grp]):
                    await ws.send_json({"event":"chat","msg":"❌ Vous devez posséder le monopole complet."})
                    continue
                houses = room["houses"]
                current = houses.get(pos, 0)
                if current >= 5:
                    await ws.send_json({"event":"chat","msg":"❌ Déjà un hôtel sur cette propriété."})
                    continue
                # Construction équitable : ne peut pas avoir plus d'une maison de plus que les autres du groupe
                max_others = max((houses.get(m, 0) for m in GROUP_MEMBERS[grp] if m != pos), default=0)
                if current >= max_others + 1:
                    await ws.send_json({"event":"chat","msg":"❌ Construction doit être équitable entre les propriétés du groupe."})
                    continue
                cost = HOUSE_PRICE[grp]
                if rooms[rid]["players"][pid]["money"] < cost:
                    await ws.send_json({"event":"chat","msg":f"❌ Pas assez d'argent ({cost}$ requis)."})
                    continue
                rooms[rid]["players"][pid]["money"] -= cost
                houses[pos] = current + 1
                label = "hôtel" if houses[pos] == 5 else f"{houses[pos]} maison(s)"
                p_name = PROPERTIES[pos]["name"]
                await broadcast(rid, {"event":"chat","msg":f"🏗️ {rooms[rid]['players'][pid]['name']} construit sur {p_name} ({label}) pour {cost}$"})
                await broadcast(rid, get_state(rid))
            elif cmd == "sell_house":
                pos = int(msg.get("pos", -1))
                grp = COLOR_GROUPS.get(pos)
                if not grp or room["owned"].get(pos) != pid:
                    await ws.send_json({"event":"chat","msg":"❌ Impossible."})
                    continue
                houses = room["houses"]
                current = houses.get(pos, 0)
                if current == 0:
                    await ws.send_json({"event":"chat","msg":"❌ Aucune maison à vendre."})
                    continue
                # Vente équitable : ne peut pas vendre si les autres ont moins
                min_others = min((houses.get(m, 0) for m in GROUP_MEMBERS[grp] if m != pos), default=0)
                if current <= min_others:
                    await ws.send_json({"event":"chat","msg":"❌ Vente doit être équitable."})
                    continue
                refund = HOUSE_PRICE[grp] // 2
                rooms[rid]["players"][pid]["money"] += refund
                if current == 1:
                    del houses[pos]
                else:
                    houses[pos] = current - 1
                p_name = PROPERTIES[pos]["name"]
                await broadcast(rid, {"event":"chat","msg":f"💰 {rooms[rid]['players'][pid]['name']} vend une maison sur {p_name} (+{refund}$)"})
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
