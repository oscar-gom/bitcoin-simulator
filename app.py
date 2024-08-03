from flask import Flask, request, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)


def create_database():
    conn = sqlite3.connect("blockchain.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS wallet (address TEXT, token_amount NUMERIC, word1 TEXT, word2 TEXT, word3 TEXT, word4 TEXT, word5 TEXT, word6 TEXT, word7 TEXT, word8 TEXT, word9 TEXT, word10 TEXT, word11 TEXT, word12 TEXT)"""
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS transactions (hash TEXT, emitter TEXT, receiver TEXT, created DATETIME, mined DATETIME, gas_fee NUMERIC, FOREIGN KEY(receiver) REFERENCES wallet(address), FOREIGN KEY (emitter) REFERENCES wallet(address))"
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
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    create_database()
    app.run(debug=True)
