from flask import Flask, jsonify, request, render_template
import psycopg2
import os
import json

app = Flask(_name_)

# =========================================================
# Database
# =========================================================

DB_URL = os.environ.get("DATABASE_URL")


def get_db():
    return psycopg2.connect(
        DB_URL,
        sslmode="require"
    )


# =========================================================
# โหลดข้อมูลเมนู + ท็อปปิ้ง
# =========================================================

@app.route("/api/init-data", methods=["GET"])
def get_init_data():

    conn = None

    try:

        conn = get_db()
        cursor = conn.cursor()

        # -----------------------------
        # เมนู
        # -----------------------------

        cursor.execute("""
            SELECT name, price, image_url
            FROM menu_items
            ORDER BY name ASC
        """)

        menu = [
            {
                "name": row[0],
                "price": float(row[1]),
                "image_url": row[2]
            }
            for row in cursor.fetchall()
        ]

        # -----------------------------
        # ท็อปปิ้ง
        # -----------------------------

        cursor.execute("""
            SELECT name, price
            FROM toppings
            ORDER BY price ASC
        """)

        toppings = [
            {
                "name": row[0],
                "price": float(row[1])
            }
            for row in cursor.fetchall()
        ]

        return jsonify({
            "menu": menu,
            "toppings": toppings
        })

    except Exception as e:

        print("Database Error:", e)

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        if conn:
            conn.close()


# =========================================================
# รับออเดอร์
# =========================================================

@app.route("/api/order", methods=["POST"])
def create_order():

    conn = None

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid request"
            }), 400

        table_number = data.get("table_number")
        cart = data.get("cart")
        total_price = data.get("total_price")

        if not table_number:
            return jsonify({
                "success": False,
                "error": "Missing customer name"
            }), 400

        if not cart:
            return jsonify({
                "success": False,
                "error": "Cart is empty"
            }), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO orders
            (
                table_number,
                items_json,
                total_price,
                status
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                table_number,
                json.dumps(
                    cart,
                    ensure_ascii=False
                ),
                total_price,
                "pending"
            )
        )

        conn.commit()

        return jsonify({
            "success": True
        })

    except Exception as e:

        print("Order Error:", e)

        if conn:
            conn.rollback()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    finally:

        if conn:
            conn.close()


# =========================================================
# หน้าเว็บ
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# Run
# =========================================================

if _name_ == "_main_":

    app.run(
        host="0.0.0.0",
        port=5000
    )
