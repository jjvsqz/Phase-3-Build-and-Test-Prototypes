"""CRAVD: playable, multi-browser Phase 3 classroom prototype.
Synthetic campus menu and fictional user roles, no student data or real campus menu feeds.
"""
import json
import os
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CRAVD_DB_PATH", str(BASE_DIR / "cravd_demo.sqlite3")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SURVEY_URL = os.getenv("SURVEY_URL", "").strip()

app = FastAPI(title="CRAVD Phase 3 Playable Prototype", version="1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

PERSONAS = {
    "User01": {"role": "Organizer", "favorites": ["bowl", "matcha"], "color": "#bddad0"},
    "User02": {"role": "Friend", "favorites": ["pizza", "sandwich", "coldbrew"], "color": "#e5c4b9"},
    "User03": {"role": "Friend", "favorites": ["pizza", "bowl", "burrito"], "color": "#c9c5e8"},
    "User04": {"role": "Optional friend", "favorites": ["matcha", "burrito"], "color": "#f1d98f"},
}
SLOTS = ["Thu 11:30 AM", "Thu 12:00 PM", "Thu 12:30 PM", "Thu 1:00 PM"]
ALLOWED_TAGS = ["Flavorful", "Too salty", "Filling", "Light", "Good value", "Spicy", "Fresh", "Would try again"]
ITEMS = [
    {"id":"pizza", "name":"Pepperoni Pizza", "category":"Pizza", "venue":"Campus Slice", "emoji":"🍕", "description":"A crispy slice with tomato sauce and pepperoni.", "note":"Available in this fictional Thursday menu", "seasonal": False, "available": True, "gradient":"#f3cab0"},
    {"id":"bowl", "name":"Honey Sesame Bowl", "category":"Bowls", "venue":"Campus Bowls", "emoji":"🍚", "description":"Rice, seasoned chicken, vegetables, and sesame sauce.", "note":"Sample item", "seasonal": False, "available": True, "gradient":"#d8e6c1"},
    {"id":"matcha", "name":"Iced Matcha Latte", "category":"Drinks", "venue":"Campus Café", "emoji":"🍵", "description":"Iced matcha with a creamy milk base.", "note":"Sample item", "seasonal": False, "available": True, "gradient":"#d0e0bb"},
    {"id":"sandwich", "name":"Crispy Chicken Sandwich", "category":"Sandwiches", "venue":"Dining Commons", "emoji":"🍔", "description":"Crunchy chicken, lettuce, and tangy sauce on a bun.", "note":"Sample item", "seasonal": False, "available": True, "gradient":"#f4d4a8"},
    {"id":"burrito", "name":"Veggie Burrito", "category":"Wraps", "venue":"Campus Grill", "emoji":"🌯", "description":"Beans, roasted peppers, avocado, and rice.", "note":"Sample item", "seasonal": False, "available": True, "gradient":"#cde6db"},
    {"id":"coldbrew", "name":"Cinnamon Apple Cold Brew", "category":"Drinks", "venue":"Campus Café", "emoji":"🥤", "description":"A limited-time cold brew with cinnamon and apple.", "note":"This week's simulated seasonal item", "seasonal": True, "available": True, "gradient":"#ecd2bf"},
]
ITEM_LOOKUP = {item["id"]: item for item in ITEMS}


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS rooms (code TEXT PRIMARY KEY, state TEXT NOT NULL, updated REAL NOT NULL)")

init_db()


def seed_state():
    members = {
        name: {**persona, "claimed": False, "token": None, "last_seen": 0, "sharing": True}
        for name, persona in PERSONAS.items()
    }
    return {"created": time.time(), "members": members, "invites": [], "events": [], "event_id": 0}


def add_event(state: dict, actor: str, event: str, detail: str = ""):
    state["event_id"] += 1
    state["events"].append({"id": state["event_id"], "at": round(time.time(), 2), "actor": actor, "type": event, "detail": detail[:120]})
    state["events"] = state["events"][-80:]


def create_code():
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # omit ambiguous O/I/0/1
    return "".join(secrets.choice(alphabet) for _ in range(6))


def read_state(conn, code: str):
    row = conn.execute("SELECT state FROM rooms WHERE code=?", (code.upper(),)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Room not found. Double-check the six-character code.")
    return json.loads(row["state"])


def save_state(conn, code: str, state: dict):
    conn.execute("UPDATE rooms SET state=?, updated=? WHERE code=?", (json.dumps(state, separators=(",", ":")), time.time(), code.upper()))


def viewer_for_token(state: dict, token: str | None):
    if not token:
        return None
    for name, p in state["members"].items():
        if p["token"] and secrets.compare_digest(p["token"], token):
            return name
    return None


def exposed(state: dict, viewer: str | None, room_code: str):
    now = time.time()
    members = {}
    for name, p in state["members"].items():
        favorites = p["favorites"] if p["sharing"] or viewer == name else []
        members[name] = {
            "role": p["role"], "favorites": favorites, "color": p["color"],
            "joined": p["claimed"], "online": p["claimed"] and now - p["last_seen"] < 18,
            "sharing": p["sharing"],
        }
    return {"code": room_code, "viewer": viewer, "members": members,
            "items": ITEMS, "slots": SLOTS, "tags": ALLOWED_TAGS,
            "invites": state["invites"], "events": state["events"][-30:],
            "survey_url": SURVEY_URL, "server_time": now, "fictional_demo": True}


class JoinPayload(BaseModel):
    role: str

class ActionPayload(BaseModel):
    token: str
    action: str
    data: dict[str, Any] = {}


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/guide")
def guide():
    return FileResponse(BASE_DIR / "static" / "guide.html")

@app.get("/api/guide-config")
def guide_config():
    return {"survey_url": SURVEY_URL}


@app.get("/api/health")
def health():
    return {"ok": True, "name": "CRAVD classroom prototype", "rooms_db": DB_PATH.name}


@app.post("/api/rooms")
def create_room():
    state = seed_state()
    add_event(state, "System", "room_created", "Created a role-play room")
    with connect() as conn:
        for _ in range(20):
            code = create_code()
            try:
                conn.execute("INSERT INTO rooms (code, state, updated) VALUES (?, ?, ?)", (code, json.dumps(state), time.time()))
                return {"code": code, "guide": f"/guide?room={code}"}
            except sqlite3.IntegrityError:
                pass
    raise HTTPException(503, "Unable to create room, please try again")


@app.post("/api/rooms/{code}/join")
def join_room(code: str, payload: JoinPayload):
    code = code.upper().strip()
    role = payload.role
    if role not in PERSONAS:
        raise HTTPException(400, "Select one of the available demo roles")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        state = read_state(conn, code)
        member = state["members"][role]
        if member["claimed"]:
            raise HTTPException(409, f"{role} is already being used. Select another role or create a new room.")
        token = secrets.token_urlsafe(32)
        member.update({"claimed": True, "token": token, "last_seen": time.time()})
        add_event(state, role, "joined", "Joined the lunch scenario")
        save_state(conn, code, state)
        return {"code": code, "token": token, "role": role}


@app.get("/api/rooms/{code}")
def get_room(code: str, token: str = ""):
    code = code.upper().strip()
    with connect() as conn:
        state = read_state(conn, code)
        viewer = viewer_for_token(state, token)
        if viewer:
            if time.time() - state["members"][viewer]["last_seen"] > 4:
                conn.execute("BEGIN IMMEDIATE")
                state = read_state(conn, code)
                viewer = viewer_for_token(state, token)
                if viewer:
                    state["members"][viewer]["last_seen"] = time.time()
                    save_state(conn, code, state)
        return exposed(state, viewer, code)


def validate_string(value, limit=200):
    if not isinstance(value, str):
        raise HTTPException(400, "Text field must be a string")
    return value.strip()[:limit]


def require_invite(state, invite_id):
    for invite in state["invites"]:
        if invite["id"] == invite_id:
            return invite
    raise HTTPException(404, "Lunch plan not found")


def shared_slots(invite: dict):
    """A time is common only when every invited member has explicitly accepted it."""
    if any(name not in invite["responses"] for name in invite["invitees"]):
        return []
    common = set(invite["slots"])
    for name in invite["invitees"]:
        common &= set(invite["responses"][name]["slots"])
    return [x for x in invite["slots"] if x in common]


@app.post("/api/rooms/{code}/action")
def act(code: str, payload: ActionPayload):
    code = code.upper().strip()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        state = read_state(conn, code)
        actor = viewer_for_token(state, payload.token)
        if not actor:
            raise HTTPException(403, "Choose your role to participate in this room")
        action, data = payload.action, payload.data
        result = {}
        if action == "toggle_favorite":
            item_id = data.get("item_id")
            if item_id not in ITEM_LOOKUP:
                raise HTTPException(400, "Unknown dish")
            favs = state["members"][actor]["favorites"]
            if item_id in favs:
                favs.remove(item_id)
                add_event(state, actor, "favorite_removed", ITEM_LOOKUP[item_id]["name"])
            else:
                favs.append(item_id)
                add_event(state, actor, "favorite_added", ITEM_LOOKUP[item_id]["name"])
        elif action == "set_sharing":
            state["members"][actor]["sharing"] = bool(data.get("sharing"))
            add_event(state, actor, "privacy_updated", "Favorites visibility changed")
        elif action == "create_invite":
            item_id = data.get("item_id")
            invited = data.get("invitees", [])
            slots = data.get("slots", [])
            if item_id not in ITEM_LOOKUP:
                raise HTTPException(400, "Select a sample dish")
            if not isinstance(invited, list) or not (1 <= len(invited) <= 3) or any(x not in PERSONAS or x == actor for x in invited) or len(set(invited)) != len(invited):
                raise HTTPException(400, "Invite one to three other roles")
            if not isinstance(slots, list) or not slots or len(slots) > 4 or any(x not in SLOTS for x in slots):
                raise HTTPException(400, "Select one or more Thursday lunch times")
            invite = {
                "id": uuid.uuid4().hex[:10], "item_id": item_id, "organizer": actor,
                "invitees": invited, "slots": [s for s in SLOTS if s in slots],
                "responses": {}, "confirmed_slot": None, "stage": "planning", "created": time.time(),
                "messages": [], "reviews": [], "votes": {},
            }
            state["invites"].append(invite)
            add_event(state, actor, "invited", f"{', '.join(invited)} → {ITEM_LOOKUP[item_id]['name']}")
            result["invite_id"] = invite["id"]
        elif action == "respond":
            invite = require_invite(state, data.get("invite_id"))
            if actor not in invite["invitees"]:
                raise HTTPException(403, "Only invited friends can RSVP")
            if invite["stage"] != "planning":
                raise HTTPException(400, "This lunch has already been scheduled")
            times = data.get("slots", [])
            if not isinstance(times, list) or any(x not in invite["slots"] for x in times):
                raise HTTPException(400, "Choose from the proposed time slots")
            note = validate_string(data.get("note", ""), 140)
            invite["responses"][actor] = {"slots": list(dict.fromkeys(times)), "note": note, "at": time.time()}
            add_event(state, actor, "rsvp", f"Responded to {ITEM_LOOKUP[invite['item_id']]['name']}")
        elif action == "message":
            invite = require_invite(state, data.get("invite_id"))
            if actor not in invite["invitees"] + [invite["organizer"]]:
                raise HTTPException(403, "Only invited participants can post")
            body = validate_string(data.get("text", ""), 240)
            if not body:
                raise HTTPException(400, "Type a message")
            invite["messages"].append({"author": actor, "text": body, "at": time.time()})
            invite["messages"] = invite["messages"][-35:]
            add_event(state, actor, "message", "Sent a note in the lunch plan")
        elif action == "change_slots":
            invite = require_invite(state, data.get("invite_id"))
            if invite["organizer"] != actor or invite["stage"] != "planning":
                raise HTTPException(403, "Only the organizer can revise proposed times")
            slots = data.get("slots", [])
            if not isinstance(slots, list) or not slots or any(x not in SLOTS for x in slots):
                raise HTTPException(400, "Select one or more valid times")
            invite["slots"] = [s for s in SLOTS if s in slots]
            invite["responses"] = {}  # everyone must RSVP again after proposed times change
            add_event(state, actor, "times_revised", "Revised times; RSVPs need refreshing")
        elif action == "confirm":
            invite = require_invite(state, data.get("invite_id"))
            selected = data.get("slot")
            if actor != invite["organizer"] or invite["stage"] != "planning":
                raise HTTPException(403, "Only organizer can confirm a pending plan")
            if selected not in shared_slots(invite):
                raise HTTPException(400, "Pick a time that every invited friend has accepted")
            invite["confirmed_slot"] = selected
            invite["stage"] = "scheduled"
            add_event(state, actor, "confirmed", f"Lunch confirmed at {selected}")
        elif action == "finish_meal":
            invite = require_invite(state, data.get("invite_id"))
            if actor != invite["organizer"] or invite["stage"] != "scheduled":
                raise HTTPException(403, "The organizer can simulate finishing a scheduled lunch")
            invite["stage"] = "reviewing"
            add_event(state, actor, "meal_finished", "Time jump: group has finished lunch")
        elif action == "review":
            invite = require_invite(state, data.get("invite_id"))
            if actor not in invite["invitees"] + [invite["organizer"]] or invite["stage"] != "reviewing":
                raise HTTPException(400, "Wait until the simulated lunch is finished")
            tags = data.get("tags", [])
            note = validate_string(data.get("note", ""), 180)
            if not isinstance(tags, list) or len(tags) > 3 or any(t not in ALLOWED_TAGS for t in tags):
                raise HTTPException(400, "Select up to three reaction tags")
            if not note and not tags:
                raise HTTPException(400, "Add at least a quick tag or a short note")
            if actor in [r["author"] for r in invite["reviews"]]:
                raise HTTPException(400, "You've already added your perspective to this review")
            invite["reviews"].append({"author": actor, "tags": list(dict.fromkeys(tags)), "note": note, "at": time.time()})
            add_event(state, actor, "review", "Added a quick perspective to the group review")
        elif action == "upvote":
            invite = require_invite(state, data.get("invite_id"))
            review_author = data.get("review_author")
            if actor not in invite["invitees"] + [invite["organizer"]]:
                raise HTTPException(403, "Only participants can upvote here")
            if review_author == actor:
                raise HTTPException(400, "Choose someone else's perspective")
            if review_author not in [r["author"] for r in invite["reviews"]]:
                raise HTTPException(400, "Review not found")
            voters = invite["votes"].setdefault(review_author, [])
            if actor in voters:
                voters.remove(actor)
            else:
                voters.append(actor)
            add_event(state, actor, "helpful_vote", f"Reacted to {review_author}'s perspective")
        else:
            raise HTTPException(400, "Unknown action")
        save_state(conn, code, state)
        return {"ok": True, **result, "state": exposed(state, actor, code)}
