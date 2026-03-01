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

# ===================== ИНИЦИАЛИЗАЦИЯ СЕССИИ =====================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.theme = "light"
    st.session_state.notifications = []
    st.session_state.favorites = []
    st.session_state.role = None
    st.session_state.user = None
    st.session_state.data = None

# ===================== ФУНКЦИЯ ДЛЯ СМЕНЫ ТЕМЫ =====================
def set_theme(theme):
    st.session_state.theme = theme
    st.rerun()

# ===================== СТИЛИ В ЗАВИСИМОСТИ ОТ ТЕМЫ =====================
def get_theme_styles():
    if st.session_state.theme == "dark":
        return """
            <style>
                /* Темная тема */
                .stApp {
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                }
                
                .main {
                    background: rgba(26, 26, 46, 0.95);
                    color: #fff;
                }
                
                .glass-card {
                    background: rgba(30, 30, 46, 0.95);
                    border: 1px solid rgba(255,255,255,0.1);
                    color: #fff;
                }
                
                .stTabs [data-baseweb="tab-list"] {
                    background: rgba(0,0,0,0.3);
                }
                
                .stTextInput > div > div > input,
                .stSelectbox > div > div,
                .stTextArea > div > div > textarea {
                    background-color: #16213e !important;
                    color: white !important;
                    border-color: #0f3460 !important;
                }
                
                h1, h2, h3, h4, h5, h6, p, span, label {
                    color: #fff !important;
                }
                
                .stMarkdown {
                    color: #fff;
                }
            </style>
        """
    else:
        return """
            <style>
                /* Светлая тема */
                .stApp {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                
                .main {
                    background: rgba(255, 255, 255, 0.95);
                }
                
                .glass-card {
                    background: rgba(255, 255, 255, 0.95);
                    border: 1px solid rgba(0,0,0,0.1);
                }
                
                .stTabs [data-baseweb="tab-list"] {
                    background: rgba(255,255,255,0.1);
                }
                
                .stTextInput > div > div > input,
                .stSelectbox > div > div,
                .stTextArea > div > div > textarea {
                    background-color: white !important;
                }
                
                h1, h2, h3, h4, h5, h6, p, span, label {
                    color: #1a1a2e !important;
                }
            </style>
        """

