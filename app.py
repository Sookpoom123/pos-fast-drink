from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        cursor_factory=RealDictCursor
    )
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # ดึงข้อมูลเมนูเครื่องดื่มทั้งหมด
        cur.execute("SELECT * FROM drinks;")
        drinks = cur.fetchall()
        
        # ดึงข้อมูลท็อปปิ้งทั้งหมด
        cur.execute("SELECT * FROM toppings;")
        toppings = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # แปลงข้อมูลให้แน่ใจว่าฟิลด์รูปภาพพร้อมใช้งาน
        for d in drinks:
            if 'image_url' in d and not d.get('image'):
                d['image'] = d['image_url']
                
        return jsonify({
            'drinks': drinks,
            'toppings': toppings
        })
    except Exception as e:
        print("Database error:", e)
        # ถ้าเชื่อมต่อ DB ไม่ได้จริงๆ ให้ส่ง 500 error เพื่อให้หน้าเว็บรู้
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
        print("Order error:", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
