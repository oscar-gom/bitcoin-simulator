from flask import Flask, request, render_template, redirect, url_for, session
from dotenv import load_dotenv
import os
import sqlite3
import json
import random
import string
import hashlib

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


def create_database():
    conn = sqlite3.connect("blockchain.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS wallet (address TEXT, token_amount NUMERIC, word1 TEXT, word2 TEXT, word3 TEXT, word4 TEXT, word5 TEXT, word6 TEXT, word7 TEXT, word8 TEXT, word9 TEXT, word10 TEXT, word11 TEXT, word12 TEXT)"""
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS transactions (hash TEXT, emitter TEXT, receiver TEXT, created DATETIME, mined DATETIME, tokens_send NUMERIC, gas_fee NUMERIC, FOREIGN KEY(receiver) REFERENCES wallet(address), FOREIGN KEY (emitter) REFERENCES wallet(address))"
    )
    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_address_wallet ON wallet (address)"
    )
    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_hash ON transactions(hash)"
    )
    conn.commit()
    conn.close()


def connect_database():
    conn = sqlite3.connect("blockchain.db")
    # conn.row_factory = sqlite3.Row
    return conn


def get_words():
    with open("bip39words.json", "r") as file:
        data = json.load(file)

    wallet_words = random.sample(data, 12)

    return wallet_words


def create_address():
    length = 42
    prefix = "bc"
    total_length = length - len(prefix)

    allowed_characters = string.ascii_lowercase + string.digits

    random_part = "".join(
        random.choice(allowed_characters) for _ in range(total_length)
    )

    address = prefix + random_part

    return address


def encrypt_words(words):
    hashed_words = []

    for word in words:
        current_hash = word.encode("utf-8")

        for _ in range(int(os.getenv("TIMES_ENCRYPTED"))):
            hash_obj = hashlib.sha256()
            hash_obj.update(current_hash)
            current_hash = hash_obj.digest()

        hashed_words.append(current_hash.hex())

    return hashed_words


def get_position_words():
    positions = random.sample(range(1, 13), 5)
    positions.sort()
    return positions


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create-wallet", methods=["GET", "POST"])
def create_wallet():
    if request.method == "GET":
        words = get_words()
        session["words"] = words
    else:
        words = session.get("words")
        if words is None:
            return "<h1>Error: No words found in session.</h1>", 400

        address = create_address()

        crypted_words = encrypt_words(words)

        conn = connect_database()
        c = conn.cursor()

        c.execute(
            "INSERT INTO wallet VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (address, 0.0, *crypted_words),
        )
        conn.commit()
        conn.close()

        return f"<h1>Wallet address: {address} Created successfully!</h1>"

    return render_template("createwallet.html", words=words)


@app.route("/add-tokens", methods=["GET", "POST"])
def add_tokens():
    if request.method == "GET":
        positions = get_position_words()
        session["positions"] = positions
        return render_template("addtokens.html", positions=positions)


if __name__ == "__main__":
    create_database()
    get_words()
    app.run(debug=True)
