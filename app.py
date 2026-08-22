from flask import Flask, jsonify, request, render_template
import psycopg2
import os
import json

app = Flask(__name__)

# ดึง URL จาก Environment Variable
DB_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DB_URL)

@app.route('/api/init-data', methods=['GET'])
def get_init_data():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name, price, image_url FROM menu_items ORDER BY name ASC")
        menu = [{"name": r[0], "price": float(r[1]), "image_url": r[2]} for r in cursor.fetchall()]
        
        cursor.execute("SELECT name, price FROM toppings ORDER BY price ASC")
        toppings = [{"name": r[0], "price": float(r[1])} for r in cursor.fetchall()]
        conn.close()
        return jsonify({"menu": menu, "toppings": toppings})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/order', methods=['POST'])
def create_order():
    try:
        data = request.json
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO orders (table_number, items_json, total_price, status) VALUES (%s, %s, %s, %s)",
            (data['table_number'], json.dumps(data['cart'], ensure_ascii=False), data['total_price'], 'pending')
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
