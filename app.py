from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM drinks;")
        drinks = cur.fetchall()
        
        cur.execute("SELECT * FROM toppings;")
        toppings = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'drinks': drinks,
            'toppings': toppings
        })
    except Exception as e:
        print("Database Error:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/order', methods=['POST'])
def create_order():
    try:
        data = request.json
        table_no = data.get('table', 'กลับบ้าน')
        order_date = data.get('date')
        items = data.get('items', [])
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        for item in items:
            drink_name = item.get('drink_name')
            price = item.get('price', 0)
            topping_name = item.get('topping_name', '')
            topping_price = item.get('topping_price', 0)
            total = item.get('total', 0)
            
            cur.execute("""
                INSERT INTO orders (table_no, drink_name, price, topping_name, topping_price, total, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (table_no, drink_name, price, topping_name, topping_price, total, order_date))
            
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print("Order Error:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
