# setup_database.py
import sqlite3

def setup_database():
    conn = sqlite3.connect("sample.db")
    c = conn.cursor()

    # Drop tables if they exist (for a clean start).
    c.execute("DROP TABLE IF EXISTS users")
    c.execute("DROP TABLE IF EXISTS orders")
    c.execute("DROP TABLE IF EXISTS products")

    # Create tables.
    c.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER,
        email TEXT
    )
    ''')

    c.execute('''
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        total_price REAL,
        order_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    c.execute('''
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT,
        price REAL,
        stock INTEGER
    )
    ''')

    # Insert sample data.
    users = [
        (1, 'Alice', 30, 'alice@example.com'),
        (2, 'Bob', 25, 'bob@example.com'),
        (3, 'Charlie', 35, 'charlie@example.com')
    ]
    c.executemany("INSERT INTO users VALUES (?,?,?,?)", users)

    orders = [
        (1, 1, 100.0, '2025-01-15'),
        (2, 2, 150.0, '2025-01-20'),
        (3, 1, 200.0, '2025-02-10'),
        (4, 3, 50.0, '2025-02-05')
    ]
    c.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)

    products = [
        (1, 'Widget', 10.0, 100),
        (2, 'Gadget', 15.0, 150),
        (3, 'Thingamajig', 20.0, 200)
    ]
    c.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

    # Create indexes for faster query performance.
    c.execute("CREATE INDEX idx_order_date ON orders(order_date)")
    c.execute("CREATE INDEX idx_user_id ON orders(user_id)")

    conn.commit()
    conn.close()
    print("Database setup complete: sample.db created with tables and indexes.")

if __name__ == "__main__":
    setup_database()
