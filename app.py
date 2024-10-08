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
import time
from functools import wraps

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
        "CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, hash TEXT, emitter TEXT, receiver TEXT, mined DATETIME, tokens_send NUMERIC, gas_fee NUMERIC, completed INTEGER(1) DEFAULT 0, FOREIGN KEY(receiver) REFERENCES wallet(address), FOREIGN KEY (emitter) REFERENCES wallet(address))"
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


# Method to limit de amount of requests to the API
def rate_limited(min_interval):
    def decorator(func):
        last_called = [0]
        last_result = [None]

        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed >= min_interval:
                last_result[0] = func(*args, **kwargs)
                last_called[0] = time.time()
            return last_result[0]

        return wrapper

    return decorator


@rate_limited(120)
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


def get_dollars_btc(tokens):
    btc_dollars = get_value_btc()
    dollars = tokens * btc_dollars
    formatted_dollars = "{:.2f}".format(dollars)

    return formatted_dollars


def get_gas_fee():
    btc_dollars = get_value_btc()
    gas_fee = 5 / btc_dollars

    return gas_fee


def update_chain():
    # Check mine date and update token amount
    conn = connect_database()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM transactions WHERE mined < ? AND completed = 0",
        (datetime.now(),),
    )
    transactions = c.fetchall()

    for transaction in transactions:
        # Set to completed
        c.execute(
            "UPDATE transactions SET completed = 1 WHERE id = ?", (transaction[0],)
        )

        # Remove tokens and gas fee from emitter
        c.execute(
            "UPDATE wallet SET token_amount = token_amount - ? - ? WHERE address = ?",
            (transaction[5], transaction[7], transaction[2]),
        )

        # Add tokens to receiver
        c.execute(
            "UPDATE wallet SET token_amount = token_amount + ? WHERE address = ?",
            (transaction[5], transaction[3]),
        )

    print("Updated transactions")
    conn.commit()
    conn.close()


# Format tokens into 6 decimal places
def format_tokens(tokens):
    return "{:.6f}".format(tokens)


@app.route("/")
def index():
    update_chain()
    return render_template("index.html")


@app.route("/create-wallet", methods=["GET", "POST"])
def create_wallet():
    if request.method == "GET":
        words = get_words()
        session["words"] = words
    else:
        words = session.get("words")

        address = create_address()
        encrypted_words = encrypt_words(words)

        conn = connect_database()
        c = conn.cursor()

        c.execute(
            "INSERT INTO wallet VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (address, 0.0, *encrypted_words),
        )
        conn.commit()
        conn.close()

        session["result"] = True
        session["message"] = (
            f"Your wallet address {address} was created successfully! Keep your seedphrase somewhere safe!"
        )

        return redirect(
            url_for(
                "chain",
            )
        )

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
            session["result"] = True
            session["message"] = (
                f"The tokes were added successfully to your wallet ({address})!"
            )

            return redirect(
                url_for(
                    "chain",
                )
            )
            # return f"<h1>Wallet address: {address} </h1>"
        else:
            session["error"] = True
            session["message"] = "Something went wrong reenter your seedphrase!"
            return redirect(url_for("add_tokens"))


@app.route("/make-transaction", methods=["GET", "POST"])
def make_transaction():
    if request.method == "GET":
        positions = get_position_words()
        gas_fee = 0.00005  #! TEST ONLY get_gas_fee()
        formatted_gas_fee = format_tokens(gas_fee)
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

            session["result"] = True
            session["message"] = (
                f"The transaction was created successfully! The transaction hash is {hash} and will be mined in 10 minutes! ({mined_time})"
            )

            return redirect(
                url_for(
                    "chain",
                )
            )

        else:
            session["error"] = True
            session["message"] = (
                "Something went wrong reenter your seedphrase or the receiver address and try again!"
            )
            return redirect(url_for("make_transaction"))


@app.route("/chain")
def chain():
    update_chain()
    conn = connect_database()
    c = conn.cursor()

    c.execute("SELECT * FROM transactions")
    transactions = c.fetchall()
    full_transactions = []
    for t in transactions:
        btc_amount = t[5]
        usd_amount = get_dollars_btc(btc_amount)
        gas_fee = t[6]
        formatted_gas_fee = format_tokens(gas_fee)
        full_transactions.append(t + (usd_amount, formatted_gas_fee))

    conn.close()

    result = session.pop("result", False)
    message = session.pop("message", "")

    return render_template(
        "transactionslist.html",
        transactions=full_transactions,
        result=result,
        message=message,
    )


@app.route("/transaction/<id>")
def transaction(id):
    update_chain()
    conn = connect_database()
    c = conn.cursor()

    c.execute("SELECT * FROM transactions WHERE id = ?", (id,))
    transaction = c.fetchall()

    if transaction == []:
        conn.close()
        return "Transaction not found"

    gas_fee = transaction[0][6]
    formatted_gas_fee = format_tokens(gas_fee)
    converted_gas_fee = get_dollars_btc(gas_fee)

    token_amount = transaction[0][5]
    converted_token_amount = get_dollars_btc(token_amount)

    conn.close()

    return render_template(
        "transaction.html",
        transaction=transaction[0],
        id=id,
        gas_fee=formatted_gas_fee,
        converted_gas_fee=converted_gas_fee,
        converted_token_amount=converted_token_amount,
    )


@app.route("/wallet/<address>")
def wallet(address):
    update_chain()
    conn = connect_database()
    c = conn.cursor()

    c.execute("SELECT token_amount FROM wallet WHERE address = ?", (address,))
    tokens = c.fetchall()

    c.execute(
        "SELECT * FROM transactions WHERE emitter = ? OR receiver = ?",
        (address, address),
    )

    transactions = c.fetchall()

    if tokens == []:
        conn.close()
        return "Wallet not found"

    formatted_tokens = format_tokens(tokens[0][0])

    value_tokens = get_dollars_btc(tokens[0][0])

    conn.close()

    return render_template(
        "wallet.html",
        tokens=formatted_tokens,
        address=address,
        transactions=transactions,
        dollars=value_tokens,
    )


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form["search"]
        conn = connect_database()
        c = conn.cursor()

        if query[0] == "b" and query[1] == "c":
            c.execute("SELECT * FROM wallet WHERE address = ?", (query,))
            wallet = c.fetchall()
            conn.close()
            if wallet:
                return redirect(url_for("wallet", address=query))
            else:
                session["result"] = True
                session["message"] = (
                    f"Wallet with address {query} not found! Try again!"
                )
                return redirect(url_for("chain"))
        elif query[0] == "0":
            c.execute("SELECT * FROM transactions WHERE hash = ?", (query,))
            transaction = c.fetchall()
            conn.close()
            if transaction:
                return redirect(url_for("transaction", id=transaction[0][0]))
            else:
                session["result"] = True
                session["message"] = (
                    f"Transaction with hash {query} not found! Try again!"
                )
                return redirect(url_for("chain"))
        else:
            session["result"] = True
            session["message"] = "Invalid search! Try again!"
            return redirect(url_for("chain"))


if __name__ == "__main__":
    create_database()
    get_words()
    app.run(debug=True)
