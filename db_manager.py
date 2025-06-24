import sqlite3

DB_PATH = "accounts.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE
    )
    """)
    conn.commit()
    conn.close()

def account_exists(url):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_accounts WHERE url = ?", (url,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def add_account(url):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO processed_accounts (url) VALUES (?)", (url,))
        conn.commit()
    except sqlite3.IntegrityError:
        # La cuenta ya estaba insertada
        pass
    finally:
        conn.close()
