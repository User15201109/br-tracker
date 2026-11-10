from flask import Flask, render_template, request, redirect, url_for, Response
import json
import os
import csv
import io
from datetime import datetime

app = Flask(__name__)
DATA_DIR = 'db'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(data, filename):
    with open(os.path.join(DATA_DIR, filename), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    config = load_json('config.json')
    theme = config.get('theme', 'dark')

    virts = load_json('virts.json')
    history = load_json('sales.json').get('history', [])
    expenses = load_json('expenses.json').get('history', [])
    
    total_virts = sum(item.get('virts', 0) for item in virts.values() if isinstance(item, dict))
    total_money = sum(s.get('sum', 0) for s in history)
    total_exp = sum(e.get('sum', 0) for e in expenses)
    net_profit = total_money - total_exp

    return render_template('index.html', 
        theme=theme,
        virts=virts, history=history[::-1], 
        total_virts=total_virts, total_money=total_money, total_exp=total_exp, net_profit=net_profit,
        sell_accounts=load_json('sell_accounts.json').get('accounts', []),
        accounts_base=load_json('accounts_base.json').get('accounts', []),
        assortment=load_json('assortment.json').get('categories', {}),
        expenses=expenses[::-1], 
        blacklist=load_json('blacklist.json').get('users', []),
        notes=load_json('notes.json').get('list', [])
    )

@app.route('/change_theme', methods=['POST'])
def change_theme():
    config = load_json('config.json')
    config['theme'] = request.form.get('theme')
    save_json(config, 'config.json')
    return redirect(url_for('index'))

# ================= СКЛАД =================
@app.route('/update_virts', methods=['POST'])
def update_virts():
    server = request.form.get('server', '').strip().upper()
    amount = float(request.form.get('amount', 0))
    action = request.form.get('action')
    data = load_json('virts.json')
    if server not in data: data[server] = {'virts': 0, 'date': '—'}
    if action == 'add': data[server]['virts'] += amount
    elif action == 'remove': data[server]['virts'] -= amount
    elif action == 'set': data[server]['virts'] = amount
    data[server]['date'] = datetime.now().strftime('%d.%m %H:%M')
    save_json(data, 'virts.json')
    return redirect(url_for('index'))

@app.route('/sell_virts', methods=['POST'])
def sell_virts():
    server = request.form.get('server')
    amount = float(request.form.get('amount', 0))
    price = float(request.form.get('price', 0))
    data = load_json('virts.json')
    if server in data:
        data[server]['virts'] -= amount
        data[server]['date'] = datetime.now().strftime('%d.%m %H:%M')
        save_json(data, 'virts.json')
    sales = load_json('sales.json')
    if 'history' not in sales: sales['history'] = []
    sales['history'].append({'date': datetime.now().strftime('%Y-%m-%d %H:%M'), 'server': server, 'amount': amount, 'price': price, 'sum': amount * price})
    save_json(sales, 'sales.json')
    return redirect(url_for('index'))

@app.route('/delete_virts/<server>')
def delete_virts(server):
    data = load_json('virts.json')
    if server in data: del data[server]
    save_json(data, 'virts.json')
    return redirect(url_for('index'))

# ================= АККИ =================
@app.route('/add_sell_acc', methods=['POST'])
def add_sell_acc():
    acc = {'server': request.form.get('server').upper(), 'nick': request.form.get('nick'), 'lvl': request.form.get('lvl'), 'info': request.form.get('info'), 'price': float(request.form.get('price', 0)), 'status': 'в наличии', 'date': datetime.now().strftime('%Y-%m-%d')}
    data = load_json('sell_accounts.json')
    if 'accounts' not in data: data['accounts'] = []
    data['accounts'].append(acc)
    save_json(data, 'sell_accounts.json')
    return redirect(url_for('index'))

@app.route('/change_acc_status/<int:idx>', methods=['POST'])
def change_acc_status(idx):
    data = load_json('sell_accounts.json')
    if 'accounts' in data and 0 <= idx < len(data['accounts']):
        data['accounts'][idx]['status'] = request.form.get('status')
        save_json(data, 'sell_accounts.json')
    return redirect(url_for('index'))

@app.route('/delete_sell_acc/<int:idx>')
def delete_sell_acc(idx):
    data = load_json('sell_accounts.json')
    if 'accounts' in data and 0 <= idx < len(data['accounts']): data['accounts'].pop(idx)
    save_json(data, 'sell_accounts.json')
    return redirect(url_for('index'))

# ================= ПАРОЛИ =================
@app.route('/add_base_acc', methods=['POST'])
def add_base_acc():
    acc = {'server': request.form.get('server').upper(), 'nick': request.form.get('nick'), 'pwd': request.form.get('pwd')}
    data = load_json('accounts_base.json')
    if 'accounts' not in data: data['accounts'] = []
    data['accounts'].append(acc)
    save_json(data, 'accounts_base.json')
    return redirect(url_for('index'))

@app.route('/delete_base_acc/<int:idx>')
def delete_base_acc(idx):
    data = load_json('accounts_base.json')
    if 'accounts' in data and 0 <= idx < len(data['accounts']): data['accounts'].pop(idx)
    save_json(data, 'accounts_base.json')
    return redirect(url_for('index'))

# ================= АССОРТИМЕНТ =================
@app.route('/add_category', methods=['POST'])
def add_category():
    cat = request.form.get('category').strip()
    data = load_json('assortment.json')
    if 'categories' not in data: data['categories'] = {}
    if cat and cat not in data['categories']:
        data['categories'][cat] = []
        save_json(data, 'assortment.json')
    return redirect(url_for('index'))

@app.route('/add_item', methods=['POST'])
def add_item():
    cat = request.form.get('category')
    item = {'name': request.form.get('name'), 'qty': float(request.form.get('qty', 0)), 'price': float(request.form.get('price', 0))}
    data = load_json('assortment.json')
    if cat in data.get('categories', {}):
        data['categories'][cat].append(item)
        save_json(data, 'assortment.json')
    return redirect(url_for('index'))

@app.route('/delete_item/<cat>/<int:idx>')
def delete_item(cat, idx):
    data = load_json('assortment.json')
    if cat in data.get('categories', {}) and 0 <= idx < len(data['categories'][cat]):
        data['categories'][cat].pop(idx)
        save_json(data, 'assortment.json')
    return redirect(url_for('index'))

# ================= ОСТАЛЬНОЕ =================
@app.route('/add_expense', methods=['POST'])
def add_expense():
    expenses = load_json('expenses.json')
    if 'history' not in expenses: expenses['history'] = []
    expenses['history'].append({'date': datetime.now().strftime('%Y-%m-%d %H:%M'), 'desc': request.form.get('desc'), 'sum': float(request.form.get('amount', 0))})
    save_json(expenses, 'expenses.json')
    return redirect(url_for('index'))

@app.route('/add_note', methods=['POST'])
def add_note():
    data = load_json('notes.json')
    if 'list' not in data: data['list'] = []
    data['list'].append({'text': request.form.get('text'), 'date': datetime.now().strftime('%Y-%m-%d %H:%M')})
    save_json(data, 'notes.json')
    return redirect(url_for('index'))

@app.route('/delete_note/<int:idx>')
def delete_note(idx):
    data = load_json('notes.json')
    if 'list' in data and 0 <= idx < len(data['list']): data['list'].pop(idx)
    save_json(data, 'notes.json')
    return redirect(url_for('index'))

@app.route('/add_blacklist', methods=['POST'])
def add_blacklist():
    data = load_json('blacklist.json')
    if 'users' not in data: data['users'] = []
    data['users'].append({'nick': request.form.get('nick'), 'reason': request.form.get('reason'), 'date': datetime.now().strftime('%Y-%m-%d')})
    save_json(data, 'blacklist.json')
    return redirect(url_for('index'))

@app.route('/export')
def export():
    data = load_json('virts.json')
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Сервер', 'Вирты (кк)', 'Обновлено'])
    for server, info in data.items(): writer.writerow([server, info.get('virts', 0), info.get('date', '—')])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=br_virts.csv"})

if __name__ == '__main__':
    app.run(debug=True)