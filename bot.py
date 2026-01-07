import time
import requests
import telebot
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WB_API_KEY = os.getenv('WB_API_KEY')
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

if not WB_API_KEY or not TG_BOT_TOKEN or not TG_CHAT_ID:
    print("Please set WB_API_KEY, TG_BOT_TOKEN, and TG_CHAT_ID in .env file")
    exit()

bot = telebot.TeleBot(TG_BOT_TOKEN)

# File to store processed order IDs to avoid duplicates
ORDERS_FILE = 'orders.json'

def load_processed_orders():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            return set()
    return set()

def save_processed_orders(processed_orders):
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(processed_orders), f)

def get_wb_orders():
    # Using Statistics API
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/orders"
    
    # Check from 1 day ago to ensure we catch recent orders
    # Even if we run this every 5 minutes, we ask for 1 day to be safe against downtime
    date_from = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
    
    params = {
        'dateFrom': date_from,
        'flag': 0
    }
    
    headers = {
        'Authorization': WB_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 401:
            print("Error: Unauthorized. Check your WB_API_KEY.")
            return []
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching WB orders: {e}")
        return []

def format_message(order):
    title = order.get('subject', 'Неизвестный товар') 
    article = order.get('supplierArticle', 'Нет артикула')
    price = order.get('totalPrice', 0)
    nm_id = order.get('nmId', 'N/A')
    date = order.get('date', '').replace('T', ' ')
    
    # Convert cents/coins if needed, but WB usually returns float or int rubles/currency
    
    return (
        f"📦 <b>Новый заказ!</b>\n\n"
        f"📎 <b>Артикул:</b> {article}\n"
        f"🏷 <b>Название:</b> {title}\n"
        f"🆔 <b>nmId:</b> {nm_id}\n"
        f"💰 <b>Цена со скидкой:</b> {price} руб.\n"
        f"📅 <b>Дата:</b> {date}"
    )

def main():
    print("Bot started monitoring...")
    processed_orders = load_processed_orders()
    
    # If the list is empty (first run), we might want to prevent spamming all cached orders from the last day.
    # However, user might want to see them.
    # To prevent spam on absolute first start, we can just load them as processed without sending.
    # Uncomment lines below to skip notification on first run:
    # if not processed_orders:
    #     print("First run: marking existing orders as processed to avoid spam.")
    #     initial_orders = get_wb_orders()
    #     for order in initial_orders:
    #         order_id = order.get('srid')
    #         if order_id: processed_orders.add(order_id)
    #     save_processed_orders(processed_orders)

    while True:
        try:
            orders = get_wb_orders()
            new_orders_found = False
            
            # Helper to sort orders by date maybe? WB API usually returns sorted but good to be sure if sequence matters
            # But simple iteration is fine for notification purposes
            
            for order in orders:
                # srid is the unique identifier for orders in Statistics API
                order_id = order.get('srid') 
                
                if not order_id:
                    continue
                
                if order_id not in processed_orders:
                    try:
                        msg = format_message(order)
                        bot.send_message(TG_CHAT_ID, msg, parse_mode='HTML')
                        print(f"Sent notification for order {order_id}")
                        processed_orders.add(order_id)
                        new_orders_found = True
                        time.sleep(1) # Respect TG rate limits
                    except Exception as e:
                        print(f"Failed to send message: {e}")
            
            if new_orders_found:
                save_processed_orders(processed_orders)
            
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            
        print("Waiting 5 minutes...")
        time.sleep(300)

if __name__ == "__main__":
    main()
