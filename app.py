from flask import Flask, request, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)


def create_database():
    conn = sqlite3.connect("todo.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, task TEXT)"""
    )
    conn.commit()
    conn.close()
