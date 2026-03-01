import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import hashlib
import hmac
from datetime import datetime, date, timedelta
from pathlib import Path
import zipfile
import io
import shutil
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlalchemy as sa
from sqlalchemy import create_engine, text
import time
import base64
from PIL import Image
import pytz
import uuid
import re

# ===================== КОНФИГУРАЦИЯ =====================
st.set_page_config(
    page_title="OLYMPUS 2026 • Медицинская лаборатория",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/asidorevich/olympus',
        'Report a bug': 'https://github.com/asidorevich/olympus/issues',
        'About': '# OLYMPUS 2026\nУмная система управления лабораторией'
    }
)

# Константы
PHOTO_DIR = "чеки"
LOGS_DIR = "logs"
BACKUP_DIR = "backups"
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# Часовой пояс
TZ = pytz.timezone('Asia/Almaty')

# ===================== СТИЛИ И АНИМАЦИИ =====================
st.markdown("""
<style>
    /* Глобальные стили */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Montserrat', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    /* Анимированный фон */
    .main {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 30px 30px 0 0;
        padding: 20px;
        margin-top: 20px;
        box-shadow: 0 -20px 40px rgba(0,0,0,0.1);
    }
    
    /* Красивые карточки */
    .glass-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 20px;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 30px 60px rgba(0,0,0,0.15);
    }
    
    /* Метрики */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        line-height: 1.2;
    }
    
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Анимированные кнопки */
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2) !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.05);
        box-shadow: 0 15px 30px rgba(102, 126, 234, 0.4) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) scale(0.95);
    }
    
    /* Табы */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: rgba(255,255,255,0.1);
        padding: 10px;
        border-radius: 50px;
        backdrop-filter: blur(10px);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 40px !important;
        padding: 10px 25px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #667eea, #764ba2) !important;
        color: white !important;
    }
    
    /* Анимации загрузки */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .loading {
        animation: pulse 2s infinite;
    }
    
    /* Уведомления */
    .custom-success {
        background: linear-gradient(45deg, #10b981, #059669);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        animation: slideIn 0.5s ease;
    }
    
    .custom-error {
        background: linear-gradient(45deg, #ef4444, #dc2626);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        animation: slideIn 0.5s ease;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(-100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    /* Прогресс-бары */
    .progress-container {
        width: 100%;
        background: #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
        margin: 10px 0;
    }
    
    .progress-bar {
        height: 20px;
        background: linear-gradient(45deg, #667eea, #764ba2);
        transition: width 1s ease;
        border-radius: 10px;
    }
    
    /* Мобильная адаптация */
    @media (max-width: 768px) {
        .main {
            padding: 10px;
        }
        
        .metric-value {
            font-size: 1.8rem;
        }
        
        .stButton > button {
            padding: 8px 20px !important;
            font-size: 0.9rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 8px 15px !important;
            font-size: 0.9rem !important;
        }
    }
    
    /* Темная тема */
    @media (prefers-color-scheme: dark) {
        .main {
            background: rgba(18, 18, 18, 0.95);
            color: #fff;
        }
        
        .glass-card {
            background: rgba(30, 30, 30, 0.95);
            border-color: rgba(255,255,255,0.1);
        }
        
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(0,0,0,0.3);
        }
    }
</style>
""", unsafe_allow_html=True)

# ===================== БЕЗОПАСНОСТЬ И ЛОГИРОВАНИЕ =====================
def hash_password(password):
    """Хеширование пароля"""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return salt + key

def verify_password(password, hashed):
    """Проверка пароля"""
    salt = hashed[:32]
    key = hashed[32:]
    new_key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return hmac.compare_digest(key, new_key)

def log_action(action, user, details=""):
    """Логирование действий"""
    log_entry = {
        "timestamp": datetime.now(TZ).isoformat(),
        "user": user,
        "action": action,
        "details": details,
        "session_id": st.session_state.get("session_id", str(uuid.uuid4()))
    }
    
    log_file = Path(LOGS_DIR) / f"log_{date.today().isoformat()}.json"
    
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []
    
    logs.append(log_entry)
    
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# ===================== БАЗА ДАННЫХ =====================
@st.cache_resource
def get_engine():
    """Получение движка БД с кешированием"""
    return create_engine(
        st.secrets["db_url"],
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=3600
    )

def get_raw(table):
    """Безопасное получение данных"""
    try:
        with get_engine().connect() as conn:
            return pd.read_sql(f"SELECT * FROM {table}", conn)
    except Exception as e:
        st.error(f"Ошибка загрузки {table}: {str(e)}")
        return pd.DataFrame()

def save_raw(table, df):
    """Безопасное сохранение данных"""
    try:
        with get_engine().connect() as conn:
            df.to_sql(table, conn, if_exists="replace", index=False)
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения {table}: {str(e)}")
        return False

def delete_all_from_table(table):
    """Безопасное удаление данных"""
    try:
        with get_engine().connect() as conn:
            conn.execute(text(f"DELETE FROM {table}"))
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Ошибка удаления {table}: {str(e)}")
        return False

# ===================== ЗАГРУЗКА ДАННЫХ =====================
@st.cache_data(ttl=300)  # Кеш на 5 минут
def load_all_data():
    """Загрузка всех данных с кешированием"""
    return {
        "purchases": get_raw("purchases"),
        "stock": get_raw("stock"),
        "orders": get_raw("orders"),
        "last_update": datetime.now(TZ).isoformat()
    }

# ===================== ИНИЦИАЛИЗАЦИЯ СЕССИИ =====================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.data = load_all_data()
    st.session_state.theme = "light"
    st.session_state.notifications = []
    st.session_state.favorites = []

