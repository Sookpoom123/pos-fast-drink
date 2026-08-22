from flask import Flask, jsonify, request, render_template
import psycopg2
import os
import json

app = Flask(__name__)

DB_URL = os.environ.get("DATABASE_URL")

def get_db():
    if not DB_URL:
        raise Exception("ไม่พบ DATABASE_URL")
    # เพิ่ม sslmode='require' เพื่อให้เชื่อมต่อกับ Cloud Database ได้
    return psycopg2.connect(DB_URL, sslmode='require')

@app.route("/api/init-data", methods=["GET"])
def get_init_data():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # ลองดึงแบบมีคอลัมน์หลายภาษา หากไม่มีใน DB ให้ Fallback ไปใช้ Query ปกติ
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
            conn.close()

@app.route("/api/order", methods=["POST"])
def create_order():
    conn = None
    try:
        data = request.get_json(silent=True) or {}
        table_number = str(data.get("table_number", "")).strip()
        cart = data.get("cart", [])
        total_price = float(data.get("total_price", 0))

        if not table_number:
            return jsonify({"success": False, "error": "กรุณากรอกชื่อ/คิว"}), 400
        if not cart:
            return jsonify({"success": False, "error": "ยังไม่มีรายการสินค้า"}), 400

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO orders (table_number, items_json, total_price, status) VALUES (%s, %s, %s, %s)",
            (table_number, json.dumps(cart, ensure_ascii=False), total_price, "pending")
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
            conn.close()

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