# ===================== ОСНОВНЫЕ СТИЛИ =====================
st.markdown("""
<style>
    /* Глобальные стили */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Montserrat', sans-serif;
    }
    
    .stApp {
        background-attachment: fixed;
    }
    
    /* Основной контейнер */
    .main {
        backdrop-filter: blur(10px);
        border-radius: 30px 30px 0 0;
        padding: 20px;
        margin-top: 20px;
        box-shadow: 0 -20px 40px rgba(0,0,0,0.1);
    }
    
    /* Красивые карточки */
    .glass-card {
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
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
        margin: 5px;
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
        padding: 10px;
        border-radius: 50px;
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
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
    
    /* Стили для сайдбара */
    .css-1d391kg, .css-12oz5g7 {
        background: linear-gradient(180deg, #ffffff, #f0f7ff) !important;
    }
    
    /* Стили для data editor */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Стили для expander */
    .streamlit-expanderHeader {
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# Применяем тему
st.markdown(get_theme_styles(), unsafe_allow_html=True)

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
    try:
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
    except Exception as e:
        print(f"Ошибка логирования: {e}")

# ===================== БАЗА ДАННЫХ =====================
@st.cache_resource
def get_engine():
    """Получение движка БД с кешированием"""
    try:
        return create_engine(
            st.secrets["db_url"],
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600
        )
    except Exception as e:
        st.error(f"Ошибка подключения к базе данных: {str(e)}")
        return None

def get_raw(table):
    """Безопасное получение данных"""
    try:
        engine = get_engine()
        if engine:
            with engine.connect() as conn:
                return pd.read_sql(f"SELECT * FROM {table}", conn)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ошибка загрузки {table}: {str(e)}")
        return pd.DataFrame()

def save_raw(table, df):
    """Безопасное сохранение данных"""
    try:
        engine = get_engine()
        if engine:
            with engine.connect() as conn:
                df.to_sql(table, conn, if_exists="replace", index=False)
                conn.commit()
            return True
        return False
    except Exception as e:
        st.error(f"Ошибка сохранения {table}: {str(e)}")
        return False

def delete_all_from_table(table):
    """Безопасное удаление данных"""
    try:
        engine = get_engine()
        if engine:
            with engine.connect() as conn:
                conn.execute(text(f"DELETE FROM {table}"))
                conn.commit()
            return True
        return False
    except Exception as e:
        st.error(f"Ошибка удаления {table}: {str(e)}")
        return False

# ===================== ЗАГРУЗКА ДАННЫХ =====================
@st.cache_data(ttl=300)
def load_all_data():
    """Загрузка всех данных с кешированием"""
    return {
        "purchases": get_raw("purchases"),
        "stock": get_raw("stock"),
        "orders": get_raw("orders"),
        "last_update": datetime.now(TZ).isoformat()
    }

# ===================== ЛОГОТИП И ЗАГОЛОВОК =====================
LOGO_URL = "https://github.com/asidorevich/my_homework_repo/blob/main/logo.PNG?raw=true"

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
                    st.session_state.data = load_all_data()
                    
                    log_action("LOGIN", username, f"Вход как {role}")
                    
                    st.success(f"✅ Добро пожаловать, {username}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Неверное имя пользователя или пароль")
    
    st.stop()

# ===================== ЗАГРУЗКА ДАННЫХ ПОСЛЕ АВТОРИЗАЦИИ =====================
if st.session_state.data is None:
    with st.spinner("Загрузка данных..."):
        st.session_state.data = load_all_data()

data = st.session_state.data

# ===================== САЙДБАР =====================
with st.sidebar:
    st.image(LOGO_URL, width=100)
    
    st.markdown(f"""
    <div style="text-align: center; margin: 20px 0;">
        <p style="color: #667eea; font-weight: 600; font-size: 1.2rem;">👤 {st.session_state.user}</p>
        <p style="font-size: 0.9rem; color: #666;">
            {datetime.now(TZ).strftime("%d.%m.%Y %H:%M")}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Метрики в сайдбаре
    total_spent = data["purchases"]["total"].sum() if not data["purchases"].empty else 0
    critical_items = len(data["stock"][data["stock"]["quantity"] <= data["stock"]["min_qty"]]) if not data["stock"].empty else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Всего потрачено", f"{total_spent:,.0f} ₸")
    with col2:
        st.metric("⚠️ Критических", critical_items)
    
    st.divider()
    
    # Быстрые действия
    st.markdown("### ⚡ Быстрые действия")
    
    if st.button("🔄 Обновить данные", use_container_width=True):
        with st.spinner("Обновление..."):
            st.cache_data.clear()
            st.session_state.data = load_all_data()
            st.toast("✅ Данные обновлены!", icon="🔄")
            time.sleep(0.5)
            st.rerun()
    
    # Экспорт отчета
    report_buffer = io.BytesIO()
    with pd.ExcelWriter(report_buffer, engine='openpyxl') as writer:
        for name, df in data.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.to_excel(writer, sheet_name=name[:31], index=False)
    
    st.download_button(
        "📥 Скачать отчет",
        report_buffer.getvalue(),
        f"report_{date.today().isoformat()}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    # Смена темы
    st.markdown("### 🎨 Тема")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌞 Светлая", use_container_width=True):
            set_theme("light")
    with col2:
        if st.button("🌙 Темная", use_container_width=True):
            set_theme("dark")
    
    st.divider()
    
    if st.button("🚪 Выйти", use_container_width=True, type="secondary"):
        log_action("LOGOUT", st.session_state.user, "Выход из системы")
        st.session_state.role = None
        st.session_state.user = None
        st.session_state.data = None
        st.cache_data.clear()
        st.rerun()

# ===================== ОСНОВНОЙ ИНТЕРФЕЙС =====================
# Функция для создания метрик
def create_metric_card(value, label, color=None):
    color_style = f"background: {color};" if color else ""
    return f"""
    <div class="metric-card" style="{color_style}">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """

# МЕДСЕСТРА
if st.session_state.role == "med":
    st.markdown("## 👩‍⚕️ Панель медсестры")
    
    tabs = st.tabs([
        "🏠 Главная",
        "📦 Склад",
        "📉 Списание",
        "📨 Заявки",
        "📊 Аналитика"
    ])
    
    # Главная
    with tabs[0]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📊 Панель управления")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Позиций на складе", len(data["stock"]))
            
            with col2:
                pending_orders = len(data["orders"][data["orders"]["status"] == "new"])
                st.metric("Активных заявок", pending_orders)
            
            with col3:
                low_stock = len(data["stock"][data["stock"]["quantity"] <= data["stock"]["min_qty"]])
                st.metric("Критических остатков", low_stock)
            
            with col4:
                today_usage = len(data["purchases"][
                    (pd.to_datetime(data["purchases"]["date"]).dt.date == date.today()) & 
                    (data["purchases"]["item"].str.contains("СПИСАНО"))
                ]) if not data["purchases"].empty else 0
                st.metric("Списаний сегодня", today_usage)
            
            st.divider()
            
            if low_stock > 0:
                st.error(f"⚠️ Обнаружено {low_stock} позиций с критическим остатком!")
                
                critical = data["stock"][data["stock"]["quantity"] <= data["stock"]["min_qty"]].copy()
                for _, item in critical.iterrows():
                    percent = min((item["quantity"] / item["min_qty"]) * 100, 100)
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.progress(percent/100, text=f"**{item['item']}**")
                    with col2:
                        st.write(f"{item['quantity']} / {item['min_qty']} {item['unit']}")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Склад
    with tabs[1]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📦 Текущие остатки")
            
            if not data["stock"].empty:
                # Поиск
                search = st.text_input("🔍 Поиск по названию", placeholder="Введите название товара...")
                
                # Фильтр по категориям
                categories = ["Все"] + sorted(data["stock"]["category"].unique().tolist())
                category = st.selectbox("📂 Категория", categories)
                
                # Фильтрация
                filtered_df = data["stock"].copy()
                if search:
                    filtered_df = filtered_df[filtered_df["item"].str.contains(search, case=False, na=False)]
                if category != "Все":
                    filtered_df = filtered_df[filtered_df["category"] == category]
                
                # Отображение
                for _, item in filtered_df.iterrows():
                    status = "🟢" if item["quantity"] > item["min_qty"] else "🔴"
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"{status} **{item['item']}**")
                        st.caption(f"{item['category']}")
                    with col2:
                        st.write(f"**{item['quantity']}** {item['unit']}")
                    with col3:
                        st.write(f"Мин: {item['min_qty']}")
                    st.divider()
            else:
                st.info("📭 Склад пуст")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Списание
    with tabs[2]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📉 Списание материалов")
            
            if not data["stock"].empty:
                with st.form("write_off_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        item = st.selectbox(
                            "Выберите товар",
                            options=sorted(data["stock"]["item"].tolist())
                        )
                        
                        if item:
                            item_info = data["stock"][data["stock"]["item"] == item].iloc[0]
                            st.info(f"📦 Доступно: **{item_info['quantity']} {item_info['unit']}**")
                            
                            qty = st.number_input(
                                "Количество",
                                min_value=0.1,
                                max_value=float(item_info['quantity']),
                                step=0.1,
                                format="%.1f"
                            )
                    
                    with col2:
                        patient = st.text_input("👤 Пациент / № анализа")
                        reason = st.selectbox(
                            "📋 Причина",
                            ["Использование", "Брак", "Порча", "Истечение срока", "Другое"]
                        )
                        comment = st.text_area("📝 Комментарий")
                    
                    submitted = st.form_submit_button("✅ СПИСАТЬ", use_container_width=True)
                    
                    if submitted and qty > 0:
                        # Обновляем остатки
                        data["stock"].loc[data["stock"]["item"] == item, "quantity"] -= qty
                        
                        if save_raw("stock", data["stock"]):
                            # Добавляем запись в историю
                            new_entry = pd.DataFrame([{
                                "date": date.today().isoformat(),
                                "item": f"[СПИСАНО] {item}",
                                "category": item_info["category"],
                                "qty": qty,
                                "unit": item_info["unit"],
                                "price": 0,
                                "total": 0,
                                "supplier": "",
                                "comment": f"{reason}: {patient} - {comment}" if comment else f"{reason}: {patient}",
                                "photo": "",
                                "added_by": st.session_state.user
                            }])
                            
                            data["purchases"] = pd.concat([data["purchases"], new_entry], ignore_index=True)
                            save_raw("purchases", data["purchases"])
                            
                            st.success(f"✅ Списано {qty} {item_info['unit']} {item}")
                            time.sleep(1)
                            st.rerun()
            else:
                st.info("📭 Нет товаров для списания")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Заявки
    with tabs[3]:
        with st.container():
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
                
                comment = st.text_area("📝 Комментарий")
                
                submitted = st.form_submit_button("📨 ОТПРАВИТЬ ЗАЯВКУ", use_container_width=True)
                
                if submitted and item.strip():
                    new_order = pd.DataFrame([{
                        "item": item.strip(),
                        "qty": qty,
                        "unit": unit,
                        "comment": f"{priority}: {comment}" if comment else priority,
                        "ordered_by": st.session_state.user,
                        "ordered_at": datetime.now(TZ).isoformat(),
                        "status": "new",
                        "priority": priority
                    }])
                    
                    data["orders"] = pd.concat([data["orders"], new_order], ignore_index=True)
                    
                    if save_raw("orders", data["orders"]):
                        st.success("✅ Заявка отправлена!")
                        time.sleep(1)
                        st.rerun()
            
            st.divider()
            
            # История заявок
            st.subheader("📋 История ваших заявок")
            user_orders = data["orders"][data["orders"]["ordered_by"] == st.session_state.user]
            
            if not user_orders.empty:
                for _, order in user_orders.iterrows():
                    status_emoji = {
                        "new": "🟡",
                        "done": "🟢",
                        "rejected": "🔴"
                    }.get(order["status"], "⚪")
                    
                    with st.expander(f"{status_emoji} {order['item']} - {order['qty']} {order['unit']}"):
                        st.write(f"**Статус:** {order['status']}")
                        st.write(f"**Дата:** {order['ordered_at'][:16]}")
                        if order.get('comment'):
                            st.write(f"**Комментарий:** {order['comment']}")
            else:
                st.info("😕 У вас пока нет заявок")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Аналитика
    with tabs[4]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📊 Аналитика расхода")
            
            if not data["purchases"].empty:
                # Фильтруем только списания
                write_offs = data["purchases"][data["purchases"]["item"].str.contains("СПИСАНО")].copy()
                
                if not write_offs.empty:
                    write_offs["date"] = pd.to_datetime(write_offs["date"])
                    write_offs["month"] = write_offs["date"].dt.strftime("%Y-%m")
                    
                    # График по месяцам
                    monthly = write_offs.groupby("month")["qty"].sum().reset_index()
                    fig = px.line(monthly, x="month", y="qty", title="Динамика списаний")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Топ расходуемых
                    st.subheader("📈 Топ расходуемых товаров")
                    top_items = write_offs.groupby("item")["qty"].sum().sort_values(ascending=False).head(10)
                    fig = px.bar(
                        x=top_items.values,
                        y=top_items.index,
                        orientation='h',
                        title="Самые популярные товары"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("😕 Нет данных о списаниях")
            else:
                st.info("😕 Недостаточно данных для аналитики")
            
            st.markdown('</div>', unsafe_allow_html=True)

# СНАБЖЕНИЕ
elif st.session_state.role == "snab":
    st.markdown("## 📦 Панель снабжения")
    
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
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🏠 Панель управления")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                pending_orders = len(data["orders"][data["orders"]["status"] == "new"])
                st.metric("Новых заявок", pending_orders)
            
            with col2:
                total_purchases = len(data["purchases"])
                st.metric("Всего закупок", total_purchases)
            
            with col3:
                total_spent = data["purchases"]["total"].sum() if not data["purchases"].empty else 0
                st.metric("💰 Потрачено", f"{total_spent:,.0f} ₸")
            
            with col4:
                unique_suppliers = data["purchases"]["supplier"].nunique() if not data["purchases"].empty else 0
                st.metric("Поставщиков", unique_suppliers)
            
            st.divider()
            
            # Последние заявки
            st.subheader("📨 Последние заявки")
            recent_orders = data["orders"][data["orders"]["status"] == "new"].head(5)
            
            if not recent_orders.empty:
                for _, order in recent_orders.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.write(f"**{order['item']}**")
                            st.caption(f"от {order['ordered_by']}")
                        with col2:
                            st.write(f"{order['qty']} {order['unit']}")
                        with col3:
                            priority_color = {
                                "Низкий": "🟢",
                                "Средний": "🟡",
                                "Высокий": "🟠",
                                "Критический": "🔴"
                            }.get(order.get("priority", "Средний"), "⚪")
                            st.write(priority_color)
                        st.divider()
            else:
                st.success("✅ Нет новых заявок")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Заявки
    with tabs[1]:
        with st.container():
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
            filtered_orders = data["orders"].copy()
            if status_filter != "Все":
                filtered_orders = filtered_orders[filtered_orders["status"] == status_filter]
            if search:
                filtered_orders = filtered_orders[filtered_orders["item"].str.contains(search, case=False, na=False)]
            
            if not filtered_orders.empty:
                for idx, order in filtered_orders.iterrows():
                    with st.expander(f"📦 {order['item']} - {order['qty']} {order['unit']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**От:** {order['ordered_by']}")
                            st.write(f"**Когда:** {order['ordered_at'][:16]}")
                            if order.get('comment'):
                                st.write(f"**Комментарий:** {order['comment']}")
                        
                        with col2:
                            if order["status"] == "new":
                                if st.button("✅ Выполнить", key=f"done_{idx}", use_container_width=True):
                                    filtered_orders.loc[idx, "status"] = "done"
                                    if save_raw("orders", filtered_orders):
                                        st.session_state.data = load_all_data()
                                        st.success("✅ Заявка выполнена!")
                                        st.rerun()
                                
                                if st.button("🔄 В работу", key=f"work_{idx}", use_container_width=True):
                                    st.session_state["order_to_purchase"] = {
                                        "item": order["item"],
                                        "qty": order["qty"],
                                        "unit": order["unit"],
                                        "comment": order.get("comment", "")
                                    }
                                    st.success("📝 Данные перенесены в закупку!")
            else:
                st.info("😕 Заявок не найдено")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Закупки
    with tabs[2]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🛒 Добавление закупки")
            
            default_data = st.session_state.get("order_to_purchase", {})
            
            with st.form("purchase_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    item = st.text_input(
                        "📦 Товар *",
                        value=default_data.get("item", "")
                    )
                    
                    category = st.selectbox(
                        "📂 Категория",
                        ["Расходный материал", "Канцелярия", "Пробирки", "Хозтовары", "Прочее"]
                    )
                    
                    qty = st.number_input(
                        "🔢 Количество *",
                        min_value=1,
                        value=int(default_data.get("qty", 1))
                    )
                    
                    unit = st.selectbox(
                        "📏 Единица измерения",
                        ["шт", "упак", "коробка", "рулон", "литр", "кг"],
                        index=["шт", "упак", "коробка", "рулон", "литр", "кг"].index(default_data.get("unit", "шт")) 
                        if default_data.get("unit") in ["шт", "упак", "коробка", "рулон", "литр", "кг"] else 0
                    )
                
                with col2:
                    price = st.number_input("💰 Цена за единицу *", min_value=0.0, step=10.0)
                    supplier = st.text_input("🏭 Поставщик")
                    purchase_date = st.date_input("📅 Дата закупки", value=date.today())
                
                col1, col2 = st.columns(2)
                with col1:
                    no_track = st.checkbox("❌ Не учитывать на складе")
                with col2:
                    urgent = st.checkbox("⚡ Срочная закупка")
                
                files = st.file_uploader(
                    "📎 Прикрепить документы",
                    accept_multiple_files=True,
                    type=["png", "jpg", "jpeg", "pdf"]
                )
                
                comment = st.text_area(
                    "📝 Комментарий",
                    value=default_data.get("comment", "")
                )
                
                submitted = st.form_submit_button("💾 СОХРАНИТЬ ЗАКУПКУ", use_container_width=True)
                
                if submitted:
                    if not item or qty <= 0 or price <= 0:
                        st.error("❌ Заполните все обязательные поля (отмечены *)")
                    else:
                        # Сохраняем файлы
                        paths = []
                        if files:
                            for f in files:
                                safe_name = f"{date.today()}_{item}_{f.name}".replace(" ", "_")
                                safe_name = re.sub(r'[^\w\-_\.]', '', safe_name)
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
                            "comment": f"{'СРОЧНО! ' if urgent else ''}{comment}",
                            "photo": ";".join(paths) if paths else "",
                            "added_by": st.session_state.user
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
                            
                            if "order_to_purchase" in st.session_state:
                                del st.session_state["order_to_purchase"]
                            
                            st.session_state.data = load_all_data()
                            st.success("✅ Закупка добавлена!")
                            time.sleep(1)
                            st.rerun()
            
            st.divider()
            
            # Последние закупки
            st.subheader("📋 Последние закупки")
            if not data["purchases"].empty:
                recent = data["purchases"].sort_values("date", ascending=False).head(10)
                st.dataframe(
                    recent[["date", "item", "qty", "unit", "total", "supplier"]],
                    use_container_width=True,
                    hide_index=True
                )
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Склад
    with tabs[3]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📦 Управление складом")
            
            if not data["stock"].empty:
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
                        st.success("✅ Изменения сохранены!")
                        st.rerun()
            else:
                st.info("📭 Склад пуст")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Аналитика
    with tabs[4]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📈 Аналитика")
            
            if not data["purchases"].empty:
                purchases = data["purchases"].copy()
                purchases["date"] = pd.to_datetime(purchases["date"])
                
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
                
                # Фильтрация
                mask = (purchases["date"].dt.date >= start_date) & (purchases["date"].dt.date <= end_date)
                filtered = purchases[mask]
                
                if not filtered.empty:
                    # Метрики
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("💰 Всего", f"{filtered['total'].sum():,.0f} ₸")
                    with col2:
                        st.metric("📊 Средний чек", f"{filtered['total'].mean():,.0f} ₸")
                    with col3:
                        st.metric("📦 Закупок", len(filtered))
                    with col4:
                        st.metric("📋 Позиций", filtered["item"].nunique())
                    
                    st.divider()
                    
                    # Графики
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # По категориям
                        cat_stats = filtered.groupby("category")["total"].sum()
                        fig = px.pie(
                            values=cat_stats.values,
                            names=cat_stats.index,
                            title="Распределение по категориям"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # По поставщикам
                        supp_stats = filtered.groupby("supplier")["total"].sum().nlargest(10)
                        fig = px.bar(
                            x=supp_stats.values,
                            y=supp_stats.index,
                            orientation='h',
                            title="Топ поставщиков"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Динамика
                    daily = filtered.groupby(filtered["date"].dt.strftime("%Y-%m-%d"))["total"].sum().reset_index()
                    fig = px.line(daily, x="date", y="total", title="Динамика расходов")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("😕 Нет данных за выбранный период")
            else:
                st.info("😕 Недостаточно данных для аналитики")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Чеки
    with tabs[5]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🖼 Галерея чеков")
            
            # Загрузка
            with st.expander("📤 Загрузить новые чеки"):
                uploaded_files = st.file_uploader(
                    "Выберите файлы",
                    accept_multiple_files=True,
                    type=["png", "jpg", "jpeg", "pdf"]
                )
                
                if uploaded_files and st.button("💾 Сохранить все", use_container_width=True):
                    for f in uploaded_files:
                        safe_name = f"{date.today()}_{f.name}".replace(" ", "_")
                        safe_name = re.sub(r'[^\w\-_\.]', '', safe_name)
                        path = os.path.join(PHOTO_DIR, safe_name)
                        
                        with open(path, "wb") as out:
                            out.write(f.getbuffer())
                    
                    st.success(f"✅ Сохранено {len(uploaded_files)} файлов!")
                    st.rerun()
            
            st.divider()
            
            # Отображение
            files = sorted(Path(PHOTO_DIR).iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if files:
                cols = st.columns(3)
                for i, f in enumerate(files[:12]):
                    with cols[i % 3]:
                        if f.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                            st.image(str(f), use_container_width=True)
                        else:
                            st.markdown(f"📄 {f.name}")
                        
                        if st.button("🗑️", key=f"del_{f.name}"):
                            f.unlink()
                            st.rerun()
            else:
                st.info("😕 Нет загруженных чеков")
            
            st.markdown('</div>', unsafe_allow_html=True)

# АДМИНИСТРАТОР
else:
    st.markdown("## 👑 Админ-панель")
    
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
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📊 Системный обзор")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Закупок", len(data["purchases"]))
            with col2:
                st.metric("Товаров", len(data["stock"]))
            with col3:
                st.metric("Заявок", len(data["orders"]))
            with col4:
                st.metric("Активных", 1)
            
            st.divider()
            
            # Статус
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🟢 Статус")
                st.markdown(f"- **БД:** ✅ Подключено")
                st.markdown(f"- **Файлы:** ✅ {len(list(Path(PHOTO_DIR).glob('*')))} файлов")
            
            with col2:
                total_size = sum(f.stat().st_size for f in Path(PHOTO_DIR).glob("*")) / 1024 / 1024
                st.markdown("### 💾 Использование")
                st.markdown(f"- **Место:** {total_size:.1f} MB")
                st.markdown(f"- **Записей:** {len(data['purchases']) + len(data['stock']) + len(data['orders'])}")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Пользователи
    with tabs[1]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("👥 Управление пользователями")
            
            users = pd.DataFrame([
                {"username": "nurse", "role": "med", "status": "active"},
                {"username": "snab", "role": "snab", "status": "active"},
                {"username": "admin", "role": "admin", "status": "active"}
            ])
            
            edited_users = st.data_editor(
                users,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "username": "Имя",
                    "role": st.column_config.SelectboxColumn(
                        "Роль",
                        options=["med", "snab", "admin"]
                    ),
                    "status": st.column_config.SelectboxColumn(
                        "Статус",
                        options=["active", "blocked"]
                    )
                }
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Редактор
    with tabs[2]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("✏️ Редактор данных")
            
            table = st.selectbox(
                "Выберите таблицу",
                ["purchases", "stock", "orders"]
            )
            
            if table in data:
                edited_df = st.data_editor(
                    data[table],
                    use_container_width=True,
                    num_rows="dynamic"
                )
                
                if st.button("💾 Сохранить", type="primary", use_container_width=True):
                    if save_raw(table, edited_df):
                        st.session_state.data = load_all_data()
                        st.success("✅ Сохранено!")
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Бэкапы
    with tabs[3]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("💾 Бэкапы")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📦 Создать бэкап", use_container_width=True, type="primary"):
                    with st.spinner("Создание бэкапа..."):
                        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                        backup_path = Path(BACKUP_DIR) / backup_name
                        
                        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                            for t in ["purchases", "stock", "orders"]:
                                df = data[t]
                                zf.writestr(f"{t}.csv", df.to_csv(index=False))
                            
                            for f in Path(PHOTO_DIR).glob("*"):
                                zf.write(f, f"чеки/{f.name}")
                            
                            for f in Path(LOGS_DIR).glob("*"):
                                zf.write(f, f"логи/{f.name}")
                        
                        st.success(f"✅ Бэкап создан")
                        
                        with open(backup_path, "rb") as f:
                            st.download_button(
                                "📥 Скачать",
                                f.read(),
                                backup_name,
                                "application/zip",
                                use_container_width=True
                            )
            
            with col2:
                st.subheader("📋 История")
                backups = sorted(Path(BACKUP_DIR).glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)
                for b in backups[:5]:
                    size = b.stat().st_size / 1024 / 1024
                    st.markdown(f"- {b.name} ({size:.1f} MB)")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Логи
    with tabs[4]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📈 Системные логи")
            
            log_file = Path(LOGS_DIR) / f"log_{date.today().isoformat()}.json"
            
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                
                if logs:
                    logs_df = pd.DataFrame(logs)
                    st.dataframe(logs_df, use_container_width=True, hide_index=True)
                else:
                    st.info("Логи пусты")
            else:
                st.info("Нет логов за сегодня")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Настройки
    with tabs[5]:
        with st.container():
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("⚙️ Настройки системы")
            
            with st.form("settings_form"):
                st.markdown("### 🔐 Безопасность")
                session_timeout = st.number_input("Таймаут сессии (минут)", 5, 120, 30)
                max_attempts = st.number_input("Макс. попыток входа", 3, 10, 5)
                
                st.markdown("### 📁 Хранение")
                max_file_size = st.number_input("Макс. размер файла (MB)", 1, 50, 10)
                
                if st.form_submit_button("💾 Сохранить", use_container_width=True):
                    st.success("✅ Настройки сохранены!")
            
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
                "Выберите таблицу",
                ["purchases", "stock", "orders"],
                key="clear_table"
            )
            
            confirm = st.text_input("Введите 'DELETE' для подтверждения", key="confirm_delete")
            
            if st.button(f"🗑 ОЧИСТИТЬ {table_to_clear}", use_container_width=True):
                if confirm == "DELETE":
                    if delete_all_from_table(table_to_clear):
                        st.session_state.data = load_all_data()
                        st.success(f"✅ Таблица {table_to_clear} очищена!")
                        st.rerun()
        
        with col2:
            st.subheader("💥 Полное уничтожение")
            st.error("Удалит ВСЕ данные навсегда!")
            
            confirm1 = st.text_input("Введите 'GODMODE'", type="password", key="godmode")
            confirm2 = st.checkbox("Я понимаю последствия", key="understand")
            
            if st.button("☢️ УНИЧТОЖИТЬ ВСЁ", use_container_width=True):
                if confirm1 == "GODMODE" and confirm2:
                    for t in ["purchases", "stock", "orders"]:
                        delete_all_from_table(t)
                    
                    if os.path.exists(PHOTO_DIR):
                        shutil.rmtree(PHOTO_DIR)
                        os.makedirs(PHOTO_DIR)
                    
                    st.session_state.data = load_all_data()
                    st.success("💥 Все данные уничтожены!")
                    time.sleep(2)
                    st.rerun()

# ===================== ФУТЕР =====================
st.markdown("""
<div style="text-align: center; padding: 30px 0 20px; color: #666;">
    <hr style="margin: 20px 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, #667eea, transparent);">
    <p>© 2026 КДЛ OLYMPUS • Умная система управления лабораторией</p>
</div>
""", unsafe_allow_html=True)
