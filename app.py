from turtle import pos
from flask import Flask, request, render_template, redirect, url_for, session
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import sqlite3
import json
import random
import string
import hashlib
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


def create_database():
    conn = sqlite3.connect("blockchain.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS wallet (address TEXT PRIMARY KEY, token_amount NUMERIC, word1 TEXT, word2 TEXT, word3 TEXT, word4 TEXT, word5 TEXT, word6 TEXT, word7 TEXT, word8 TEXT, word9 TEXT, word10 TEXT, word11 TEXT, word12 TEXT)"""
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, hash TEXT, emitter TEXT, receiver TEXT, mined DATETIME, tokens_send NUMERIC, gas_fee NUMERIC, FOREIGN KEY(receiver) REFERENCES wallet(address), FOREIGN KEY (emitter) REFERENCES wallet(address))"
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


def create_transaction_hash():
    prefix = "0" * 20

    random_characters = "".join(
        random.choice(string.ascii_lowercase + string.digits) for _ in range(44)
    )

    hash = prefix + random_characters

    return hash


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


def does_wallet_exist(user_input, positions):
    conn = connect_database()
    c = conn.cursor()

    if positions != []:
        encrypted_input = encrypt_words(user_input)

        query = """
        SELECT address 
        FROM wallet 
        WHERE word{} = ? AND word{} = ? AND word{} = ? AND word{} = ? AND word{} = ?
        """.format(positions[0], positions[1], positions[2], positions[3], positions[4])

        c.execute(
            query,
            (
                encrypted_input[0],
                encrypted_input[1],
                encrypted_input[2],
                encrypted_input[3],
                encrypted_input[4],
            ),
        )

        query = c.fetchall()
        conn.close()

        if query:
            address = query[0][0]
            return True, address
        else:
            return False, ""
    else:
        c.execute("SELECT address FROM wallet WHERE address = ?", (user_input,))
        query = c.fetchall()

        if query:
            address = query[0][0]
            return True, address
        else:
            return False, ""


def add_tokens_address(tokens, address):
    conn = connect_database()
    c = conn.cursor()

    c.execute(
        "UPDATE wallet SET token_amount = token_amount + ? WHERE address = ?",
        (tokens, address),
    )

    conn.commit()

    c.execute("SELECT token_amount FROM wallet WHERE address = ?", (address,))
    print(f"New amount of tokens: {c.fetchall()[0][0]}")
    conn.close()


def get_value_btc():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    parameters = {"symbol": "BTC", "convert": "USD"}
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": os.getenv("COINMARKET_API_KEY"),
    }

    response = requests.get(url, headers=headers, params=parameters)
    data = response.json()

    btc_price = data["data"]["BTC"]["quote"]["USD"]["price"]
    print("precio", btc_price)
    return btc_price


def get_gas_fee():
    btc_dollars = get_value_btc()
    gas_fee = 5 / btc_dollars

    return gas_fee


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
    else:
        positions = session.get("positions")
        user_input = []
        for p in positions:
            user_input.append(request.form[f"word{p}"])

        wallet_exists, address = does_wallet_exist(user_input, positions)

        if wallet_exists:
            print(address)
            token_amount = request.form["token_amount"]
            add_tokens_address(token_amount, address)
            return "good"
            # return f"<h1>Wallet address: {address} </h1>"
        else:
            return "Your seedphrase is wrong!"


@app.route("/make-transaction", methods=["GET", "POST"])
def make_transaction():
    if request.method == "GET":
        positions = get_position_words()
        gas_fee = 0.00005  #! TEST ONLY get_gas_fee()
        formatted_gas_fee = "{:.6f}".format(gas_fee)
        session["gas"] = formatted_gas_fee
        session["positions"] = positions
        return render_template(
            "maketransaction.html", positions=positions, gas_fee=formatted_gas_fee
        )
    else:
        positions = session.get("positions")
        user_input = []
        for p in positions:
            user_input.append(request.form[f"word{p}"])

        wallet_exists, emitter = does_wallet_exist(user_input, positions)

        if wallet_exists:
            receiver = request.form["receiver"]
            receiver_exists = does_wallet_exist(receiver, [])
            if not receiver_exists:
                return "Receiver does not exist!"

            token_amount = float(request.form["token_amount"])
            print(token_amount)
            hash = create_transaction_hash()
            mined_time = datetime.now() + timedelta(minutes=10)
            gas_fee = float(session.get("gas"))

            conn = connect_database()
            c = conn.cursor()

            print(hash, str(emitter), receiver, mined_time, token_amount, gas_fee)

            c.execute(
                "INSERT INTO transactions (hash, emitter, receiver, mined, tokens_send, gas_fee) VALUES (?, ?, ?, ?, ?, ?)",
                (hash, str(emitter), receiver, mined_time, token_amount, gas_fee),
            )

            conn.commit()
            conn.close()
            return "good"

        else:
            return "Your seedphrase is wrong!"


@app.route("/chain")
def transactions():
    conn = connect_database()
    c = conn.cursor()

    c.execute("SELECT * FROM transactions")
    transactions = c.fetchall()

    conn.close()

    return render_template("transactionslist.html", transactions=transactions)


@app.route("/transaction/<id>")
def transaction(id):
    conn = connect_database()
    c = conn.cursor()

    c.execute("SELECT * FROM transactions WHERE id = ?", (id,))
    transaction = c.fetchall()

    if transaction == []:
        conn.close()
        return "Transaction not found"

    gas_fee = transaction[0][6]
    formatted_gas_fee = "{:.6f}".format(gas_fee)

    conn.close()

    return render_template(
        "transaction.html", transaction=transaction[0], id=id, gas_fee=formatted_gas_fee
    )


if __name__ == "__main__":
    create_database()
    get_words()
    app.run(debug=True)
