import os
import requests
import feedparser
import pytz
from datetime import datetime
from deep_translator import GoogleTranslator
from apscheduler.schedulers.background import BackgroundScheduler
import time
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002064314678")
USER_ID = os.getenv("USER_ID", "6678054169")

RSS_FEEDS = {
    "ForkLog": "https://forklog.com/feed/",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed"
}

KEYWORDS = ["bitcoin", "ethereum", "sec", "etf", "launch", "upgrade", 
            "crypto", "blockchain", "notcoin", "solana"]

def translate_to_russian(text):
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text[:5000])  # Ограничение длины
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text

def get_news(limit=6):
    news_items = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            logger.info(f"Fetched {len(feed.entries)} entries from {source}")
            
            for entry in feed.entries[:limit*2]:  # Берем с запасом для фильтрации
                try:
                    title = entry.title
                    link = entry.link
                    if any(k.lower() in title.lower() for k in KEYWORDS):
                        translated_title = title if source == "ForkLog" else translate_to_russian(title)
                        news_items.append({'title': translated_title, 'url': link})
                        if len(news_items) >= limit:
                            break
                except Exception as e:
                    logger.error(f"Error processing entry: {e}")
        except Exception as e:
            logger.error(f"Error reading {source}: {e}")
    return news_items[:limit]

def split_news(news, split_index=3):
    return news[:split_index], news[split_index:]

def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Message sent to {chat_id}")
        else:
            logger.error(f"Failed to send to {chat_id}: {response.text}")
    except Exception as e:
        logger.error(f"Error in send_message: {e}")

def create_message(header, news_items):
    current_date = datetime.now(pytz.timezone('Europe/Kiev')).strftime("%d.%m.%Y")
    message = [
        f"{header} ({current_date})",
        "▬▬▬▬▬▬▬▬▬▬▬▬",
        "<b>📌 Главные новости:</b>",
        *[f"• <b><a href='{item['url']}'>{item['title']}</a></b>" for item in news_items],
        "▬▬▬▬▬▬▬▬▬▬▬▬",
        "👨‍💼 Администрация: @nordist_admin",
        "<a href='https://bingx.com/partner/KIMTRADING/'>📈 Получить бонусы на BingX</a>"
    ]
    return "\n".join(message)

def send_morning_digest():
    try:
        logger.info("Starting morning digest")
        news = get_news(limit=6)
        if not news:
            logger.warning("No news found!")
            send_message(CHANNEL_ID, "⚠️ Сегодня новостей не найдено")
            return
            
        digest_news, _ = split_news(news)
        message = create_message("🌅 Утренний криптодайджест", digest_news)
        send_message(CHANNEL_ID, message)
    except Exception as e:
        logger.error(f"Error in morning digest: {e}")

def send_news_both():
    try:
        logger.info("Starting news distribution")
        news = get_news(limit=6)
        if not news:
            logger.warning("No news found!")
            send_message(CHANNEL_ID, "⚠️ Новостей не найдено")
            send_message(USER_ID, "⚠️ Новостей не найдено")
            return
            
        _, later_news = split_news(news)
        message = create_message("📰 Новости", later_news)
        send_message(CHANNEL_ID, message)
        send_message(USER_ID, message)
    except Exception as e:
        logger.error(f"Error in news distribution: {e}")

def setup_scheduler():
    scheduler = BackgroundScheduler(timezone="Europe/Kiev")
    scheduler.add_job(
        send_morning_digest,
        'cron',
        hour=9,
        minute=0,
        misfire_grace_time=60
    )
    scheduler.add_job(
        send_news_both,
        'cron',
        hour=12,
        minute=0,
        misfire_grace_time=60
    )
    return scheduler

if __name__ == "__main__":
    if not TOKEN:
        logger.error("TOKEN environment variable is not set!")
        exit(1)

    logger.info("Starting application")
    
    # Тестовая отправка при старте
    try:
        send_message(USER_ID, "🟢 Бот успешно запущен! Ожидайте дайджест в 7:40 и новости в 7:41.")
    except Exception as e:
        logger.error(f"Test message failed: {e}")

    scheduler = setup_scheduler()
    scheduler.start()

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Application stopped")