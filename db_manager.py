import os
from dotenv import load_dotenv

import psycopg2
import psycopg2.pool

load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('USER_NAME'),
    'password': os.getenv('PASSWORD'),
    'host': os.getenv('HOST'),
    'port': os.getenv('PORT')
}

class BaseDBManager:
    def get_connection(self):
        raise NotImplementedError

    def close_connection(self, conn):
        raise NotImplementedError

    def create_user(self, username, email):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, email) VALUES (%s, %s) RETURNING id", (username, email))
            conn.commit()
            return cur.fetchone()[0]
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            self.close_connection(conn)

    def read_user(self, user_id):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()
        finally:
            self.close_connection(conn)

    def update_user(self, user_id, new_email):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET email = %s WHERE id = %s", (new_email, user_id))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            self.close_connection(conn)
    
    def delete_user(self, user_id):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            self.close_connection(conn)
    
class NoPoolManager(BaseDBManager):
    """Manages database connections without pooling."""
    def get_connection(self):
        return psycopg2.connect(**DB_CONFIG)

    def close_connection(self, conn):
        conn.close()

class PoolManager(BaseDBManager):
    """Manages database connections with a connection pool."""
    def __init__(self):
        self.pool = psycopg2.pool.SimpleConnectionPool(1, 50, **DB_CONFIG)

    def get_connection(self):
        return self.pool.getconn()

    def close_connection(self, conn):
        self.pool.putconn(conn)
    
    def close_pool(self):
        self.pool.closeall()