# ===================== ЛОГОТИП И ЗАГОЛОВОК =====================
LOGO_URL = "https://github.com/asidorevich/my_homework_repo/blob/main/logo.PNG?raw=true"

def get_base64_of_image(image_path):
    """Конвертация изображения в base64"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

st.markdown(f"""
<div style="text-align: center; padding: 30px 0;">
    <div style="display: inline-block; position: relative;">
        <img src="{LOGO_URL}" style="width: 150px; height: 150px; border-radius: 50%; 
             border: 5px solid white; box-shadow: 0 20px 40px rgba(0,0,0,0.2); 
             animation: pulse 2s infinite;">
        <div style="position: absolute; bottom: 0; right: 0; 
                    background: linear-gradient(45deg, #667eea, #764ba2);
                    color: white; padding: 5px 15px; border-radius: 20px;
                    font-size: 0.9rem; font-weight: 600;">
            v2.0
        </div>
    </div>
    <h1 style="font-size: 4rem; margin: 20px 0 10px; 
               background: linear-gradient(45deg, #667eea, #764ba2);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;
               text-shadow: 0 10px 20px rgba(102,126,234,0.3);">
        OLYMPUS
    </h1>
    <p style="font-size: 1.2rem; color: #667eea; letter-spacing: 5px;
              text-transform: uppercase; font-weight: 600;">
        2026 • Медицинская лаборатория
    </p>
</div>
""", unsafe_allow_html=True)

# ===================== АВТОРИЗАЦИЯ =====================
if "role" not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

if st.session_state.role is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.markdown("""
            <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="color: #667eea;">🔐 Вход в систему</h2>
                <p style="color: #666;">Введите свои учетные данные</p>
            </div>
            """, unsafe_allow_html=True)
            
            role = st.selectbox(
                "Выберите роль",
                ["👩‍⚕️ Медсестра", "📦 Снабжение", "👑 Администратор"],
                index=0
            )
            
            username = st.text_input("👤 Имя пользователя", placeholder="Введите имя")
            password = st.text_input("🔑 Пароль", type="password", placeholder="Введите пароль")
            
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                submitted = st.form_submit_button("🚀 ВОЙТИ", use_container_width=True)
            
            if submitted:
                # В реальном приложении здесь должна быть проверка по базе данных
                # Сейчас для демонстрации используем простую проверку
                valid_credentials = {
                    "👩‍⚕️ Медсестра": {"username": "nurse", "password": "med123", "role": "med"},
                    "📦 Снабжение": {"username": "snab", "password": "olympus2025", "role": "snab"},
                    "👑 Администратор": {"username": "admin", "password": "godmode2026", "role": "admin"}
                }
                
                cred = valid_credentials.get(role)
                if cred and username == cred["username"] and password == cred["password"]:
                    st.session_state.role = cred["role"]
                    st.session_state.user = username
                    st.session_state.login_time = datetime.now(TZ).isoformat()
                    
                    # Логируем вход
                    log_action("LOGIN", username, f"Вход как {role}")
                    
                    st.success(f"✅ Добро пожаловать, {username}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Неверное имя пользователя или пароль")
    
    st.stop()

# ===================== САЙДБАР =====================
with st.sidebar:
    st.image(LOGO_URL, width=100)
    
    st.markdown(f"""
    <div style="text-align: center; margin: 20px 0;">
        <p style="color: #667eea; font-weight: 600;">👤 {st.session_state.user}</p>
        <p style="font-size: 0.9rem; color: #666;">
            {datetime.now(TZ).strftime("%d.%m.%Y %H:%M")}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Метрики в сайдбаре
    data = st.session_state.data
    total_spent = data["purchases"]["total"].sum() if not data["purchases"].empty else 0
    critical_items = len(data["stock"][data["stock"]["quantity"] <= data["stock"]["min_qty"]]) if not data["stock"].empty else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="padding: 15px;">
            <div class="metric-value">{total_spent:,.0f}</div>
            <div class="metric-label">₸ всего</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="padding: 15px; background: linear-gradient(45deg, #f97316, #f59e0b);">
            <div class="metric-value">{critical_items}</div>
            <div class="metric-label">⚠️ критично</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Быстрые действия
    st.markdown("### ⚡ Быстрые действия")
    
    if st.button("🔄 Обновить данные", use_container_width=True):
        with st.spinner("Обновление..."):
            st.session_state.data = load_all_data()
            st.toast("✅ Данные обновлены!", icon="🔄")
            time.sleep(0.5)
            st.rerun()
    
    if st.button("📊 Экспорт отчета", use_container_width=True):
        # Создаем отчет
        report = io.BytesIO()
        with pd.ExcelWriter(report, engine='openpyxl') as writer:
            for name, df in data.items():
                if not df.empty:
                    df.to_excel(writer, sheet_name=name, index=False)
        
        st.download_button(
            "📥 Скачать отчет",
            report.getvalue(),
            f"report_{date.today().isoformat()}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    if st.button("🚪 Выйти", use_container_width=True, type="secondary"):
        log_action("LOGOUT", st.session_state.user, "Выход из системы")
        st.session_state.role = None
        st.session_state.user = None
        st.rerun()
    
    st.divider()
    
    # Настройки
    with st.expander("⚙️ Настройки"):
        theme = st.select_slider(
            "Тема",
            options=["🌞 Светлая", "🌙 Темная"],
            value="🌞 Светлая"
        )
        
        notifications = st.checkbox("🔔 Включить уведомления", value=True)
        
        if st.button("💾 Сохранить настройки"):
            st.session_state.theme = theme
            st.session_state.notifications = notifications
            st.toast("✅ Настройки сохранены!")

# ===================== ОСНОВНОЙ ИНТЕРФЕЙС =====================
# В зависимости от роли показываем разные вкладки
if st.session_state.role == "med":
    # ===================== МЕДСЕСТРА =====================
    tabs = st.tabs([
        "🏠 Главная",
        "📦 Склад",
        "📉 Списание",
        "📨 Заявки",
        "📊 Аналитика",
        "📱 Мобильное меню"
    ])
    
    # Главная
    with tabs[0]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📊 Панель управления")
        
        # Ключевые метрики
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">позиций на складе</div>
            </div>
            """.format(len(data["stock"])))
        
        with col2:
            pending_orders = len(data["orders"][data["orders"]["status"] == "new"])
            st.markdown("""
            <div class="metric-card" style="background: linear-gradient(45deg, #f97316, #f59e0b);">
                <div class="metric-value">{}</div>
                <div class="metric-label">активных заявок</div>
            </div>
            """.format(pending_orders))
        
        with col3:
            low_stock = len(data["stock"][data["stock"]["quantity"] <= data["stock"]["min_qty"]])
            color = "#10b981" if low_stock == 0 else "#ef4444"
            st.markdown("""
            <div class="metric-card" style="background: {};">
                <div class="metric-value">{}</div>
                <div class="metric-label">критических остатков</div>
            </div>
            """.format(color, low_stock))
        
        with col4:
            today_usage = 0  # Здесь можно добавить расчет расхода за сегодня
            st.markdown("""
            <div class="metric-card" style="background: linear-gradient(45deg, #3b82f6, #2563eb);">
                <div class="metric-value">{}</div>
                <div class="metric-label">использовано сегодня</div>
            </div>
            """.format(today_usage))
        
        st.divider()
        
        # Критические позиции
        if low_stock > 0:
            st.error(f"⚠️ Обнаружено {low_stock} позиций с критическим остатком!")
            
            critical = data["stock"][data["stock"]["quantity"] <= data["stock"]["min_qty"]].copy()
            for _, item in critical.iterrows():
                percent = (item["quantity"] / item["min_qty"]) * 100
                st.markdown(f"""
                <div style="margin: 10px 0; padding: 15px; background: rgba(239, 68, 68, 0.1); 
                            border-radius: 10px; border-left: 5px solid #ef4444;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: 600;">{item['item']}</span>
                        <span style="color: #ef4444; font-weight: 600;">{item['quantity']} / {item['min_qty']} {item['unit']}</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {percent}%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Склад
    with tabs[1]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📦 Текущие остатки")
        
        # Поиск и фильтры
        col1, col2 = st.columns([2, 1])
        with col1:
            search = st.text_input("🔍 Поиск по названию", placeholder="Введите название товара...")
        with col2:
            category_filter = st.selectbox(
                "📂 Категория",
                ["Все"] + sorted(data["stock"]["category"].unique().tolist()) if not data["stock"].empty else ["Все"]
            )
        
        # Фильтрация данных
        stock_display = data["stock"].copy()
        if search:
            stock_display = stock_display[stock_display["item"].str.contains(search, case=False, na=False)]
        if category_filter != "Все":
            stock_display = stock_display[stock_display["category"] == category_filter]
        
        # Отображение в виде карточек для мобильных
        if not stock_display.empty:
            for _, item in stock_display.iterrows():
                status_color = "#10b981" if item["quantity"] > item["min_qty"] else "#ef4444"
                st.markdown(f"""
                <div style="margin: 10px 0; padding: 15px; background: white; border-radius: 10px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-weight: 600; font-size: 1.1rem;">{item['item']}</span>
                            <br>
                            <span style="color: #666; font-size: 0.9rem;">{item['category']}</span>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 1.5rem; font-weight: 700; color: {status_color};">
                                {item['quantity']}
                            </span>
                            <br>
                            <span style="color: #666; font-size: 0.9rem;">{item['unit']}</span>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <div class="progress-container">
                            <div class="progress-bar" style="width: {(item['quantity']/item['min_qty']*100) if item['min_qty'] > 0 else 100}%;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                            <span style="color: #666;">Минимум: {item['min_qty']}</span>
                            <span style="color: #666;">Текущий остаток</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("😕 Ничего не найдено")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Списание
    with tabs[2]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📉 Списание материалов")
        
        # Быстрое списание для популярных товаров
        if not data["stock"].empty:
            st.markdown("#### ⚡ Быстрое списание")
            popular_items = data["stock"].nlargest(5, "quantity")["item"].tolist()
            
            cols = st.columns(5)
            for i, item in enumerate(popular_items[:5]):
                with cols[i]:
                    if st.button(f"📦 {item}", key=f"quick_{item}"):
                        st.session_state["quick_item"] = item
        
        st.divider()
        
        # Форма списания
        with st.form("write_off_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Выбор товара
                item_options = sorted(data["stock"]["item"].tolist()) if not data["stock"].empty else []
                default_item = st.session_state.get("quick_item", item_options[0] if item_options else None)
                
                item = st.selectbox(
                    "Выберите товар",
                    options=item_options,
                    index=item_options.index(default_item) if default_item in item_options else 0
                )
                
                # Получаем информацию о товаре
                if item and not data["stock"].empty:
                    item_info = data["stock"][data["stock"]["item"] == item].iloc[0]
                    current_qty = item_info["quantity"]
                    unit = item_info["unit"]
                    
                    st.info(f"📦 Доступно: **{current_qty} {unit}**")
                    
                    qty = st.number_input(
                        "Количество",
                        min_value=0.0,
                        max_value=float(current_qty),
                        step=0.1,
                        format="%.1f"
                    )
            
            with col2:
                patient = st.text_input("👤 Пациент / № анализа", placeholder="ФИО или номер")
                reason = st.selectbox(
                    "📋 Причина",
                    ["Использование", "Брак", "Порча", "Истечение срока", "Другое"]
                )
                comment = st.text_area("📝 Комментарий", placeholder="Дополнительная информация")
            
            # Кнопка отправки
            submitted = st.form_submit_button("✅ СПИСАТЬ", use_container_width=True)
            
            if submitted:
                if qty > 0:
                    # Обновляем остатки
                    data["stock"].loc[data["stock"]["item"] == item, "quantity"] -= qty
                    
                    # Сохраняем изменения
                    if save_raw("stock", data["stock"]):
                        # Логируем действие
                        log_action("WRITE_OFF", st.session_state.user, f"Списание: {item} {qty} {unit}")
                        
                        # Добавляем запись в историю закупок как списание
                        new_entry = pd.DataFrame([{
                            "date": date.today().isoformat(),
                            "item": f"[СПИСАНО] {item}",
                            "category": item_info["category"],
                            "qty": qty,
                            "unit": unit,
                            "price": 0,
                            "total": 0,
                            "supplier": "",
                            "comment": f"{reason}: {comment}" if comment else reason,
                            "photo": "",
                            "added_by": st.session_state.user
                        }])
                        
                        data["purchases"] = pd.concat([data["purchases"], new_entry], ignore_index=True)
                        save_raw("purchases", data["purchases"])
                        
                        # Обновляем данные в сессии
                        st.session_state.data = load_all_data()
                        
                        st.toast(f"✅ Списано {qty} {unit} {item}", icon="🗑️")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("❌ Укажите количество для списания")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Заявки
    with tabs[3]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📨 Создание заявки")
        
        with st.form("order_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                item = st.text_input("📦 Что нужно?", placeholder="Например: Перчатки нитриловые M")
                qty = st.number_input("🔢 Количество", min_value=1, step=1)
            
            with col2:
                unit = st.selectbox("📏 Единица измерения", ["шт", "упак", "коробка", "пара", "литр", "кг"])
                priority = st.select_slider(
                    "⚡ Приоритет",
                    options=["Низкий", "Средний", "Высокий", "Критический"],
                    value="Средний"
                )
            
            comment = st.text_area("📝 Комментарий", placeholder="Дополнительная информация...")
            
            submitted = st.form_submit_button("📨 ОТПРАВИТЬ ЗАЯВКУ", use_container_width=True)
            
            if submitted:
                if item.strip():
                    # Создаем заявку
                    new_order = pd.DataFrame([{
                        "item": item.strip(),
                        "qty": qty,
                        "unit": unit,
                        "comment": f"Приоритет: {priority}. {comment}" if comment else f"Приоритет: {priority}",
                        "ordered_by": st.session_state.user,
                        "ordered_at": datetime.now(TZ).isoformat(),
                        "status": "new",
                        "priority": priority
                    }])
                    
                    data["orders"] = pd.concat([data["orders"], new_order], ignore_index=True)
                    
                    if save_raw("orders", data["orders"]):
                        log_action("CREATE_ORDER", st.session_state.user, f"Заявка: {item} {qty} {unit}")
                        st.session_state.data = load_all_data()
                        st.toast("✅ Заявка отправлена!", icon="📨")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("❌ Укажите название товара")
        
        st.divider()
        
        # История заявок
        st.subheader("📋 История ваших заявок")
        user_orders = data["orders"][data["orders"]["ordered_by"] == st.session_state.user]
        
        if not user_orders.empty:
            for _, order in user_orders.iterrows():
                status_color = {
                    "new": "#f97316",
                    "done": "#10b981",
                    "rejected": "#ef4444"
                }.get(order["status"], "#666")
                
                st.markdown(f"""
                <div style="margin: 10px 0; padding: 15px; background: white; border-radius: 10px;
                            border-left: 5px solid {status_color};">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: 600;">{order['item']}</span>
                        <span style="color: {status_color};">{order['status'].upper()}</span>
                    </div>
                    <div style="color: #666; font-size: 0.9rem;">
                        {order['qty']} {order['unit']} • {order['ordered_at'][:10]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("😕 У вас пока нет заявок")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Аналитика
    with tabs[4]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📊 Аналитика расхода")
        
        if not data["purchases"].empty and not data["stock"].empty:
            # График расхода по категориям
            purchases_with_dates = data["purchases"].copy()
            purchases_with_dates["date"] = pd.to_datetime(purchases_with_dates["date"])
            purchases_with_dates = purchases_with_dates[purchases_with_dates["date"].dt.year == datetime.now().year]
            
            if not purchases_with_dates.empty:
                fig = px.line(
                    purchases_with_dates.groupby(
                        [purchases_with_dates["date"].dt.strftime("%Y-%m"), "category"]
                    )["total"].sum().reset_index(),
                    x="date",
                    y="total",
                    color="category",
                    title="Динамика расходов по месяцам"
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            # Топ расходуемых товаров
            st.subheader("📈 Топ расходуемых товаров")
            usage_stats = data["purchases"][data["purchases"]["item"].str.contains("СПИСАНО") == False]
            usage_stats = usage_stats.groupby("item")["qty"].sum().sort_values(ascending=False).head(10)
            
            fig = px.bar(
                x=usage_stats.values,
                y=usage_stats.index,
                orientation='h',
                title="Самые популярные товары"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("😕 Недостаточно данных для аналитики")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Мобильное меню
    with tabs[5]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📱 Мобильное меню быстрых действий")
        
        # Большие кнопки для мобильных
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📦 Склад", use_container_width=True):
                st.switch_page(tabs[1])
            
            if st.button("📉 Списание", use_container_width=True):
                st.switch_page(tabs[2])
        
        with col2:
            if st.button("📨 Заявка", use_container_width=True):
                st.switch_page(tabs[3])
            
            if st.button("📊 Аналитика", use_container_width=True):
                st.switch_page(tabs[4])
        
        st.divider()
        
        # QR-код для быстрого доступа (можно сгенерировать)
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <div style="background: white; padding: 20px; border-radius: 10px; display: inline-block;">
                <div style="width: 150px; height: 150px; background: #000; margin: 0 auto;"></div>
            </div>
            <p style="margin-top: 10px;">Отсканируйте для быстрого доступа</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.role == "snab":
    # ===================== СНАБЖЕНИЕ =====================
    tabs = st.tabs([
        "🏠 Дашборд",
        "📨 Заявки",
        "🛒 Закупки",
        "📦 Склад",
        "📈 Аналитика",
        "🖼 Чеки"
    ])
    
    # Дашборд
    with tabs[0]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🏠 Панель управления снабжением")
        
        # Метрики
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            pending_orders = len(data["orders"][data["orders"]["status"] == "new"])
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{pending_orders}</div>
                <div class="metric-label">новых заявок</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            total_purchases = len(data["purchases"])
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(45deg, #10b981, #059669);">
                <div class="metric-value">{total_purchases}</div>
                <div class="metric-label">закупок всего</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            total_spent = data["purchases"]["total"].sum() if not data["purchases"].empty else 0
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(45deg, #f97316, #f59e0b);">
                <div class="metric-value">{total_spent:,.0f}</div>
                <div class="metric-label">₸ потрачено</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            unique_suppliers = data["purchases"]["supplier"].nunique() if not data["purchases"].empty else 0
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(45deg, #3b82f6, #2563eb);">
                <div class="metric-value">{unique_suppliers}</div>
                <div class="metric-label">поставщиков</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # Последние заявки
        st.subheader("📨 Последние заявки")
        recent_orders = data["orders"][data["orders"]["status"] == "new"].head(5)
        
        if not recent_orders.empty:
            for _, order in recent_orders.iterrows():
                priority_color = {
                    "Низкий": "#666",
                    "Средний": "#f97316",
                    "Высокий": "#ef4444",
                    "Критический": "#7f1d1d"
                }.get(order.get("priority", "Средний"), "#666")
                
                st.markdown(f"""
                <div style="margin: 10px 0; padding: 15px; background: white; border-radius: 10px;
                            border-left: 5px solid {priority_color};">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: 600;">{order['item']}</span>
                        <span style="color: {priority_color};">{order.get('priority', 'Средний')}</span>
                    </div>
                    <div style="color: #666;">
                        {order['qty']} {order['unit']} • от {order['ordered_by']}
                    </div>
                    <div style="font-size: 0.9rem; color: #999;">
                        {order['ordered_at'][:16]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Нет новых заявок")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Заявки
    with tabs[1]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📨 Управление заявками")
        
        # Фильтры
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "📊 Статус",
                ["Все", "new", "done", "rejected"]
            )
        with col2:
            search = st.text_input("🔍 Поиск", placeholder="Поиск по товару...")
        
        # Фильтрация
        orders_display = data["orders"].copy()
        if status_filter != "Все":
            orders_display = orders_display[orders_display["status"] == status_filter]
        if search:
            orders_display = orders_display[orders_display["item"].str.contains(search, case=False, na=False)]
        
        if not orders_display.empty:
            for idx, order in orders_display.iterrows():
                with st.expander(f"📦 {order['item']} - {order['qty']} {order['unit']}"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**От:** {order['ordered_by']}")
                        st.write(f"**Когда:** {order['ordered_at']}")
                        st.write(f"**Комментарий:** {order.get('comment', 'Нет')}")
                    
                    with col2:
                        if order["status"] == "new":
                            if st.button("✅ Выполнить", key=f"done_{idx}", use_container_width=True):
                                orders_display.loc[idx, "status"] = "done"
                                if save_raw("orders", orders_display):
                                    log_action("ORDER_DONE", st.session_state.user, f"Заявка выполнена: {order['item']}")
                                    st.session_state.data = load_all_data()
                                    st.toast("✅ Заявка выполнена!")
                                    st.rerun()
                            
                            if st.button("❌ Отклонить", key=f"rej_{idx}", use_container_width=True):
                                orders_display.loc[idx, "status"] = "rejected"
                                if save_raw("orders", orders_display):
                                    log_action("ORDER_REJECTED", st.session_state.user, f"Заявка отклонена: {order['item']}")
                                    st.toast("❌ Заявка отклонена!")
                                    st.rerun()
                    
                    with col3:
                        if st.button("🔄 В работу", key=f"work_{idx}", use_container_width=True):
                            st.session_state["order_to_purchase"] = {
                                "item": order["item"],
                                "qty": order["qty"],
                                "unit": order["unit"],
                                "comment": order.get("comment", "")
                            }
                            st.toast("📝 Данные перенесены в закупку!")
        else:
            st.info("😕 Заявок не найдено")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Закупки
    with tabs[2]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🛒 Добавление закупки")
        
        # Если есть данные из заявки
        default_data = st.session_state.get("order_to_purchase", {})
        
        with st.form("purchase_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                item = st.text_input(
                    "📦 Товар",
                    value=default_data.get("item", ""),
                    placeholder="Название товара"
                )
                
                category = st.selectbox(
                    "📂 Категория",
                    ["Расходный материал", "Канцелярия", "Пробирки", "Хозтовары", "Прочее"]
                )
                
                qty = st.number_input(
                    "🔢 Количество",
                    min_value=1,
                    value=int(default_data.get("qty", 1)),
                    step=1
                )
                
                unit = st.selectbox(
                    "📏 Единица измерения",
                    ["шт", "упак", "коробка", "рулон", "литр", "кг"],
                    index=["шт", "упак", "коробка", "рулон", "литр", "кг"].index(default_data.get("unit", "шт")) if default_data.get("unit") in ["шт", "упак", "коробка", "рулон", "литр", "кг"] else 0
                )
            
            with col2:
                price = st.number_input("💰 Цена за единицу, ₸", min_value=0.0, step=10.0)
                supplier = st.text_input("🏭 Поставщик", placeholder="Название поставщика")
                invoice_number = st.text_input("📄 № счета/накладной", placeholder="Номер документа")
                
                purchase_date = st.date_input(
                    "📅 Дата закупки",
                    value=date.today()
                )
            
            # Флаги
            col1, col2 = st.columns(2)
            with col1:
                no_track = st.checkbox("❌ Не учитывать на складе")
            with col2:
                urgent = st.checkbox("⚡ Срочная закупка")
            
            # Загрузка файлов
            files = st.file_uploader(
                "📎 Прикрепить документы",
                accept_multiple_files=True,
                type=["png", "jpg", "jpeg", "pdf", "xlsx", "docx"]
            )
            
            comment = st.text_area(
                "📝 Комментарий",
                value=default_data.get("comment", ""),
                placeholder="Дополнительная информация..."
            )
            
            submitted = st.form_submit_button("💾 СОХРАНИТЬ ЗАКУПКУ", use_container_width=True)
            
            if submitted:
                if item and qty > 0 and price > 0:
                    # Сохраняем файлы
                    paths = []
                    if files:
                        for f in files:
                            safe_name = f"{date.today()}_{item}_{f.name}".replace(" ", "_")
                            safe_name = re.sub(r'[^\w\-_\. ]', '', safe_name)
                            path = os.path.join(PHOTO_DIR, safe_name)
                            
                            with open(path, "wb") as out:
                                out.write(f.getbuffer())
                            paths.append(path)
                    
                    # Создаем запись
                    new_purchase = pd.DataFrame([{
                        "date": purchase_date.isoformat(),
                        "item": item,
                        "category": category,
                        "qty": qty,
                        "unit": unit,
                        "price": price,
                        "total": qty * price,
                        "supplier": supplier,
                        "comment": f"Срочно: {urgent}. {comment}" if urgent else comment,
                        "photo": ";".join(paths) if paths else "",
                        "added_by": st.session_state.user,
                        "invoice": invoice_number
                    }])
                    
                    data["purchases"] = pd.concat([data["purchases"], new_purchase], ignore_index=True)
                    
                    if save_raw("purchases", data["purchases"]):
                        # Обновляем склад
                        if not no_track:
                            if item in data["stock"]["item"].values:
                                data["stock"].loc[data["stock"]["item"] == item, "quantity"] += qty
                            else:
                                new_stock = pd.DataFrame([{
                                    "item": item,
                                    "category": category,
                                    "unit": unit,
                                    "quantity": qty,
                                    "min_qty": 5
                                }])
                                data["stock"] = pd.concat([data["stock"], new_stock], ignore_index=True)
                            
                            save_raw("stock", data["stock"])
                        
                        # Логируем
                        log_action("PURCHASE_ADDED", st.session_state.user, f"Закупка: {item} {qty} {unit} на {qty * price}₸")
                        
                        # Очищаем временные данные
                        if "order_to_purchase" in st.session_state:
                            del st.session_state["order_to_purchase"]
                        
                        st.session_state.data = load_all_data()
                        st.toast("✅ Закупка добавлена!", icon="🛒")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("❌ Заполните все обязательные поля")
        
        st.divider()
        
        # Последние закупки
        st.subheader("📋 Последние закупки")
        recent_purchases = data["purchases"].sort_values("date", ascending=False).head(10)
        
        if not recent_purchases.empty:
            st.dataframe(
                recent_purchases[["date", "item", "qty", "unit", "total", "supplier"]],
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Склад
    with tabs[3]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📦 Управление складом")
        
        # Редактирование остатков
        edited_stock = st.data_editor(
            data["stock"],
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "item": "Товар",
                "category": "Категория",
                "unit": "Ед.изм",
                "quantity": st.column_config.NumberColumn("Остаток", min_value=0),
                "min_qty": st.column_config.NumberColumn("Минимум", min_value=0)
            }
        )
        
        if st.button("💾 Сохранить изменения", type="primary", use_container_width=True):
            if save_raw("stock", edited_stock):
                st.session_state.data = load_all_data()
                log_action("STOCK_UPDATED", st.session_state.user, "Ручное обновление склада")
                st.toast("✅ Изменения сохранены!")
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Аналитика
    with tabs[4]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📈 Расширенная аналитика")
        
        if not data["purchases"].empty:
            purchases_analytics = data["purchases"].copy()
            purchases_analytics["date"] = pd.to_datetime(purchases_analytics["date"])
            
            # Выбор периода
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Начало",
                    value=date.today() - timedelta(days=30)
                )
            with col2:
                end_date = st.date_input(
                    "Конец",
                    value=date.today()
                )
            
            # Фильтруем по дате
            mask = (purchases_analytics["date"].dt.date >= start_date) & \
                   (purchases_analytics["date"].dt.date <= end_date)
            filtered = purchases_analytics[mask]
            
            if not filtered.empty:
                # Основные метрики
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total = filtered["total"].sum()
                    st.metric("💰 Всего", f"{total:,.0f} ₸")
                
                with col2:
                    avg = filtered["total"].mean()
                    st.metric("📊 Средний чек", f"{avg:,.0f} ₸")
                
                with col3:
                    count = len(filtered)
                    st.metric("📦 Закупок", count)
                
                with col4:
                    items = filtered["item"].nunique()
                    st.metric("📋 Позиций", items)
                
                st.divider()
                
                # Графики
                col1, col2 = st.columns(2)
                
                with col1:
                    # По категориям
                    cat_stats = filtered.groupby("category")["total"].sum().sort_values(ascending=False)
                    fig = px.pie(
                        values=cat_stats.values,
                        names=cat_stats.index,
                        title="Распределение по категориям"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # По поставщикам
                    supp_stats = filtered.groupby("supplier")["total"].sum().sort_values(ascending=False).head(10)
                    fig = px.bar(
                        x=supp_stats.values,
                        y=supp_stats.index,
                        orientation='h',
                        title="Топ поставщиков"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Динамика
                daily = filtered.groupby(filtered["date"].dt.strftime("%Y-%m-%d"))["total"].sum().reset_index()
                fig = px.line(
                    daily,
                    x="date",
                    y="total",
                    title="Динамика расходов"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("😕 Нет данных за выбранный период")
        else:
            st.info("😕 Недостаточно данных для аналитики")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Чеки
    with tabs[5]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🖼 Галерея чеков")
        
        # Загрузка новых чеков
        with st.expander("📤 Загрузить новые чеки"):
            uploaded_files = st.file_uploader(
                "Выберите файлы",
                accept_multiple_files=True,
                type=["png", "jpg", "jpeg", "pdf"]
            )
            
            if uploaded_files:
                if st.button("💾 Сохранить все", use_container_width=True):
                    saved = 0
                    for f in uploaded_files:
                        safe_name = f"{date.today()}_{f.name}".replace(" ", "_")
                        safe_name = re.sub(r'[^\w\-_\. ]', '', safe_name)
                        path = os.path.join(PHOTO_DIR, safe_name)
                        
                        with open(path, "wb") as out:
                            out.write(f.getbuffer())
                        saved += 1
                    
                    st.toast(f"✅ Сохранено {saved} файлов!")
                    st.rerun()
        
        st.divider()
        
        # Отображение чеков
        files = sorted(Path(PHOTO_DIR).iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if files:
            # Пагинация
            items_per_page = 12
            total_pages = len(files) // items_per_page + 1
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page = st.number_input(
                    "Страница",
                    min_value=1,
                    max_value=total_pages,
                    value=1
                )
            
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(files))
            
            # Сетка изображений
            cols = st.columns(4)
            for i, f in enumerate(files[start_idx:end_idx]):
                with cols[i % 4]:
                    if f.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                        st.image(str(f), use_container_width=True)
                    else:
                        st.markdown(f"📄 {f.name}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("👁️", key=f"view_{f.name}"):
                            if f.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                                st.image(str(f))
                    with col2:
                        if st.button("🗑️", key=f"del_{f.name}"):
                            f.unlink()
                            st.toast(f"🗑️ {f.name} удален")
                            st.rerun()
        else:
            st.info("😕 Нет загруженных чеков")
        
        st.markdown('</div>', unsafe_allow_html=True)

else:  # admin
    # ===================== АДМИНИСТРАТОР =====================
    tabs = st.tabs([
        "📊 Обзор",
        "👥 Пользователи",
        "✏️ Редактор",
        "💾 Бэкапы",
        "📈 Логи",
        "⚙️ Настройки"
    ])
    
    # Обзор
    with tabs[0]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📊 Системный обзор")
        
        # Метрики
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Закупок всего", len(data["purchases"]))
        with col2:
            st.metric("Товаров на складе", len(data["stock"]))
        with col3:
            st.metric("Всего заявок", len(data["orders"]))
        with col4:
            st.metric("Активных сессий", 1)  # Здесь можно добавить реальный подсчет
        
        st.divider()
        
        # Статус системы
        st.subheader("🟢 Статус системы")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            - **База данных:** ✅ Подключено
            - **Хранилище файлов:** ✅ Доступно
            - **Кеш:** ✅ Активен
            - **Последнее обновление:** {}
            """.format(st.session_state.data.get("last_update", "Неизвестно")))
        
        with col2:
            # Статистика использования
            total_size = sum(f.stat().st_size for f in Path(PHOTO_DIR).glob("*")) / 1024 / 1024
            st.markdown(f"""
            - **Занято места:** {total_size:.1f} MB
            - **Всего файлов:** {len(list(Path(PHOTO_DIR).glob("*")))}
            - **Размер БД:** ~{len(data['purchases']) + len(data['stock']) + len(data['orders'])} записей
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Пользователи (заглушка для демонстрации)
    with tabs[1]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("👥 Управление пользователями")
        
        users_data = pd.DataFrame([
            {"username": "nurse", "role": "med", "last_login": "2024-01-15 10:30", "status": "active"},
            {"username": "snab", "role": "snab", "last_login": "2024-01-15 09:15", "status": "active"},
            {"username": "admin", "role": "admin", "last_login": "2024-01-15 11:00", "status": "active"}
        ])
        
        st.data_editor(
            users_data,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "username": "Имя пользователя",
                "role": st.column_config.SelectboxColumn(
                    "Роль",
                    options=["med", "snab", "admin"]
                ),
                "last_login": "Последний вход",
                "status": st.column_config.SelectboxColumn(
                    "Статус",
                    options=["active", "blocked", "pending"]
                )
            }
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Редактор данных
    with tabs[2]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("✏️ Редактирование данных")
        
        table = st.selectbox(
            "Выберите таблицу",
            ["purchases", "stock", "orders"]
        )
        
        df = data[table].copy()
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Сохранить изменения", use_container_width=True, type="primary"):
                if save_raw(table, edited_df):
                    st.session_state.data = load_all_data()
                    log_action("ADMIN_EDIT", st.session_state.user, f"Редактирование {table}")
                    st.toast("✅ Изменения сохранены!")
                    st.rerun()
        
        with col2:
            if st.button("🔄 Сбросить", use_container_width=True):
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Бэкапы
    with tabs[3]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("💾 Создание бэкапов")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📦 Создать бэкап", use_container_width=True, type="primary"):
                with st.spinner("Создание бэкапа..."):
                    # Создаем ZIP архив
                    backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    backup_path = Path(BACKUP_DIR) / backup_name
                    
                    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        # Сохраняем таблицы
                        for t in ["purchases", "stock", "orders"]:
                            df = data[t]
                            csv_data = df.to_csv(index=False).encode('utf-8')
                            zf.writestr(f"{t}.csv", csv_data)
                        
                        # Сохраняем файлы
                        for f in Path(PHOTO_DIR).glob("*"):
                            zf.write(f, f"чеки/{f.name}")
                        
                        # Сохраняем логи
                        for f in Path(LOGS_DIR).glob("*"):
                            zf.write(f, f"логи/{f.name}")
                    
                    st.success(f"✅ Бэкап создан: {backup_name}")
                    
                    # Предлагаем скачать
                    with open(backup_path, "rb") as f:
                        st.download_button(
                            "📥 Скачать бэкап",
                            f.read(),
                            backup_name,
                            "application/zip",
                            use_container_width=True
                        )
        
        with col2:
            # Список бэкапов
            st.subheader("📋 История бэкапов")
            backups = sorted(Path(BACKUP_DIR).glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)
            
            for b in backups[:5]:
                size_mb = b.stat().st_size / 1024 / 1024
                st.markdown(f"- {b.name} ({size_mb:.1f} MB)")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Логи
    with tabs[4]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📈 Системные логи")
        
        # Загружаем логи за сегодня
        log_file = Path(LOGS_DIR) / f"log_{date.today().isoformat()}.json"
        
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
            
            logs_df = pd.DataFrame(logs)
            if not logs_df.empty:
                st.dataframe(
                    logs_df[["timestamp", "user", "action", "details"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("😕 Логи пусты")
        else:
            st.info("😕 Нет логов за сегодня")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Настройки
    with tabs[5]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("⚙️ Настройки системы")
        
        with st.form("system_settings"):
            st.markdown("### 🔐 Безопасность")
            session_timeout = st.number_input(
                "Таймаут сессии (минут)",
                min_value=5,
                max_value=120,
                value=30
            )
            
            max_login_attempts = st.number_input(
                "Максимум попыток входа",
                min_value=3,
                max_value=10,
                value=5
            )
            
            st.markdown("### 📁 Хранение")
            max_file_size = st.number_input(
                "Макс. размер файла (MB)",
                min_value=1,
                max_value=50,
                value=10
            )
            
            st.markdown("### 🔔 Уведомления")
            email_notifications = st.checkbox("Email уведомления", value=True)
            telegram_notifications = st.checkbox("Telegram уведомления", value=False)
            
            if st.form_submit_button("💾 Сохранить настройки", use_container_width=True):
                st.toast("✅ Настройки сохранены!")
                log_action("SETTINGS_CHANGED", st.session_state.user, "Изменены настройки системы")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ===================== ОПАСНАЯ ЗОНА ДЛЯ АДМИНА =====================
if st.session_state.role == "admin":
    st.divider()
    
    with st.expander("☢️ ОПАСНАЯ ЗОНА", expanded=False):
        st.warning("⚠️ Эти действия необратимы!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🗑 Очистка таблицы")
            table_to_clear = st.selectbox(
                "Выберите таблицу для очистки",
                ["purchases", "stock", "orders"],
                key="clear_table"
            )
            
            if st.button(f"🗑 ОЧИСТИТЬ {table_to_clear}", type="primary", use_container_width=True):
                confirm = st.text_input("Введите 'DELETE' для подтверждения")
                if confirm == "DELETE":
                    if delete_all_from_table(table_to_clear):
                        st.session_state.data = load_all_data()
                        log_action("ADMIN_DELETE_TABLE", st.session_state.user, f"Очищена таблица {table_to_clear}")
                        st.toast(f"✅ Таблица {table_to_clear} очищена!")
                        st.rerun()
        
        with col2:
            st.subheader("💥 Полное уничтожение")
            st.error("Удалит ВСЕ данные навсегда!")
            
            confirm1 = st.text_input("Введите 'GODMODE'", type="password")
            confirm2 = st.checkbox("Я понимаю, что данные будут удалены навсегда")
            
            if st.button("☢️ УНИЧТОЖИТЬ ВСЁ", type="primary", use_container_width=True):
                if confirm1 == "GODMODE" and confirm2:
                    # Удаляем все таблицы
                    for t in ["purchases", "stock", "orders"]:
                        delete_all_from_table(t)
                    
                    # Удаляем файлы
                    if os.path.exists(PHOTO_DIR):
                        shutil.rmtree(PHOTO_DIR)
                        os.makedirs(PHOTO_DIR)
                    
                    # Удаляем логи
                    if os.path.exists(LOGS_DIR):
                        shutil.rmtree(LOGS_DIR)
                        os.makedirs(LOGS_DIR)
                    
                    st.session_state.data = load_all_data()
                    log_action("ADMIN_NUKE", st.session_state.user, "ПОЛНОЕ УНИЧТОЖЕНИЕ БАЗЫ")
                    
                    st.toast("💥 ВСЕ ДАННЫЕ УНИЧТОЖЕНЫ!")
                    time.sleep(2)
                    st.rerun()

# ===================== ФУТЕР =====================
st.markdown("""
<div style="text-align: center; padding: 50px 0 20px; color: #666;">
    <hr style="margin: 20px 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, #667eea, transparent);">
    <p>© 2026 КДЛ OLYMPUS • Умная система управления лабораторией</p>
    <p style="font-size: 0.9rem;">Версия 2.0 • Все права защищены</p>
</div>
""", unsafe_allow_html=True)
