# app.py - メインのFlaskアプリケーション
from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS
import sqlite3
import json
import csv
from datetime import datetime, timedelta
import os
from functools import wraps
import io

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://admin-attendance.netlify.app",
            "https://employee-attendance1.netlify.app"
        ]
    }
})


# 設定
DATABASE_PATH = 'database/attendance.db'
ADMIN_PASSWORD = 'admin123'  # 実際の運用では環境変数で管理

# データベース初期化
def init_db():
    """データベースとテーブルを初期化"""
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 出退勤ログテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            client_name TEXT NOT NULL,
            log_type TEXT NOT NULL,  -- 'clock_in' or 'clock_out'
            timestamp DATETIME NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 従業員マスタテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 取引先マスタテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("データベースを初期化しました")

# 管理者認証デコレータ
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {ADMIN_PASSWORD}':
            return jsonify({'error': '管理者権限が必要です'}), 401
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# 使用者用API
# =============================================================================

@app.route('/')
def user_page():
    """使用者用ページ"""
    try:
        with open('frontend/user/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>ファイルが見つかりません</title></head>
        <body>
            <h1>エラー</h1>
            <p>frontend/user/index.html が見つかりません。</p>
            <p>ファイル構成を確認してください。</p>
        </body>
        </html>
        """, 404

@app.route('/api/employees', methods=['GET'])
def get_employees():
    """従業員一覧を取得"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM employees ORDER BY name')
    employees = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(employees)

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """取引先一覧を取得"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM clients ORDER BY name')
    clients = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(clients)

@app.route('/api/clock-in', methods=['POST'])
def clock_in():
    """出勤記録"""
    data = request.json
    employee_name = data.get('employee_name')
    client_name = data.get('client_name')
    
    if not employee_name or not client_name:
        return jsonify({'error': '従業員名と取引先名は必須です'}), 400
    
    now = datetime.now()
    timestamp = now.isoformat()
    date = now.strftime('%Y年%m月%d日')
    time = now.strftime('%H:%M')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attendance_logs (employee_name, client_name, log_type, timestamp, date, time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (employee_name, client_name, 'clock_in', timestamp, date, time))
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'おはようございます。',
        'timestamp': timestamp,
        'employee': employee_name,
        'client': client_name
    })

@app.route('/api/clock-out', methods=['POST'])
def clock_out():
    """退勤記録"""
    data = request.json
    employee_name = data.get('employee_name')
    client_name = data.get('client_name')
    
    if not employee_name or not client_name:
        return jsonify({'error': '従業員名と取引先名は必須です'}), 400
    
    now = datetime.now()
    timestamp = now.isoformat()
    date = now.strftime('%Y年%m月%d日')
    time = now.strftime('%H:%M')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attendance_logs (employee_name, client_name, log_type, timestamp, date, time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (employee_name, client_name, 'clock_out', timestamp, date, time))
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'お疲れさまでした。',
        'timestamp': timestamp,
        'employee': employee_name,
        'client': client_name
    })

# =============================================================================
# 管理者用API
# =============================================================================

@app.route('/admin/')
def admin_page():
    """管理者用ページ（パスワード保護）"""
    return '''
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>管理者ログイン</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f5f5f5; }
            .login-container { max-width: 400px; margin: 100px auto; padding: 40px; 
                             background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 4px; }
            button { width: 100%; padding: 12px; background: #333; color: white; border: none; 
                    border-radius: 4px; font-size: 16px; cursor: pointer; }
            button:hover { background: #555; }
            .error { color: red; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h2>管理者ログイン</h2>
            <form id="loginForm">
                <div class="form-group">
                    <label for="password">パスワード:</label>
                    <input type="password" id="password" required>
                </div>
                <button type="submit">ログイン</button>
                <div id="error" class="error"></div>
            </form>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', function(e) {
                e.preventDefault();
                const password = document.getElementById('password').value;
                
                fetch('/admin/verify', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({password: password})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        localStorage.setItem('adminToken', password);
                        window.location.href = '/admin/dashboard';
                    } else {
                        document.getElementById('error').textContent = 'パスワードが間違っています';
                    }
                });
            });
        </script>
    </body>
    </html>
    '''

@app.route('/admin/verify', methods=['POST'])
def verify_admin():
    """管理者パスワード確認"""
    data = request.json
    password = data.get('password')
    
    if password == ADMIN_PASSWORD:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False}), 401

@app.route('/admin/dashboard')
def admin_dashboard():
    """管理者ダッシュボード"""
    try:
        with open('frontend/admin/dashboard.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>ファイルが見つかりません</title></head>
        <body>
            <h1>エラー</h1>
            <p>frontend/admin/dashboard.html が見つかりません。</p>
            <p>ファイル構成を確認してください。</p>
        </body>
        </html>
        """, 404

@app.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_logs():
    """ログ一覧を取得（管理者専用）"""
    # フィルタパラメータ
    employee = request.args.get('employee')
    client = request.args.get('client')
    log_type = request.args.get('type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 基本クエリ
    query = '''
        SELECT id, employee_name, client_name, log_type, timestamp, date, time
        FROM attendance_logs
        WHERE 1=1
    '''
    params = []
    
    # フィルタ条件を追加
    if employee:
        query += ' AND employee_name = ?'
        params.append(employee)
    
    if client:
        query += ' AND client_name = ?'
        params.append(client)
    
    if log_type:
        query += ' AND log_type = ?'
        params.append(log_type)
    
    if date_from:
        query += ' AND DATE(timestamp) >= ?'
        params.append(date_from)
    
    if date_to:
        query += ' AND DATE(timestamp) <= ?'
        params.append(date_to)
    
    query += ' ORDER BY timestamp DESC'
    
    cursor.execute(query, params)
    logs = []
    for row in cursor.fetchall():
        logs.append({
            'id': row[0],
            'employee': row[1],
            'client': row[2],
            'type': row[3],
            'timestamp': row[4],
            'date': row[5],
            'time': row[6]
        })
    
    conn.close()
    return jsonify(logs)

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_stats():
    """統計情報を取得（管理者専用）"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 総ログ数
    cursor.execute('SELECT COUNT(*) FROM attendance_logs')
    total_logs = cursor.fetchone()[0]
    
    # 今日のログ数
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM attendance_logs WHERE DATE(timestamp) = ?', (today,))
    today_logs = cursor.fetchone()[0]
    
    # 出勤・退勤回数
    cursor.execute('SELECT COUNT(*) FROM attendance_logs WHERE log_type = "clock_in"')
    clock_in_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM attendance_logs WHERE log_type = "clock_out"')
    clock_out_count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_logs': total_logs,
        'today_logs': today_logs,
        'clock_in_count': clock_in_count,
        'clock_out_count': clock_out_count
    })

@app.route('/api/admin/export/csv', methods=['GET'])
@admin_required
def export_csv():
    """CSV エクスポート（管理者専用）"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, employee_name, client_name, log_type, timestamp, date, time
        FROM attendance_logs
        ORDER BY timestamp DESC
    ''')
    
    # CSV生成
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '従業員名', '取引先', '種別', 'タイムスタンプ', '日付', '時刻'])
    
    for row in cursor.fetchall():
        log_type_jp = '出勤' if row[3] == 'clock_in' else '退勤'
        writer.writerow([row[0], row[1], row[2], log_type_jp, row[4], row[5], row[6]])
    
    conn.close()
    
    output.seek(0)
    filename = f'attendance_logs_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/admin/export/json', methods=['GET'])
@admin_required
def export_json():
    """JSON エクスポート（管理者専用）"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, employee_name, client_name, log_type, timestamp, date, time
        FROM attendance_logs
        ORDER BY timestamp DESC
    ''')
    
    logs = []
    for row in cursor.fetchall():
        logs.append({
            'id': row[0],
            'employee_name': row[1],
            'client_name': row[2],
            'log_type': row[3],
            'timestamp': row[4],
            'date': row[5],
            'time': row[6]
        })
    
    conn.close()
    
    export_data = {
        'export_date': datetime.now().isoformat(),
        'total_records': len(logs),
        'data': logs
    }
    
    filename = f'attendance_logs_{datetime.now().strftime("%Y%m%d")}.json'
    
    return send_file(
        io.BytesIO(json.dumps(export_data, ensure_ascii=False, indent=2).encode('utf-8')),
        mimetype='application/json',
        as_attachment=True,
        download_name=filename
    )

# =============================================================================
# 初期データ投入
# =============================================================================

def insert_sample_data():
    """サンプルデータを投入"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 従業員マスタ
    employees = ['田中太郎', '佐藤花子', '鈴木一郎', '山田美咲']
    for emp in employees:
        cursor.execute('INSERT OR IGNORE INTO employees (name) VALUES (?)', (emp,))
    
    # 取引先マスタ
    clients = ['A商事', 'B株式会社', 'C工業', 'D企画', '本社']
    for client in clients:
        cursor.execute('INSERT OR IGNORE INTO clients (name) VALUES (?)', (client,))
    
    conn.commit()
    conn.close()
    print("サンプルデータを投入しました")

# =============================================================================
# アプリケーション起動
# =============================================================================

if __name__ == '__main__':
    init_db()
    insert_sample_data()
    print("=" * 60)
    print("🚀 出退勤管理システムを起動しました")
    print("=" * 60)
    print("📍 使用者用ページ:  http://localhost:5000/")
    print("📍 管理者用ページ:  http://localhost:5000/admin/")
    print("🔐 管理者パスワード: admin123")
    print("=" * 60)

    port = int(os.environ.get('PORT', 5000))  # ← ここが変更ポイント！
    app.run(debug=True, host='0.0.0.0', port=port)

