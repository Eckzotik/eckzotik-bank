from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import random
from datetime import datetime

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "bank.db")

SUPPORT_TG = "@tegECKZOTIK_org"
SUPPORT_PHONE = "+380 (68) 623 70 84"
MAX_CARDS_PER_USER = 5

RATES = {
    "UAH": 1.0,
    "USD": 40.0,
    "EUR": 43.0,
    "PLN": 10.0
}

CARD_SKINS = {
    "obsidian": {
        "name": "Obsidian",
        "css": "linear-gradient(135deg,#0f172a,#111827,#1f2937)",
        "text": "#ffffff",
        "button": "#1f2937"
    },
    "aurora": {
        "name": "Aurora",
        "css": "linear-gradient(135deg,#0f766e,#14b8a6,#2dd4bf)",
        "text": "#ffffff",
        "button": "#0f4f4a"
    },
    "sunset": {
        "name": "Sunset",
        "css": "linear-gradient(135deg,#7c2d12,#ea580c,#fb7185)",
        "text": "#ffffff",
        "button": "#6b2d16"
    },
    "violet": {
        "name": "Violet",
        "css": "linear-gradient(135deg,#4c1d95,#7c3aed,#a78bfa)",
        "text": "#ffffff",
        "button": "#4c1d95"
    },
    "ocean": {
        "name": "Ocean",
        "css": "linear-gradient(135deg,#1d4ed8,#06b6d4,#67e8f9)",
        "text": "#ffffff",
        "button": "#1e3a8a"
    },
    "emerald": {
        "name": "Emerald",
        "css": "linear-gradient(135deg,#14532d,#16a34a,#4ade80)",
        "text": "#ffffff",
        "button": "#14532d"
    }
}

PRESET_AVATARS = [
    "😀", "😎", "👾", "🐱", "🦊", "🐼", "🐸", "🦁", "🐻", "⚡", "🔥", "🌙"
]


def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def table_columns(cursor, table_name: str):
    rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] for row in rows]


def add_column_if_missing(cursor, table_name: str, column_name: str, definition: str):
    cols = table_columns(cursor, table_name)
    if column_name not in cols:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def gen_card_number():
    while True:
        value = " ".join(str(random.randint(1000, 9999)) for _ in range(4))
        conn = get_conn()
        c = conn.cursor()
        row = c.execute("SELECT id FROM cards WHERE card_number=?", (value,)).fetchone()
        conn.close()
        if not row:
            return value


def gen_expiry():
    month = random.randint(1, 12)
    year = random.randint(27, 31)
    return f"{month:02d}/{year}"


def gen_cvv():
    return f"{random.randint(100, 999)}"


def gen_ref_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        code = "ECK" + "".join(random.choice(alphabet) for _ in range(7))
        conn = get_conn()
        c = conn.cursor()
        row = c.execute("SELECT username FROM users WHERE referral_code=?", (code,)).fetchone()
        conn.close()
        if not row:
            return code


def uah_to_currency(amount_uah: float, currency: str) -> float:
    if currency not in RATES:
        currency = "UAH"
    return round(amount_uah / RATES[currency], 2)


def convert_between(amount: float, from_currency: str, to_currency: str) -> float:
    if from_currency not in RATES or to_currency not in RATES:
        return round(amount, 2)
    amount_uah = amount * RATES[from_currency]
    return round(amount_uah / RATES[to_currency], 2)


def default_limits(card_type: str):
    if card_type == "child":
        return {
            "daily_limit": 2000.0,
            "per_transfer_limit": 500.0
        }
    return {
        "daily_limit": 50000.0,
        "per_transfer_limit": 20000.0
    }


