"""
Tests pour la logique de jeu de app.py.
Lancer depuis la racine du projet : pytest tests/
"""
import time
import re
import html as html_lib
import pytest
from unittest.mock import patch

from app import (
    rooms, conns,
    new_room, add_player, draw_card, nearest,
    do_buy, do_bankruptcy, do_move, apply_card,
    get_state, get_auction_state,
    PROPERTIES, COLOR_GROUPS, GROUP_MEMBERS, HOUSE_PRICE,
    RAILROADS, UTILITIES,
)

# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_rooms():
    """Réinitialise l'état global avant chaque test."""
    rooms.clear()
    conns.clear()
    yield
    rooms.clear()
    conns.clear()

@pytest.fixture
def room2():
    """Salle avec deux joueurs (Alice=p1, Bob=p2), partie démarrée."""
    rid = "test"
    new_room(rid)
    add_player(rid, "p1", "Alice")
    add_player(rid, "p2", "Bob")
    rooms[rid]["started"] = True
    return rid

def dice(d1, d2):
    """Retourne la liste side_effect pour mocker random.randint(1,6)."""
    return [d1, d2]

# ── new_room ───────────────────────────────────────────────────────────────────

class TestNewRoom:
    def test_etat_initial_vide(self):
        new_room("r1")
        r = rooms["r1"]
        assert r["players"] == {}
        assert r["order"] == []
        assert r["turn"] == 0
        assert r["started"] is False
        assert r["owned"] == {}
        assert r["pending_buy"] is None
        assert r["pending_tax"] is None
        assert r["mortgaged"] == {}
        assert r["houses"] == {}
        assert r["game_over"] is False
        assert r["winner"] is None
        assert r["extra_roll"] is None

    def test_cree_conns_pour_la_salle(self):
        new_room("r1")
        assert "r1" in conns
        assert isinstance(conns["r1"], set)

    def test_paquets_cartes_complets(self):
        from app import CHANCE_CARDS, COMMUNITY_CARDS
        new_room("r1")
        assert len(rooms["r1"]["chance_deck"]) == len(CHANCE_CARDS)
        assert len(rooms["r1"]["community_deck"]) == len(COMMUNITY_CARDS)

# ── add_player ─────────────────────────────────────────────────────────────────

class TestAddPlayer:
    def test_argent_initial_1500(self):
        new_room("r1")
        add_player("r1", "p1", "Alice")
        assert rooms["r1"]["players"]["p1"]["money"] == 1500

    def test_position_initiale_zero(self):
        new_room("r1")
        add_player("r1", "p1", "Alice")
        assert rooms["r1"]["players"]["p1"]["pos"] == 0

    def test_ajoute_a_l_ordre(self):
        new_room("r1")
        add_player("r1", "p1", "Alice")
        add_player("r1", "p2", "Bob")
        assert rooms["r1"]["order"] == ["p1", "p2"]

    def test_pas_en_faillite_au_debut(self):
        new_room("r1")
        add_player("r1", "p1", "Alice")
        assert rooms["r1"]["players"]["p1"]["bankrupt"] is False

    def test_pas_en_prison_au_debut(self):
        new_room("r1")
        add_player("r1", "p1", "Alice")
        assert rooms["r1"]["players"]["p1"]["in_jail"] is False

    def test_icones_cyclent_sur_4(self):
        new_room("r1")
        icons = ["🔴", "🔵", "🟢", "🟡"]
        for i, pid in enumerate(["p1", "p2", "p3", "p4"]):
            add_player("r1", pid, pid)
        for i, pid in enumerate(["p1", "p2", "p3", "p4"]):
            assert rooms["r1"]["players"][pid]["icon"] == icons[i]

# ── draw_card ──────────────────────────────────────────────────────────────────

class TestDrawCard:
    def test_retourne_la_premiere_carte(self):
        deck = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        assert draw_card(deck)["id"] == "a"

    def test_cycle_infini(self):
        deck = [{"id": "a"}, {"id": "b"}]
        tirages = [draw_card(deck)["id"] for _ in range(4)]
        assert tirages == ["a", "b", "a", "b"]

    def test_longueur_paquet_inchangee(self):
        deck = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        draw_card(deck)
        assert len(deck) == 3

# ── nearest ────────────────────────────────────────────────────────────────────

