from flask import Flask, jsonify, request, render_template
import psycopg2
from psycopg2 import pool
import os
import json
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

DB_URL = os.environ.get("DATABASE_URL")

# สร้าง Connection Pool เพื่อรองรับ Traffic และไม่ให้ Connection เต็ม
db_pool = None
if DB_URL:
    try:
        db_pool = pool.SimpleConnectionPool(1, 10, DB_URL, sslmode='require')
    except Exception as e:
        print("Pool Error:", e)

def get_db():
    if db_pool:
        return db_pool.getconn()
    if not DB_URL:
        raise Exception("ไม่พบ DATABASE_URL")
    return psycopg2.connect(DB_URL, sslmode='require')

def release_db(conn):
    if db_pool and conn:
        db_pool.putconn(conn)
    elif conn:
        conn.close()

# ตั้งค่า Timezone เป็นประเทศไทย (UTC+7)
THAILAND_TZ = timezone(timedelta(hours=7))

@app.route("/api/init-data", methods=["GET"])
def get_init_data():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT 
                    name, price, image_url,
                    COALESCE(name_my, name),
                    COALESCE(name_zh, name),
                    COALESCE(name_en, name)
                FROM menu_items ORDER BY name ASC
            """)
            menu_rows = cursor.fetchall()
            menu = [{
                "name": r[0], "price": float(r[1]), "image_url": r[2],
                "name_my": r[3], "name_zh": r[4], "name_en": r[5]
            } for r in menu_rows]
        except Exception:
            conn.rollback()
            cursor.execute("SELECT name, price, image_url FROM menu_items ORDER BY name ASC")
            menu_rows = cursor.fetchall()
            menu = [{
                "name": r[0], "price": float(r[1]), "image_url": r[2],
                "name_my": r[0], "name_zh": r[0], "name_en": r[0]
            } for r in menu_rows]

        try:
            cursor.execute("""
                SELECT 
                    name, price,
                    COALESCE(name_my, name),
                    COALESCE(name_zh, name),
                    COALESCE(name_en, name)
                FROM toppings ORDER BY price ASC
            """)
            topping_rows = cursor.fetchall()
            toppings = [{
                "name": r[0], "price": float(r[1]),
                "name_my": r[2], "name_zh": r[3], "name_en": r[4]
            } for r in topping_rows]
        except Exception:
            conn.rollback()
            cursor.execute("SELECT name, price FROM toppings ORDER BY price ASC")
            topping_rows = cursor.fetchall()
            toppings = [{
                "name": r[0], "price": float(r[1]),
                "name_my": r[0], "name_zh": r[0], "name_en": r[0]
            } for r in topping_rows]

        cursor.close()
        return jsonify({"success": True, "menu": menu, "toppings": toppings})

    except Exception as e:
        print("Database Error:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if conn:
            release_db(conn)

@app.route("/api/order", methods=["POST"])
def create_order():
    conn = None
    try:
        data = request.get_json(silent=True) or {}
        table_number = str(data.get("table_number", "")).strip()
        cart = data.get("cart", [])
        total_price = float(data.get("total_price", 0))
        order_date_str = data.get("order_date")

        if not table_number:
            return jsonify({"success": False, "error": "กรุณากรอกชื่อ/คิว"}), 400
        if not cart:
            return jsonify({"success": False, "error": "ยังไม่มีรายการสินค้า"}), 400

        # ใช้เวลาประเทศไทย (UTC+7)
        now_th = datetime.now(THAILAND_TZ)
        if order_date_str:
            try:
                selected_date = datetime.strptime(order_date_str, "%Y-%m-%d").date()
                created_at = datetime.combine(selected_date, now_th.time())
            except ValueError:
                created_at = now_th.replace(tzinfo=None)
        else:
            created_at = now_th.replace(tzinfo=None)

        conn = get_db()
        cursor = conn.cursor()
        
        total_cost = sum(float(item.get("cost", 0)) for item in cart)

        cursor.execute(
            """
            INSERT INTO orders (table_number, items_json, total_price, total_cost, status, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (table_number, json.dumps(cart, ensure_ascii=False), total_price, total_cost, "pending", created_at)
        )
        conn.commit()
        cursor.close()

        return jsonify({"success": True, "message": "ส่งออเดอร์เรียบร้อย"})

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if conn:
            release_db(conn)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
