import os
import requests
import feedparser
import pytz
from datetime import datetime
from deep_translator import GoogleTranslator
from apscheduler.schedulers.background import BackgroundScheduler
import time

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = -1002064314678
USER_ID = 6678054169

RSS_FEEDS = {
    "ForkLog": "https://forklog.com/feed/",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed"
}

KEYWORDS = ["bitcoin", "ethereum", "sec", "etf", "launch", "upgrade", "crypto", "blockchain", "notcoin", "solana"]

def translate_to_russian(text):
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except:
        return text

def get_news(limit=6):
    news_items = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                link = entry.link
                if any(k in title.lower() for k in KEYWORDS):
                    translated_title = title if source == "ForkLog" else translate_to_russian(title)
                    news_items.append({'title': translated_title, 'url': link})
        except Exception as e:
            print(f"Ошибка чтения {source}: {e}")
    return news_items[:limit]

def split_news(news, split_index=3):
    return news[:split_index], news[split_index*1:split_index*2]

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print(f"✅ Отправлено в {chat_id}")
    else:
        print(f"❌ Ошибка при отправке в {chat_id}: {response.text}")

def send_morning_digest():
    news = get_news(limit=6)
    digest_news, _ = split_news(news)
    current_date = datetime.now(pytz.timezone('Europe/Kiev')).strftime("%d.%m.%Y")
    message = [
        f"🌅 <b>Утренний криптодайджест ({current_date})</b>",
        "▬▬▬▬▬▬▬▬▬▬▬▬",
        "<b>📌 Главные новости:</b>",
        *[f"• <b><a href='{item['url']}'>{item['title']}</a></b>" for item in digest_news],
        "▬▬▬▬▬▬▬▬▬▬▬▬",
        "👨‍💼 Администрация: @nordist_admin",
        "<a href='https://bingx.com/partner/KIMTRADING/'>📈 Получить бонусы и пониженную комиссию на BingX</a>"
    ]
    send_message(CHANNEL_ID, "
".join(message))

def send_news_both():
    news = get_news(limit=6)
    _, later_news = split_news(news)
    message = [
        f"📰 <b>Новости</b>",
        "▬▬▬▬▬▬▬▬▬▬▬▬",
        *[f"• <b><a href='{item['url']}'>{item['title']}</a></b>" for item in later_news],
        "▬▬▬▬▬▬▬▬▬▬▬▬",
        "👨‍💼 Администрация: @nordist_admin",
        "<a href='https://bingx.com/partner/KIMTRADING/'>📈 Получить бонусы и пониженную комиссию на BingX</a>"
    ]
    text = "
".join(message)
    send_message(CHANNEL_ID, text)
    send_message(USER_ID, text)

def job_morning_digest():
    print("🟡 Запуск: Утренний дайджест")
    send_morning_digest()

def job_news_to_channel_and_ls():
    print("🟠 Запуск: Новости в канал и ЛС")
    send_news_both()

if __name__ == "__main__":
    if TOKEN is None:
        print("❌ Ошибка: переменная TOKEN не задана!")
        exit(1)

    scheduler = BackgroundScheduler(timezone="Europe/Kiev")
    scheduler.add_job(job_morning_digest, 'cron', hour=9, minute=0)
    scheduler.add_job(job_news_to_channel_and_ls, 'cron', hour=12, minute=0)

    scheduler.start()
    print("✅ Планировщик запущен. Ожидание заданий... (Ctrl+C для остановки)")
    try:
        while True:
            time.sleep(10)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("⛔ Планировщик остановлен.")