def add_history(username: str, title: str, subtitle: str, amount: float, tx_type: str, card_id=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO history(username, title, subtitle, amount, tx_type, created_at, card_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (username, title, subtitle, amount, tx_type, now_str(), card_id))
    conn.commit()
    conn.close()


def get_today_spent(card_id: int) -> float:
    conn = get_conn()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    row = c.execute("""
        SELECT IFNULL(SUM(ABS(amount)), 0) AS total
        FROM history
        WHERE card_id=? AND tx_type='expense' AND substr(created_at,1,10)=?
    """, (card_id, today)).fetchone()
    conn.close()
    return float(row["total"] or 0)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )
    """)

    add_column_if_missing(c, "users", "display_name", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing(c, "users", "phone", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing(c, "users", "theme", "TEXT NOT NULL DEFAULT 'blue'")
    add_column_if_missing(c, "users", "language", "TEXT NOT NULL DEFAULT 'ru'")
    add_column_if_missing(c, "users", "avatar_color", "TEXT NOT NULL DEFAULT '#4f46e5'")
    add_column_if_missing(c, "users", "avatar_mode", "TEXT NOT NULL DEFAULT 'preset'")
    add_column_if_missing(c, "users", "avatar_value", "TEXT NOT NULL DEFAULT '😎'")
    add_column_if_missing(c, "users", "referral_code", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing(c, "users", "referred_by", "TEXT NOT NULL DEFAULT ''")

    c.execute("""
    CREATE TABLE IF NOT EXISTS cards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        card_number TEXT NOT NULL UNIQUE,
        card_name TEXT NOT NULL DEFAULT 'Main card',
        expiry TEXT NOT NULL,
        cvv TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 0,
        currency TEXT NOT NULL DEFAULT 'UAH',
        skin TEXT NOT NULL DEFAULT 'ocean',
        card_type TEXT NOT NULL DEFAULT 'adult',
        daily_limit REAL NOT NULL DEFAULT 50000,
        per_transfer_limit REAL NOT NULL DEFAULT 20000,
        is_main INTEGER NOT NULL DEFAULT 0
    )
    """)

    add_column_if_missing(c, "cards", "currency", "TEXT NOT NULL DEFAULT 'UAH'")
    add_column_if_missing(c, "cards", "skin", "TEXT NOT NULL DEFAULT 'ocean'")
    add_column_if_missing(c, "cards", "card_type", "TEXT NOT NULL DEFAULT 'adult'")
    add_column_if_missing(c, "cards", "daily_limit", "REAL NOT NULL DEFAULT 50000")
    add_column_if_missing(c, "cards", "per_transfer_limit", "REAL NOT NULL DEFAULT 20000")
    add_column_if_missing(c, "cards", "is_blocked", "INTEGER NOT NULL DEFAULT 0")

    c.execute("""
    CREATE TABLE IF NOT EXISTS contacts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_username TEXT NOT NULL,
        contact_name TEXT NOT NULL,
        contact_username TEXT NOT NULL DEFAULT '',
        contact_card TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        title TEXT NOT NULL,
        subtitle TEXT NOT NULL DEFAULT '',
        amount REAL NOT NULL,
        tx_type TEXT NOT NULL DEFAULT 'neutral',
        created_at TEXT NOT NULL
    )
    """)

    add_column_if_missing(c, "history", "card_id", "INTEGER")

    c.execute("UPDATE users SET display_name=username WHERE display_name='' OR display_name IS NULL")
    c.execute("UPDATE users SET avatar_mode='preset' WHERE avatar_mode='' OR avatar_mode IS NULL")
    c.execute("UPDATE users SET avatar_value='😎' WHERE avatar_value='' OR avatar_value IS NULL")

    users = c.execute("SELECT username, referral_code FROM users").fetchall()
    for user in users:
        if not user["referral_code"]:
            c.execute("UPDATE users SET referral_code=? WHERE username=?", (gen_ref_code(), user["username"]))

        cards_count = c.execute("SELECT COUNT(*) AS c FROM cards WHERE username=?", (user["username"],)).fetchone()["c"]
        if cards_count == 0:
            limits = default_limits("adult")
            c.execute("""
                INSERT INTO cards(
                    username, card_number, card_name, expiry, cvv, balance,
                    currency, skin, card_type, daily_limit, per_transfer_limit, is_main, is_blocked
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
            """, (
                user["username"],
                gen_card_number(),
                "Main card",
                gen_expiry(),
                gen_cvv(),
                10000.0,
                "UAH",
                "ocean",
                "adult",
                limits["daily_limit"],
                limits["per_transfer_limit"]
            ))

    conn.commit()
    conn.close()


init_db()


def get_profile(username: str):
    conn = get_conn()
    c = conn.cursor()

    user = c.execute("""
        SELECT username, display_name, phone, theme, language, avatar_color,
               avatar_mode, avatar_value, referral_code, referred_by
        FROM users
        WHERE username=?
    """, (username,)).fetchone()

    if not user:
        conn.close()
        return None

    cards = c.execute("""
        SELECT id, card_number, card_name, expiry, cvv, balance, currency, skin,
               card_type, daily_limit, per_transfer_limit, is_main, is_blocked
        FROM cards
        WHERE username=?
        ORDER BY is_main DESC, id ASC
    """, (username,)).fetchall()

    contacts = c.execute("""
        SELECT id, contact_name, contact_username, contact_card, created_at
        FROM contacts
        WHERE owner_username=?
        ORDER BY id DESC
    """, (username,)).fetchall()

    history = c.execute("""
        SELECT id, title, subtitle, amount, tx_type, created_at, card_id
        FROM history
        WHERE username=?
        ORDER BY id DESC
        LIMIT 50
    """, (username,)).fetchall()

    conn.close()

    return {
        "user": dict(user),
        "cards": [dict(x) for x in cards],
        "contacts": [dict(x) for x in contacts],
        "history": [dict(x) for x in history],
        "skins": CARD_SKINS,
        "rates": RATES,
        "support": {
            "telegram": SUPPORT_TG,
            "phone": SUPPORT_PHONE
        },
        "preset_avatars": PRESET_AVATARS,
        "max_cards": MAX_CARDS_PER_USER
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    display_name = data.get("display_name", "").strip() or username
    phone = data.get("phone", "").strip()
    referral_input = data.get("referral_code", "").strip().upper()

    if not username or not password or not phone:
        return jsonify({"ok": False, "error": "Заполни логин, пароль и номер"})

    conn = get_conn()
    c = conn.cursor()

    exists = c.execute("SELECT username FROM users WHERE username=?", (username,)).fetchone()
    if exists:
        conn.close()
        return jsonify({"ok": False, "error": "Такой username уже занят"})

    my_ref = gen_ref_code()
    referred_by = ""
    bonus_uah = 0.0

    if referral_input:
        ref_user = c.execute("SELECT username FROM users WHERE referral_code=?", (referral_input,)).fetchone()
        if ref_user:
            referred_by = ref_user["username"]
            bonus_uah = 100.0

    c.execute("""
        INSERT INTO users(
            username, password, display_name, phone, theme, language,
            avatar_color, avatar_mode, avatar_value, referral_code, referred_by
        )
        VALUES (?, ?, ?, ?, 'blue', 'ru', '#4f46e5', 'preset', '😎', ?, ?)
    """, (username, password, display_name, phone, my_ref, referred_by))

    limits = default_limits("adult")

    c.execute("""
        INSERT INTO cards(
            username, card_number, card_name, expiry, cvv, balance,
            currency, skin, card_type, daily_limit, per_transfer_limit,
            is_main, is_blocked
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
    """, (
        username,
        gen_card_number(),
        "Main card",
        gen_expiry(),
        gen_cvv(),
        10000.0 + bonus_uah,
        "UAH",
        "ocean",
        "adult",
        limits["daily_limit"],
        limits["per_transfer_limit"]
    ))

    conn.commit()
    conn.close()

    add_history(username, "Стартовый баланс", "Регистрация", 10000.0, "income")

    if bonus_uah > 0 and referred_by:
        conn = get_conn()
        c = conn.cursor()
        main_ref = c.execute("""
            SELECT id FROM cards WHERE username=? AND is_main=1
        """, (referred_by,)).fetchone()
        if main_ref:
            c.execute("UPDATE cards SET balance = balance + 100 WHERE id=?", (main_ref["id"],))
            conn.commit()
        conn.close()

        add_history(username, "Реферальный бонус", referred_by, 100.0, "income")
        add_history(referred_by, "Награда за реферала", username, 100.0, "income")

    return jsonify({"ok": True, "profile": get_profile(username)})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = get_conn()
    c = conn.cursor()
    user = c.execute("""
        SELECT username FROM users WHERE username=? AND password=?
    """, (username, password)).fetchone()
    conn.close()

    if not user:
        return jsonify({"ok": False, "error": "Неверный логин или пароль"})

    return jsonify({"ok": True, "profile": get_profile(username)})


@app.route("/api/profile/<username>")
def profile(username):
    profile = get_profile(username)
    if not profile:
        return jsonify({"ok": False, "error": "Пользователь не найден"})
    return jsonify({"ok": True, "profile": profile})


@app.route("/api/profile/update", methods=["POST"])
def update_profile():
    data = request.get_json()
    username = data.get("username", "").strip()
    display_name = data.get("display_name", "").strip()
    avatar_color = data.get("avatar_color", "").strip() or "#4f46e5"
    avatar_mode = data.get("avatar_mode", "preset").strip()
    avatar_value = data.get("avatar_value", "😎").strip()

    if not username or not display_name:
        return jsonify({"ok": False, "error": "Некорректные данные"})

    if avatar_mode not in ["preset", "upload"]:
        avatar_mode = "preset"

    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE users
        SET display_name=?, avatar_color=?, avatar_mode=?, avatar_value=?
        WHERE username=?
    """, (display_name, avatar_color, avatar_mode, avatar_value, username))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/settings/update", methods=["POST"])
def settings_update():
    data = request.get_json()
    username = data.get("username", "").strip()
    theme = data.get("theme", "blue").strip()
    language = data.get("language", "ru").strip()

    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE users SET theme=?, language=?
        WHERE username=?
    """, (theme, language, username))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/cards/create", methods=["POST"])
def create_card():
    data = request.get_json()
    username = data.get("username", "").strip()
    card_name = data.get("card_name", "").strip() or "New card"
    currency = data.get("currency", "UAH").strip().upper()
    skin = data.get("skin", "ocean").strip()
    card_type = data.get("card_type", "adult").strip()

    if currency not in RATES:
        currency = "UAH"
    if skin not in CARD_SKINS:
        skin = "ocean"
    if card_type not in ["adult", "child"]:
        card_type = "adult"

    conn = get_conn()
    c = conn.cursor()

    count_cards = c.execute("SELECT COUNT(*) AS c FROM cards WHERE username=?", (username,)).fetchone()["c"]
    if count_cards >= MAX_CARDS_PER_USER:
        conn.close()
        return jsonify({"ok": False, "error": f"Лимит карт: {MAX_CARDS_PER_USER}"})

    limits = default_limits(card_type)
    start_balance = uah_to_currency(1000.0, currency)

    c.execute("""
        INSERT INTO cards(
            username, card_number, card_name, expiry, cvv, balance,
            currency, skin, card_type, daily_limit, per_transfer_limit,
            is_main, is_blocked
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
    """, (
        username,
        gen_card_number(),
        card_name,
        gen_expiry(),
        gen_cvv(),
        start_balance,
        currency,
        skin,
        card_type,
        limits["daily_limit"],
        limits["per_transfer_limit"]
    ))
    conn.commit()
    conn.close()

    add_history(username, "Открытие карты", f"{card_name} · {currency}", start_balance, "income")
    return jsonify({"ok": True})


@app.route("/api/cards/set_main", methods=["POST"])
def set_main():
    data = request.get_json()
    username = data.get("username", "").strip()
    card_id = int(data.get("card_id"))

    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE cards SET is_main=0 WHERE username=?", (username,))
    c.execute("UPDATE cards SET is_main=1 WHERE id=? AND username=?", (card_id, username))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/cards/toggle_block", methods=["POST"])
def toggle_block():
    data = request.get_json()
    username = data.get("username", "").strip()
    card_id = int(data.get("card_id"))

    conn = get_conn()
    c = conn.cursor()
    card = c.execute("""
        SELECT is_blocked FROM cards WHERE id=? AND username=?
    """, (card_id, username)).fetchone()

    if not card:
        conn.close()
        return jsonify({"ok": False, "error": "Карта не найдена"})

    new_state = 0 if card["is_blocked"] else 1
    c.execute("UPDATE cards SET is_blocked=? WHERE id=?", (new_state, card_id))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "is_blocked": new_state})


@app.route("/api/cards/convert", methods=["POST"])
def convert_card_currency():
    data = request.get_json()
    username = data.get("username", "").strip()
    card_id = int(data.get("card_id"))
    to_currency = data.get("to_currency", "UAH").strip().upper()

    if to_currency not in RATES:
        return jsonify({"ok": False, "error": "Неизвестная валюта"})

    conn = get_conn()
    c = conn.cursor()
    card = c.execute("""
        SELECT id, username, balance, currency, card_name, is_blocked
        FROM cards
        WHERE id=? AND username=?
    """, (card_id, username)).fetchone()

    if not card:
        conn.close()
        return jsonify({"ok": False, "error": "Карта не найдена"})

    if card["is_blocked"]:
        conn.close()
        return jsonify({"ok": False, "error": "Карта заблокирована"})

    new_amount = convert_between(card["balance"], card["currency"], to_currency)

    c.execute("""
        UPDATE cards SET balance=?, currency=?
        WHERE id=?
    """, (new_amount, to_currency, card_id))
    conn.commit()
    conn.close()

    add_history(username, "Конвертация валюты", f"{card['currency']} → {to_currency}", 0, "neutral")
    return jsonify({"ok": True})


@app.route("/api/contacts/add", methods=["POST"])
def contacts_add():
    data = request.get_json()
    username = data.get("username", "").strip()
    contact_name = data.get("contact_name", "").strip()
    contact_username = data.get("contact_username", "").strip()
    contact_card = data.get("contact_card", "").strip()

    if not username or not contact_name:
        return jsonify({"ok": False, "error": "Нужно имя контакта"})

    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO contacts(owner_username, contact_name, contact_username, contact_card, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (username, contact_name, contact_username, contact_card, now_str()))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/contacts/delete", methods=["POST"])
def contacts_delete():
    data = request.get_json()
    username = data.get("username", "").strip()
    contact_id = int(data.get("contact_id"))

    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        DELETE FROM contacts WHERE id=? AND owner_username=?
    """, (contact_id, username))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/transfer/card_to_card", methods=["POST"])
def transfer_card_to_card():
    data = request.get_json()

    username = data.get("username", "").strip()
    from_card_id = int(data.get("from_card_id"))
    target_card_number = data.get("target_card_number", "").strip()
    amount_raw = data.get("amount", 0)

    try:
        amount = float(amount_raw)
    except Exception:
        return jsonify({"ok": False, "error": "Некорректная сумма"})

    if amount <= 0:
        return jsonify({"ok": False, "error": "Сумма должна быть больше 0"})

    conn = get_conn()
    c = conn.cursor()

    sender_card = c.execute("""
        SELECT * FROM cards WHERE id=? AND username=?
    """, (from_card_id, username)).fetchone()

    receiver_card = c.execute("""
        SELECT * FROM cards WHERE card_number=?
    """, (target_card_number,)).fetchone()

    if not sender_card:
        conn.close()
        return jsonify({"ok": False, "error": "Карта отправителя не найдена"})

    if not receiver_card:
        conn.close()
        return jsonify({"ok": False, "error": "Карта получателя не найдена"})

    if sender_card["is_blocked"]:
        conn.close()
        return jsonify({"ok": False, "error": "Карта отправителя заблокирована"})

    if receiver_card["is_blocked"]:
        conn.close()
        return jsonify({"ok": False, "error": "Карта получателя заблокирована"})

    if sender_card["id"] == receiver_card["id"]:
        conn.close()
        return jsonify({"ok": False, "error": "Нельзя перевести на эту же карту"})

    if amount > sender_card["per_transfer_limit"]:
        conn.close()
        return jsonify({"ok": False, "error": f"Лимит на перевод: {sender_card['per_transfer_limit']} {sender_card['currency']}"})

    today_spent = get_today_spent(sender_card["id"])
    if today_spent + amount > sender_card["daily_limit"]:
        conn.close()
        return jsonify({"ok": False, "error": f"Превышен дневной лимит: {sender_card['daily_limit']} {sender_card['currency']}"})

    if sender_card["balance"] < amount:
        conn.close()
        return jsonify({"ok": False, "error": "Недостаточно средств"})

    converted_for_receiver = convert_between(amount, sender_card["currency"], receiver_card["currency"])

    c.execute("UPDATE cards SET balance = balance - ? WHERE id=?", (amount, sender_card["id"]))
    c.execute("UPDATE cards SET balance = balance + ? WHERE id=?", (converted_for_receiver, receiver_card["id"]))
    conn.commit()
    conn.close()

    add_history(username, "Перевод на карту", receiver_card["card_number"], -amount, "expense", sender_card["id"])
    add_history(receiver_card["username"], "Получение перевода", sender_card["card_number"], converted_for_receiver, "income", receiver_card["id"])

    return jsonify({"ok": True})


@app.route("/api/pay/fine", methods=["POST"])
def pay_fine():
    data = request.get_json()

    username = data.get("username", "").strip()
    card_id = int(data.get("card_id"))
    amount_raw = data.get("amount", 0)
    reason = data.get("reason", "").strip() or "Погашение штрафа"

    try:
        amount = float(amount_raw)
    except Exception:
        return jsonify({"ok": False, "error": "Некорректная сумма"})

    if amount <= 0:
        return jsonify({"ok": False, "error": "Сумма должна быть больше 0"})

    conn = get_conn()
    c = conn.cursor()
    card = c.execute("""
        SELECT * FROM cards WHERE id=? AND username=?
    """, (card_id, username)).fetchone()

    if not card:
        conn.close()
        return jsonify({"ok": False, "error": "Карта не найдена"})

    if card["is_blocked"]:
        conn.close()
        return jsonify({"ok": False, "error": "Карта заблокирована"})

    if amount > card["per_transfer_limit"]:
        conn.close()
        return jsonify({"ok": False, "error": "Превышен лимит карты"})

    today_spent = get_today_spent(card["id"])
    if today_spent + amount > card["daily_limit"]:
        conn.close()
        return jsonify({"ok": False, "error": "Превышен дневной лимит"})

    if card["balance"] < amount:
        conn.close()
        return jsonify({"ok": False, "error": "Недостаточно средств"})

    c.execute("UPDATE cards SET balance = balance - ? WHERE id=?", (amount, card["id"]))
    conn.commit()
    conn.close()

    add_history(username, "Погашение штрафа", reason, -amount, "expense", card["id"])
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)