class TestNearest:
    def test_gare_suivante_en_avant(self):
        # Depuis la case 6, la prochaine gare en avant est la 15
        assert nearest(6, RAILROADS) == 15

    def test_boucle_en_fin_de_plateau(self):
        # Depuis la case 36, la prochaine gare est la 5 (après la case 40)
        assert nearest(36, RAILROADS) == 5

    def test_distance_zero_sur_la_cible(self):
        # Si déjà sur une gare, celle-ci est la plus proche (distance 0)
        assert nearest(5, RAILROADS) == 5

    def test_compagnie_suivante_en_avant(self):
        # Depuis la case 3, la prochaine compagnie est la 12
        assert nearest(3, UTILITIES) == 12

    def test_compagnie_suivante_deuxieme(self):
        # Depuis la case 20, la prochaine compagnie est la 28
        assert nearest(20, UTILITIES) == 28

# ── do_buy ─────────────────────────────────────────────────────────────────────

class TestDoBuy:
    def test_achat_reussi(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 1  # Méditerranée $60
        result = do_buy(room2, "p1")
        assert "achète" in result
        assert rooms[room2]["players"]["p1"]["money"] == 1440
        assert rooms[room2]["owned"][1] == "p1"

    def test_pas_assez_d_argent(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 39  # Boulevard $400
        rooms[room2]["players"]["p1"]["money"] = 100
        result = do_buy(room2, "p1")
        assert "❌" in result
        assert 39 not in rooms[room2]["owned"]

    def test_propriete_deja_achetee(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 1
        rooms[room2]["owned"][1] = "p2"
        result = do_buy(room2, "p1")
        assert "❌" in result

    def test_case_non_achetable(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 0  # DÉPART
        result = do_buy(room2, "p1")
        assert "❌" in result

# ── do_bankruptcy ──────────────────────────────────────────────────────────────

class TestDoBankruptcy:
    def test_marque_le_joueur_en_faillite(self, room2):
        do_bankruptcy(room2, "p1")
        assert rooms[room2]["players"]["p1"]["bankrupt"] is True

    def test_argent_mis_a_zero(self, room2):
        do_bankruptcy(room2, "p1")
        assert rooms[room2]["players"]["p1"]["money"] == 0

    def test_proprietes_retournent_a_la_banque(self, room2):
        rooms[room2]["owned"][1] = "p1"
        rooms[room2]["owned"][3] = "p1"
        do_bankruptcy(room2, "p1")
        assert 1 not in rooms[room2]["owned"]
        assert 3 not in rooms[room2]["owned"]

    def test_maisons_supprimees(self, room2):
        rooms[room2]["owned"][1] = "p1"
        rooms[room2]["houses"][1] = 3
        do_bankruptcy(room2, "p1")
        assert 1 not in rooms[room2]["houses"]

    def test_hypotheques_effacees(self, room2):
        rooms[room2]["owned"][1] = "p1"
        rooms[room2]["mortgaged"][1] = True
        do_bankruptcy(room2, "p1")
        assert 1 not in rooms[room2]["mortgaged"]

    def test_retire_de_l_ordre_de_jeu(self, room2):
        do_bankruptcy(room2, "p1")
        assert "p1" not in rooms[room2]["order"]

    def test_victoire_si_un_seul_joueur_reste(self, room2):
        do_bankruptcy(room2, "p1")
        assert rooms[room2]["game_over"] is True
        assert rooms[room2]["winner"] == "p2"

    def test_pas_de_victoire_si_deux_joueurs_restent(self):
        new_room("r3")
        for pid in ("p1", "p2", "p3"):
            add_player("r3", pid, pid)
        do_bankruptcy("r3", "p1")
        assert rooms["r3"]["game_over"] is False

# ── do_move ────────────────────────────────────────────────────────────────────

class TestDoMove:
    def test_deplacement_de_base(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(3, 5)):  # = 8 (Vermont, propriété sans carte)
            do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["pos"] == 8

    def test_propriete_a_vendre_retourne_buy_pos(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(1, 2)):  # → case 3 Baltic
            _, buy_pos, _ = do_move(room2, "p1")
        assert buy_pos == 3

    def test_passage_depart_donne_200(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 38
        with patch("app.random.randint", side_effect=dice(2, 1)):  # 38+3 → 1
            do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["money"] == 1700

    def test_case_30_envoie_en_prison(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 24
        with patch("app.random.randint", side_effect=dice(3, 3)):  # 24+6 = 30
            msgs, _, can_roll = do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["pos"] == 10
        assert rooms[room2]["players"]["p1"]["in_jail"] is True
        assert can_roll is False  # doubles n'accordent pas de relance quand on va en prison
        assert any("prison" in m.lower() for m in msgs)

    def test_double_permet_de_rejouer(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(3, 3)):
            _, _, can_roll = do_move(room2, "p1")
        assert can_roll is True

    def test_sans_double_pas_de_rejeu(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(2, 3)):
            _, _, can_roll = do_move(room2, "p1")
        assert can_roll is False

    def test_trois_doubles_envoient_en_prison(self, room2):
        rooms[room2]["players"]["p1"]["doubles_streak"] = 2
        with patch("app.random.randint", side_effect=dice(3, 3)):
            _, _, can_roll = do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["in_jail"] is True
        assert rooms[room2]["players"]["p1"]["pos"] == 10
        assert can_roll is False

    def test_taxe_de_luxe_deduit_100(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 32  # 32+6=38 (luxe)
        with patch("app.random.randint", side_effect=dice(3, 3)):
            msgs, _, _ = do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["money"] == 1400
        assert any("100" in m for m in msgs)

    def test_taxe_sur_revenu_set_pending_tax(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(2, 2)):  # → case 4
            do_move(room2, "p1")
        assert rooms[room2]["pending_tax"] == "p1"

    def test_loyer_verse_au_proprietaire(self, room2):
        rooms[room2]["owned"][3] = "p2"  # Bob possède Baltic (loyer de base : 4$)
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(1, 2)):  # → case 3
            do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["money"] == 1496
        assert rooms[room2]["players"]["p2"]["money"] == 1504

    def test_loyer_double_avec_monopole(self, room2):
        rooms[room2]["owned"][1] = "p2"
        rooms[room2]["owned"][3] = "p2"  # Bob a le monopole marron
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(1, 2)):  # → case 3
            do_move(room2, "p1")
        # loyer de base 4$ × 2 = 8$
        assert rooms[room2]["players"]["p1"]["money"] == 1492

    def test_propriete_hypothequee_pas_de_loyer(self, room2):
        rooms[room2]["owned"][3] = "p2"
        rooms[room2]["mortgaged"][3] = True
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(1, 2)):
            do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["money"] == 1500  # aucun loyer

    def test_une_gare_loyer_25(self, room2):
        rooms[room2]["owned"][5] = "p2"
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(2, 3)):  # → case 5
            do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["money"] == 1475

    def test_deux_gares_loyer_50(self, room2):
        rooms[room2]["owned"][5] = "p2"
        rooms[room2]["owned"][15] = "p2"
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(2, 3)):
            do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["money"] == 1450

    def test_trois_gares_loyer_100(self, room2):
        rooms[room2]["owned"][5] = "p2"
        rooms[room2]["owned"][15] = "p2"
        rooms[room2]["owned"][25] = "p2"
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(2, 3)):
            do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["money"] == 1400

    def test_quatre_gares_loyer_200(self, room2):
        for r in RAILROADS:
            rooms[room2]["owned"][r] = "p2"
        rooms[room2]["players"]["p1"]["pos"] = 0
        with patch("app.random.randint", side_effect=dice(2, 3)):
            do_move(room2, "p1")
        assert rooms[room2]["players"]["p1"]["money"] == 1300

    def test_une_compagnie_loyer_4x(self, room2):
        rooms[room2]["owned"][12] = "p2"
        rooms[room2]["players"]["p1"]["pos"] = 6  # 6+6=12
        with patch("app.random.randint", side_effect=dice(3, 3)):  # roll=6
            do_move(room2, "p1")
        # 1 compagnie : 6 × 4 = 24$
        assert rooms[room2]["players"]["p1"]["money"] == 1476

    def test_deux_compagnies_loyer_10x(self, room2):
        rooms[room2]["owned"][12] = "p2"
        rooms[room2]["owned"][28] = "p2"
        rooms[room2]["players"]["p1"]["pos"] = 6
        with patch("app.random.randint", side_effect=dice(3, 3)):  # roll=6
            do_move(room2, "p1")
        # 2 compagnies : 6 × 10 = 60$
        assert rooms[room2]["players"]["p1"]["money"] == 1440

    def test_prison_pas_de_double_reste(self, room2):
        p = rooms[room2]["players"]["p1"]
        p["in_jail"] = True; p["jail_turns"] = 0; p["pos"] = 10
        with patch("app.random.randint", side_effect=dice(2, 3)):
            _, _, can_roll = do_move(room2, "p1")
        assert p["in_jail"] is True
        assert p["jail_turns"] == 1
        assert can_roll is False

    def test_prison_double_libere(self, room2):
        p = rooms[room2]["players"]["p1"]
        p["in_jail"] = True; p["jail_turns"] = 1; p["pos"] = 10
        with patch("app.random.randint", side_effect=dice(3, 3)):
            do_move(room2, "p1")
        assert p["in_jail"] is False

    def test_prison_3eme_tour_paye_50_auto(self, room2):
        p = rooms[room2]["players"]["p1"]
        p["in_jail"] = True; p["jail_turns"] = 2; p["pos"] = 10
        with patch("app.random.randint", side_effect=dice(2, 3)):
            do_move(room2, "p1")
        assert p["in_jail"] is False
        assert p["money"] == 1450  # 1500 - 50$

# ── apply_card ─────────────────────────────────────────────────────────────────

class TestApplyCard:
    def test_gain(self, room2):
        apply_card(room2, "p1", {"action": "gain", "amount": 50, "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["money"] == 1550

    def test_lose(self, room2):
        apply_card(room2, "p1", {"action": "lose", "amount": 100, "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["money"] == 1400

    def test_goto_sans_passage_depart(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 5
        apply_card(room2, "p1", {"action": "goto", "dest": 39, "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["pos"] == 39
        assert rooms[room2]["players"]["p1"]["money"] == 1500

    def test_goto_avec_passage_depart(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 20
        apply_card(room2, "p1", {"action": "goto", "dest": 5, "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["pos"] == 5
        assert rooms[room2]["players"]["p1"]["money"] == 1700  # +200$

    def test_goto_case_depart_donne_400(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 10
        apply_card(room2, "p1", {"action": "goto", "dest": 0, "text": ""}, 0)
        # dest<=pos → +200, puis dest==0 → +200 de plus
        assert rooms[room2]["players"]["p1"]["money"] == 1900

    def test_jail_teleporte_case_10(self, room2):
        apply_card(room2, "p1", {"action": "jail", "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["pos"] == 10
        assert rooms[room2]["players"]["p1"]["in_jail"] is True

    def test_goojf_incremente_compteur(self, room2):
        apply_card(room2, "p1", {"action": "goojf", "text": ""}, 0)
        assert rooms[room2]["goojf"].get("p1", 0) == 1

    def test_goojf_s_accumule(self, room2):
        rooms[room2]["goojf"]["p1"] = 1
        apply_card(room2, "p1", {"action": "goojf", "text": ""}, 0)
        assert rooms[room2]["goojf"]["p1"] == 2

    def test_pay_all_distribue_aux_autres(self, room2):
        apply_card(room2, "p1", {"action": "pay_all", "amount": 50, "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["money"] == 1450
        assert rooms[room2]["players"]["p2"]["money"] == 1550

    def test_collect_all_prend_aux_autres(self, room2):
        apply_card(room2, "p1", {"action": "collect_all", "amount": 10, "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["money"] == 1510
        assert rooms[room2]["players"]["p2"]["money"] == 1490

    def test_repairs_maisons_et_hotel(self, room2):
        rooms[room2]["owned"][1] = "p1"
        rooms[room2]["houses"][1] = 3   # 3 maisons → 3×25 = 75$
        rooms[room2]["owned"][3] = "p1"
        rooms[room2]["houses"][3] = 5   # 1 hôtel → 1×100 = 100$
        apply_card(room2, "p1", {"action": "repairs", "house": 25, "hotel": 100, "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["money"] == 1325  # 1500 - 175

    def test_back3(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 10
        apply_card(room2, "p1", {"action": "back3", "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["pos"] == 7

    def test_back3_boucle(self, room2):
        rooms[room2]["players"]["p1"]["pos"] = 2
        apply_card(room2, "p1", {"action": "back3", "text": ""}, 0)
        assert rooms[room2]["players"]["p1"]["pos"] == 39  # (2-3) % 40

    def test_nearest_railroad_double_loyer_carte(self, room2):
        rooms[room2]["owned"][5] = "p2"  # Bob possède Gare 1
        rooms[room2]["players"]["p1"]["pos"] = 2  # prochaine gare : case 5
        apply_card(room2, "p1", {"action": "nearest_railroad", "text": ""}, 6)
        # 1 gare, doublé par la carte Chance : 25 × 2^1 = 50$
        assert rooms[room2]["players"]["p1"]["money"] == 1450

    def test_nearest_utility_10x_roll(self, room2):
        rooms[room2]["owned"][12] = "p2"
        rooms[room2]["players"]["p1"]["pos"] = 7  # prochaine compagnie : case 12
        apply_card(room2, "p1", {"action": "nearest_utility", "text": ""}, 5)
        # roll=5, loyer = 5 × 10 = 50$
        assert rooms[room2]["players"]["p1"]["money"] == 1450

# ── get_state ──────────────────────────────────────────────────────────────────

class TestGetState:
    def test_cle_event(self, room2):
        assert get_state(room2)["event"] == "state"

    def test_nombre_joueurs(self, room2):
        assert len(get_state(room2)["players"]) == 2

    def test_tour_premier_joueur(self, room2):
        assert get_state(room2)["turn"] == "p1"

    def test_pending_tax_inclus(self, room2):
        rooms[room2]["pending_tax"] = "p1"
        assert get_state(room2)["pending_tax"] == "p1"

    def test_mortgaged_serialise_en_string(self, room2):
        rooms[room2]["mortgaged"][5] = True
        state = get_state(room2)
        assert "5" in state["mortgaged"]
        assert state["mortgaged"]["5"] is True

    def test_goojf_par_joueur(self, room2):
        rooms[room2]["goojf"]["p1"] = 2
        p1 = next(p for p in get_state(room2)["players"] if p["id"] == "p1")
        assert p1["goojf"] == 2

    def test_game_over_et_gagnant(self, room2):
        rooms[room2]["game_over"] = True
        rooms[room2]["winner"] = "p2"
        state = get_state(room2)
        assert state["game_over"] is True
        assert state["winner"] == "p2"

# ── get_auction_state ──────────────────────────────────────────────────────────

class TestGetAuctionState:
    def test_none_sans_enchere(self, room2):
        assert get_auction_state(rooms[room2]) is None

    def test_structure_sans_task(self, room2):
        rooms[room2]["pending_auction"] = {
            "pos": 5, "from_pid": "p1",
            "eligible": ["p2"], "bids": {"p2": 150},
            "deadline": time.time() + 30, "task": object(),
        }
        state = get_auction_state(rooms[room2])
        assert state["pos"] == 5
        assert state["pos_name"] == "Gare 1"
        assert state["submitted"] == ["p2"]
        assert "task" not in state  # non JSON-sérialisable, doit être exclu

# ── Sanitisation des entrées ───────────────────────────────────────────────────

def _rid(s):
    return re.sub(r"[^a-zA-Z0-9_-]", "", s)[:30] or "default"

def _name(s):
    return re.sub(r"\s+", " ", html_lib.escape(s[:40])).strip()[:20] or "Joueur"

class TestSanitisation:
    def test_rid_retire_caracteres_speciaux(self):
        assert _rid("room<script>") == "roomscript"

    def test_rid_conserve_alphanumerique_et_tirets(self):
        assert _rid("ma-salle_1") == "ma-salle_1"

    def test_rid_tronque_a_30(self):
        assert len(_rid("a" * 50)) == 30

    def test_rid_vide_devient_default(self):
        assert _rid("!!!") == "default"

    def test_nom_echappe_balises_html(self):
        result = _name("<script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result

    def test_nom_tronque_a_20(self):
        assert len(_name("A" * 100)) <= 20

    def test_nom_collapse_espaces(self):
        result = _name("Alice   Bob")
        assert "  " not in result

    def test_nom_vide_devient_joueur(self):
        assert _name("   ") == "Joueur"
