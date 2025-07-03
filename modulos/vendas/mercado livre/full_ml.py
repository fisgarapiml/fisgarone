import os
import sqlite3
from datetime import datetime, timedelta
import requests
import json
import time
from flask import render_template, jsonify
from dotenv import load_dotenv
from flask import Blueprint

load_dotenv()
full_ml_bp = Blueprint('full_ml_bp', __name__, url_prefix='/full_ml')

class FullMercadoLivre:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '../../grupo_fisgar.db')
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Cria tabelas necessárias se não existirem"""
        tables = [
            """CREATE TABLE IF NOT EXISTS ml_vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE,
                date_created TEXT,
                status TEXT,
                total_amount REAL,
                shipping_cost REAL,
                items TEXT,
                seller_id INTEGER,
                account_name TEXT,
                processed BOOLEAN DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS ml_produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE,
                title TEXT,
                price REAL,
                available_quantity INTEGER,
                sold_quantity INTEGER,
                listing_type TEXT,
                condition TEXT,
                status TEXT,
                health REAL,
                seller_id INTEGER,
                account_name TEXT,
                last_updated TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS ml_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                seller_id INTEGER,
                account_name TEXT,
                total_orders INTEGER,
                total_sales REAL,
                avg_order_value REAL,
                conversion_rate REAL,
                visits INTEGER,
                unique_visitors INTEGER
            )""",
            """CREATE TABLE IF NOT EXISTS ml_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT,
                access_token TEXT,
                refresh_token TEXT,
                expires_in INTEGER,
                last_updated TEXT
            )"""
        ]

        for table in tables:
            self.cursor.execute(table)
        self.conn.commit()

    def refresh_access_token(self, account_name):
        """Atualiza o token de acesso automaticamente"""
        client_id = os.getenv(f'CLIENT_ID_{account_name.upper()}')
        client_secret = os.getenv(f'CLIENT_SECRET_{account_name.upper()}')
        refresh_token = os.getenv(f'REFRESH_TOKEN_{account_name.upper()}')

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError(f"Credenciais não encontradas para a conta {account_name}")

        url = "https://api.mercadolibre.com/oauth/token"
        payload = {
            'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token
        }

        response = requests.post(url, data=payload)
        if response.status_code == 200:
            data = response.json()

            # Atualiza o .env
            self.update_env_file(
                account_name,
                data['access_token'],
                data.get('refresh_token', refresh_token)
            )

            # Salva no banco de dados
            self.cursor.execute(
                """INSERT OR REPLACE INTO ml_tokens 
                (account_name, access_token, refresh_token, expires_in, last_updated)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    account_name,
                    data['access_token'],
                    data.get('refresh_token', refresh_token),
                    data['expires_in'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            self.conn.commit()

            return data['access_token']
        else:
            raise Exception(f"Erro ao atualizar token: {response.text}")

    def update_env_file(self, account_name, access_token, refresh_token):
        """Atualiza o arquivo .env com novos tokens"""
        env_path = os.path.join(os.path.dirname(__file__), '../../.env')

        # Lê o conteúdo atual
        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Atualiza os tokens
        updated_lines = []
        access_updated = False
        refresh_updated = False

        for line in lines:
            if line.startswith(f'ACCESS_TOKEN_{account_name.upper()}='):
                updated_lines.append(f'ACCESS_TOKEN_{account_name.upper()}={access_token}\n')
                access_updated = True
            elif line.startswith(f'REFRESH_TOKEN_{account_name.upper()}='):
                updated_lines.append(f'REFRESH_TOKEN_{account_name.upper()}={refresh_token}\n')
                refresh_updated = True
            else:
                updated_lines.append(line)

        # Se não existir, adiciona
        if not access_updated:
            updated_lines.append(f'ACCESS_TOKEN_{account_name.upper()}={access_token}\n')
        if not refresh_updated:
            updated_lines.append(f'REFRESH_TOKEN_{account_name.upper()}={refresh_token}\n')

        # Escreve de volta
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)

        # Atualiza variáveis de ambiente
        os.environ[f'ACCESS_TOKEN_{account_name.upper()}'] = access_token
        os.environ[f'REFRESH_TOKEN_{account_name.upper()}'] = refresh_token

    def get_access_token(self, account_name):
        """Obtém o token de acesso válido"""
        # Verifica no banco de dados primeiro
        self.cursor.execute(
            "SELECT access_token, last_updated FROM ml_tokens WHERE account_name = ? ORDER BY last_updated DESC LIMIT 1",
            (account_name,)
        )
        token_data = self.cursor.fetchone()

        if token_data:
            access_token, last_updated = token_data
            last_updated = datetime.strptime(last_updated, '%Y-%m-%d %H:%M:%S')

            # Verifica se o token ainda é válido (expira em 6 horas)
            if (datetime.now() - last_updated) < timedelta(hours=5):
                return access_token

        # Se não tiver ou estiver expirado, atualiza
        return self.refresh_access_token(account_name)

    def get_sales_data(self, account_name, days=30):
        """Obtém dados de vendas dos últimos X dias"""
        access_token = self.get_access_token(account_name)
        seller_id = os.getenv(f'SELLER_ID_{account_name.upper()}')

        if not seller_id:
            raise ValueError(f"Seller ID não encontrado para a conta {account_name}")

        url = f"https://api.mercadolibre.com/orders/search?seller={seller_id}"
        headers = {'Authorization': f'Bearer {access_token}'}

        # Calcula datas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        params = {
            'order.date_created.from': start_date.strftime('%Y-%m-%dT%H:%M:%S.000-00:00'),
            'order.date_created.to': end_date.strftime('%Y-%m-%dT%H:%M:%S.000-00:00'),
            'limit': 50
        }

        all_orders = []
        while True:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise Exception(f"Erro ao obter vendas: {response.text}")

            data = response.json()
            orders = data.get('results', [])
            all_orders.extend(orders)

            # Verifica se há mais páginas
            if 'next' in data and data['next']:
                url = data['next']
                params = {}
            else:
                break

        # Processa e salva as ordens
        for order in all_orders:
            try:
                self.cursor.execute(
                    """INSERT OR IGNORE INTO ml_vendas 
                    (order_id, date_created, status, total_amount, shipping_cost, items, seller_id, account_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        order['id'],
                        order['date_created'],
                        order['status'],
                        float(order['total_amount']),
                        float(order['shipping_cost']),
                        json.dumps(order['order_items']),
                        seller_id,
                        account_name
                    )
                )
            except Exception as e:
                print(f"Erro ao salvar ordem {order['id']}: {str(e)}")

        self.conn.commit()
        return all_orders

    def get_product_data(self, account_name):
        """Obtém dados de todos os produtos/anúncios"""
        access_token = self.get_access_token(account_name)
        seller_id = os.getenv(f'SELLER_ID_{account_name.upper()}')

        if not seller_id:
            raise ValueError(f"Seller ID não encontrado para a conta {account_name}")

        url = f"https://api.mercadolibre.com/users/{seller_id}/items/search"
        headers = {'Authorization': f'Bearer {access_token}'}

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Erro ao obter produtos: {response.text}")

        product_ids = response.json().get('results', [])

        all_products = []
        for product_id in product_ids:
            product_url = f"https://api.mercadolibre.com/items/{product_id}"
            product_response = requests.get(product_url, headers=headers)

            if product_response.status_code == 200:
                product_data = product_response.json()

                # Obtém métricas de saúde do anúncio
                health_url = f"https://api.mercadolibre.com/items/{product_id}/health"
                health_response = requests.get(health_url, headers=headers)
                health_data = health_response.json() if health_response.status_code == 200 else {}

                # Prepara dados para inserção
                product = {
                    'product_id': product_data.get('id'),
                    'title': product_data.get('title'),
                    'price': float(product_data.get('price', 0)),
                    'available_quantity': product_data.get('available_quantity', 0),
                    'sold_quantity': product_data.get('sold_quantity', 0),
                    'listing_type': product_data.get('listing_type_id'),
                    'condition': product_data.get('condition'),
                    'status': product_data.get('status'),
                    'health': health_data.get('health', {}).get('percentage', 0),
                    'seller_id': seller_id,
                    'account_name': account_name,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                all_products.append(product)

                # Insere ou atualiza no banco de dados
                self.cursor.execute(
                    """INSERT OR REPLACE INTO ml_produtos 
                    (product_id, title, price, available_quantity, sold_quantity, 
                     listing_type, condition, status, health, seller_id, account_name, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    tuple(product.values())
                )

                # Pequena pausa para evitar rate limit
                time.sleep(0.1)

        self.conn.commit()
        return all_products

    def calculate_metrics(self, account_name):
        """Calcula métricas de desempenho"""
        seller_id = os.getenv(f'SELLER_ID_{account_name.upper()}')

        # Obtém vendas dos últimos 30 dias
        self.cursor.execute(
            """SELECT COUNT(*) as total_orders, SUM(total_amount) as total_sales, 
            AVG(total_amount) as avg_order_value 
            FROM ml_vendas 
            WHERE seller_id = ? AND account_name = ? 
            AND date_created >= date('now', '-30 days')""",
            (seller_id, account_name)
        )
        sales_data = self.cursor.fetchone()

        # Obtém dados de visitas (simplificado - na prática precisa da API de métricas)
        visits = 0
        unique_visitors = 0

        # Calcula taxa de conversão
        conversion_rate = 0
        if visits > 0 and sales_data[0] > 0:
            conversion_rate = (sales_data[0] / visits) * 100

        # Insere métricas
        metrics = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'seller_id': seller_id,
            'account_name': account_name,
            'total_orders': sales_data[0] if sales_data[0] else 0,
            'total_sales': sales_data[1] if sales_data[1] else 0,
            'avg_order_value': sales_data[2] if sales_data[2] else 0,
            'conversion_rate': conversion_rate,
            'visits': visits,
            'unique_visitors': unique_visitors
        }

        self.cursor.execute(
            """INSERT INTO ml_metrics 
            (date, seller_id, account_name, total_orders, total_sales, 
             avg_order_value, conversion_rate, visits, unique_visitors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            tuple(metrics.values())
        )
        self.conn.commit()

        return metrics

    def get_inventory_analysis(self, account_name):
        """Analisa o estoque e sugere reposição"""
        seller_id = os.getenv(f'SELLER_ID_{account_name.upper()}')

        # Produtos com estoque baixo
        self.cursor.execute(
            """SELECT product_id, title, available_quantity, sold_quantity 
            FROM ml_produtos 
            WHERE seller_id = ? AND account_name = ? AND available_quantity < 5
            ORDER BY sold_quantity DESC""",
            (seller_id, account_name)
        )
        low_stock = self.cursor.fetchall()

        # Produtos parados no estoque
        self.cursor.execute(
            """SELECT product_id, title, available_quantity, sold_quantity, 
            julianday('now') - julianday(last_updated) as days_in_stock
            FROM ml_produtos 
            WHERE seller_id = ? AND account_name = ? 
            AND available_quantity > 0 AND sold_quantity = 0
            ORDER BY days_in_stock DESC""",
            (seller_id, account_name)
        )
        stagnant_stock = self.cursor.fetchall()

        return {
            'low_stock': low_stock,
            'stagnant_stock': stagnant_stock
        }

    def get_dashboard_data(self, account_name):
        """Obtém todos os dados para o painel"""
        try:
            # Atualiza dados
            self.get_sales_data(account_name)
            self.get_product_data(account_name)
            metrics = self.calculate_metrics(account_name)
            inventory = self.get_inventory_analysis(account_name)

            # Obtém dados para gráficos
            self.cursor.execute(
                """SELECT date, total_sales FROM ml_metrics 
                WHERE account_name = ? 
                ORDER BY date DESC LIMIT 30""",
                (account_name,)
            )
            sales_chart = self.cursor.fetchall()

            self.cursor.execute(
                """SELECT strftime('%Y-%m-%d', date_created) as day, 
                COUNT(*) as orders, SUM(total_amount) as sales
                FROM ml_vendas 
                WHERE account_name = ? AND date_created >= date('now', '-30 days')
                GROUP BY day ORDER BY day""",
                (account_name,)
            )
            daily_sales = self.cursor.fetchall()

            self.cursor.execute(
                """SELECT title, sold_quantity 
                FROM ml_produtos 
                WHERE account_name = ? 
                ORDER BY sold_quantity DESC LIMIT 10""",
                (account_name,)
            )
            top_products = self.cursor.fetchall()

            self.cursor.execute(
                """SELECT status, COUNT(*) as count 
                FROM ml_produtos 
                WHERE account_name = ? 
                GROUP BY status""",
                (account_name,)
            )
            products_status = self.cursor.fetchall()

            return {
                'metrics': metrics,
                'inventory': inventory,
                'charts': {
                    'sales_chart': sales_chart,
                    'daily_sales': daily_sales,
                    'top_products': top_products,
                    'products_status': products_status
                }
            }
        except Exception as e:
            print(f"Erro ao obter dados do painel: {str(e)}")
            return None

    def render_dashboard(self, account_name):
        """Renderiza o template do painel com os dados"""
        dashboard_data = self.get_dashboard_data(account_name)
        return render_template('vendas/full_ml.html', data=dashboard_data, account_name=account_name.capitalize())


# Função para uso com Flask/Blueprints
# No FINAL do arquivo (após a classe FullMercadoLivre)
def init_full_ml_routes(bp):
    full_ml = FullMercadoLivre()

    @bp.route('/full_ml/<account_name>')  # Modificado aqui
    def full_ml_dashboard(account_name):
        return full_ml.render_dashboard(account_name)

    @bp.route('/api/full_ml/<account_name>/refresh')  # Modificado aqui
    def refresh_ml_data(account_name):
        try:
            full_ml.get_sales_data(account_name)
            full_ml.get_product_data(account_name)
            full_ml.calculate_metrics(account_name)
            return jsonify({'status': 'success', 'message': 'Dados atualizados com sucesso'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @bp.route('/api/mercado_livre/<account_name>/data')
    def get_ml_data(account_name):
        data = full_ml.get_dashboard_data(account_name)
        return jsonify(data) if data else jsonify({'error': 'Failed to get data'}), 500