import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
from pathlib import Path
import zipfile
import io
import shutil
import sqlalchemy as sa
from sqlalchemy import create_engine, text
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any
import hashlib
import json

# ===================== КОНФИГ =====================
st.set_page_config(
    page_title="OLYMPUS 2026",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

PHOTO_DIR = "чеки"
os.makedirs(PHOTO_DIR, exist_ok=True)

# ===================== РАСШИРЕННЫЙ CSS С АНИМАЦИЯМИ =====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700;900&display=swap');
    
    * {
        font-family: 'Montserrat', sans-serif;
    }
    
    .main, .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #1a2a44;
    }
    
    /* Стеклянный эффект для карточек */
    .glass-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        transition: transform 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 30px 60px rgba(0,0,0,0.15);
    }
    
    /* Улучшенные табы */
    div[data-testid="stTabs"] > div[role="tablist"] {
        gap: 15px !important;
        justify-content: center;
        flex-wrap: wrap;
        background: rgba(255,255,255,0.1);
        padding: 15px;
        border-radius: 50px;
        backdrop-filter: blur(10px);
    }
    
    div[data-testid="stTabs"] button {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        padding: 12px 28px !important;
        border-radius: 40px !important;
        border: none !important;
        background: rgba(255,255,255,0.2) !important;
        color: white !important;
        transition: all 0.3s ease;
    }
    
    div[data-testid="stTabs"] button:hover {
        background: rgba(255,255,255,0.3) !important;
        transform: scale(1.05);
    }
    
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background: linear-gradient(45deg, #ff8c42, #ff6b6b) !important;
        box-shadow: 0 10px 20px rgba(255,140,66,0.3) !important;
    }
    
    /* Анимированные кнопки */
    .stButton > button {
        background: linear-gradient(45deg, #ff8c42, #ff6b6b) !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 10px 20px rgba(255,140,66,0.2) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 15px 30px rgba(255,140,66,0.4) !important;
    }
    
    /* Метрики */
    .metric-container {
        background: white;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        border-left: 5px solid #ff8c42;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 900;
        background: linear-gradient(45deg, #ff8c42, #ff6b6b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 10px 0;
    }
    
    .metric-label {
        color: #64748b;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Прогресс-бар */
    .progress-container {
        background: #e0e0e0;
        border-radius: 10px;
        height: 10px;
        overflow: hidden;
        margin: 10px 0;
    }
    
    .progress-bar {
        height: 100%;
        background: linear-gradient(45deg, #ff8c42, #ff6b6b);
        transition: width 0.5s ease;
    }
    
    /* Адаптация для мобильных */
    @media (max-width: 768px) {
        div[data-testid="stTabs"] button {
            font-size: 1rem !important;
            padding: 8px 16px !important;
        }
        
        .metric-value {
            font-size: 1.8rem;
        }
    }
    
    /* Уведомления */
    .custom-toast {
        position: fixed;
        top: 20px;
        right: 20px;
        background: white;
        border-radius: 10px;
        padding: 15px 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease;
        z-index: 9999;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    /* Лоадер */
    .custom-loader {
        border: 5px solid #f3f3f3;
        border-top: 5px solid #ff8c42;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        animation: spin 1s linear infinite;
        margin: 20px auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
</style>
""", unsafe_allow_html=True)

# ===================== БАЗА ДАННЫХ С УЛУЧШЕНИЯМИ =====================
@st.cache_resource
def get_engine():
    """Получение подключения к БД с кэшированием"""
    try:
        return create_engine(
            st.secrets["db_url"],
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        return None

def get_raw(table: str) -> pd.DataFrame:
    """Безопасное получение данных из таблицы"""
    try:
        engine = get_engine()
        if engine is None:
            return pd.DataFrame()
        with engine.connect() as conn:
            return pd.read_sql(f"SELECT * FROM {table}", conn)
    except Exception as e:
        st.error(f"Ошибка загрузки {table}: {e}")
        return pd.DataFrame()

def save_raw(table: str, df: pd.DataFrame) -> bool:
    """Безопасное сохранение данных с валидацией"""
    try:
        engine = get_engine()
        if engine is None:
            return False
        with engine.connect() as conn:
            df.to_sql(table, conn, if_exists="replace", index=False)
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения {table}: {e}")
        return False

def delete_all_from_table(table: str) -> bool:
    """Безопасное удаление всех записей из таблицы"""
    try:
        engine = get_engine()
        if engine is None:
            return False
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM {table}"))
            conn.commit()
        return True
    except Exception as e:
        st.error(f"Ошибка очистки {table}: {e}")
        return False

# ===================== МЕНЕДЖЕР СОСТОЯНИЯ =====================
class StateManager:
    """Управление состоянием приложения"""
    
    @staticmethod
    def init_state():
        """Инициализация состояния"""
        if "data" not in st.session_state:
            st.session_state.data = {
                "purchases": pd.DataFrame(),
                "stock": pd.DataFrame(),
                "orders": pd.DataFrame()
            }
        if "role" not in st.session_state:
            st.session_state.role = None
        if "last_update" not in st.session_state:
            st.session_state.last_update = datetime.now()
        if "notifications" not in st.session_state:
            st.session_state.notifications = []
        if "theme" not in st.session_state:
            st.session_state.theme = "light"
        if "favorites" not in st.session_state:
            st.session_state.favorites = []
    
    @staticmethod
    def add_notification(message: str, type: str = "info"):
        """Добавление уведомления"""
        st.session_state.notifications.append({
            "message": message,
            "type": type,
            "time": datetime.now()
        })
        # Ограничиваем количество уведомлений
        if len(st.session_state.notifications) > 10:
            st.session_state.notifications = st.session_state.notifications[-10:]

# Инициализация состояния
StateManager.init_state()

# ===================== ЗАГРУЗКА ДАННЫХ =====================
@st.cache_data(ttl=60)  # Кэширование на 60 секунд
def load_all_data_cached() -> Dict[str, pd.DataFrame]:
    """Загрузка всех данных с кэшированием"""
    return {
        "purchases": get_raw("purchases"),
        "stock": get_raw("stock"),
        "orders": get_raw("orders")
    }

def load_all_data(force: bool = False):
    """Загрузка данных с возможностью принудительного обновления"""
    if force or "data" not in st.session_state:
        st.session_state.data = load_all_data_cached()
        st.session_state.last_update = datetime.now()

load_all_data()
purchases = st.session_state.data["purchases"]
stock = st.session_state.data["stock"]
orders = st.session_state.data["orders"]

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def format_currency(value: float) -> str:
    """Форматирование валюты"""
    return f"{value:,.0f} ₸"

def safe_division(a: float, b: float, default: float = 0) -> float:
    """Безопасное деление"""
    return a / b if b != 0 else default

def validate_data(df: pd.DataFrame, required_columns: list) -> bool:
    """Валидация данных"""
    return all(col in df.columns for col in required_columns)

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_backup() -> Optional[io.BytesIO]:
    """Создание резервной копии"""
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Сохраняем данные
            for table in ["purchases", "stock", "orders"]:
                df = get_raw(table)
                zf.writestr(f"{table}.csv", df.to_csv(index=False))
            
            # Сохраняем метаданные
            metadata = {
                "backup_date": datetime.now().isoformat(),
                "version": "2.0",
                "tables": ["purchases", "stock", "orders"]
            }
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            # Сохраняем чеки
            for file in Path(PHOTO_DIR).glob("*"):
                if file.is_file():
                    zf.write(file, f"чеки/{file.name}")
        
        zip_buffer.seek(0)
        return zip_buffer
    except Exception as e:
        st.error(f"Ошибка создания бэкапа: {e}")
        return None

def restore_from_backup(zip_file) -> bool:
    """Восстановление из резервной копии"""
    try:
        with zipfile.ZipFile(zip_file, "r") as zf:
            # Проверяем метаданные
            if "metadata.json" in zf.namelist():
                metadata = json.loads(zf.read("metadata.json"))
                if metadata.get("version") != "2.0":
                    st.warning("Несовместимая версия бэкапа")
            
            # Восстанавливаем таблицы
            for table in ["purchases", "stock", "orders"]:
                if f"{table}.csv" in zf.namelist():
                    df = pd.read_csv(zf.open(f"{table}.csv"))
                    save_raw(table, df)
            
            # Восстанавливаем чеки
            for file in zf.namelist():
                if file.startswith("чеки/"):
                    file_name = os.path.basename(file)
                    if file_name:
                        with open(os.path.join(PHOTO_DIR, file_name), "wb") as f:
                            f.write(zf.read(file))
        
        return True
    except Exception as e:
        st.error(f"Ошибка восстановления: {e}")
        return False

# ===================== РУССКИЕ ЗАГОЛОВКИ =====================
def rus(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Переименование колонок для отображения"""
    if df.empty:
        return df
    
    maps = {
        "purchases": {
            "rename": {
                "date": "Дата",
                "item": "Товар",
                "category": "Категория",
                "qty": "Кол-во",
                "unit": "Ед.изм",
                "price": "Цена за ед., ₸",
                "total": "Сумма, ₸",
                "supplier": "Поставщик",
                "comment": "Комментарий",
                "photo": "Чек",
                "added_by": "Кем добавлено"
            },
            "order": ["Дата", "Товар", "Категория", "Кол-во", "Ед.изм", 
                     "Цена за ед., ₸", "Сумма, ₸", "Поставщик", "Комментарий", 
                     "Чек", "Кем добавлено"]
        },
        "stock": {
            "rename": {
                "item": "Товар",
                "category": "Категория",
                "unit": "Ед.изм",
                "quantity": "Остаток",
                "min_qty": "Минимум",
                "max_qty": "Максимум",
                "location": "Расположение"
            },
            "order": ["Товар", "Категория", "Ед.изм", "Остаток", "Минимум", 
                     "Максимум", "Расположение"]
        },
        "orders": {
            "rename": {
                "item": "Товар",
                "qty": "Кол-во",
                "unit": "Ед.изм",
                "comment": "Комментарий",
                "ordered_by": "Кем заказано",
                "ordered_at": "Когда",
                "status": "Статус",
                "priority": "Приоритет"
            },
            "order": ["Когда", "Товар", "Кол-во", "Ед.изм", "Комментарий", 
                     "Кем заказано", "Статус", "Приоритет"]
        }
    }
    
    m = maps.get(kind, {"rename": {}, "order": []})
    
    # Переименовываем только существующие колонки
    rename_dict = {k: v for k, v in m["rename"].items() if k in df.columns}
    df = df.rename(columns=rename_dict)
    
    # Выбираем только существующие колонки
    available_cols = [c for c in m["order"] if c in df.columns]
    return df[available_cols]

# ===================== ЛОГО =====================
LOGO_URL = "https://github.com/asidorevich/my_homework_repo/blob/main/logo.PNG?raw=true"

def show_logo():
    """Отображение логотипа"""
    st.markdown(f"""
    <div style="text-align:center; padding:20px 0;">
        <img src="{LOGO_URL}" width="120" style="border-radius:50%; 
             border:4px solid white; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
        <h1 style="font-size:3.5rem; margin:10px 0 0; 
                   background: linear-gradient(45deg, #ff8c42, #ff6b6b);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            OLYMPUS
        </h1>
        <p style="font-size:1.2rem; color:#ff8c42; letter-spacing:3px;">2026</p>
    </div>
    """, unsafe_allow_html=True)

# ===================== АВТОРИЗАЦИЯ =====================
def login_screen():
    """Экран входа"""
    show_logo()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="glass-card">
            <h2 style="text-align:center; color:#ff8c42; margin-bottom:30px;">
                Вход в систему
            </h2>
        """, unsafe_allow_html=True)
        
        role = st.selectbox(
            "Роль",
            ["Медсестра (списание)", "Снабжение (закупки)", "🔐 Администратор"],
            key="login_role"
        )
        
        pwd = st.text_input("Пароль", type="password", key="login_password")
        
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            if st.button("🔑 ВОЙТИ", use_container_width=True, type="primary"):
                # Хеширование паролей (в реальном проекте используйте БД)
                if role == "Медсестра (списание)" and pwd == "med123":
                    st.session_state.role = "med"
                    StateManager.add_notification("Добро пожаловать, медсестра!", "success")
                    st.rerun()
                elif role == "Снабжение (закупки)" and pwd == "olympus2025":
                    st.session_state.role = "snab"
                    StateManager.add_notification("Добро пожаловать, снабжение!", "success")
                    st.rerun()
                elif role == "🔐 Администратор" and pwd == "godmode2026":
                    st.session_state.role = "admin"
                    StateManager.add_notification("Режим администратора активирован", "success")
                    st.rerun()
                else:
                    st.error("❌ Неверный пароль")
        
        st.markdown("</div>", unsafe_allow_html=True)

# ===================== САЙДБАР =====================
def show_sidebar():
    """Отображение боковой панели"""
    with st.sidebar:
        show_logo()
        
        # Метрики
        total = purchases["total"].sum() if not purchases.empty and "total" in purchases.columns else 0
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Всего потрачено</div>
            <div class="metric-value">{format_currency(total)}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Прогресс-бар (пример использования)
        if not stock.empty and "quantity" in stock.columns and "min_qty" in stock.columns:
            critical_count = len(stock[stock["quantity"] <= stock["min_qty"]])
            total_items = len(stock)
            critical_percent = safe_division(critical_count, total_items) * 100
            
            st.markdown(f"""
            <div style="margin-top:20px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span>Критических позиций</span>
                    <span>{critical_count}/{total_items}</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width:{critical_percent}%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Кнопки управления
        if st.button("🔄 Обновить данные", use_container_width=True):
            with st.spinner("Обновление..."):
                load_all_data(force=True)
                StateManager.add_notification("Данные обновлены", "success")
                st.rerun()
        
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.role = None
            st.rerun()
        
        # Информация о последнем обновлении
        st.markdown(f"""
        <div style="text-align:center; margin-top:20px; color:#64748b; font-size:0.8rem;">
            Последнее обновление:<br>
            {st.session_state.last_update.strftime('%H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)
        
        # Уведомления
        if st.session_state.notifications:
            with st.expander("🔔 Уведомления"):
                for notif in reversed(st.session_state.notifications[-5:]):
                    emoji = {
                        "success": "✅",
                        "error": "❌",
                        "warning": "⚠️",
                        "info": "ℹ️"
                    }.get(notif["type"], "📌")
                    st.markdown(f"{emoji} {notif['message']}")

# ===================== МЕДСЕСТРА =====================
def med_interface():
    """Интерфейс медсестры"""
    t1, t2, t3, t4 = st.tabs(["🏠 Дашборд", "📦 Остатки", "📉 Списание", "📨 Заявка"])
    
    with t1:
        st.subheader("📊 Главная панель")
        
        if stock.empty:
            st.info("Нет данных о остатках")
            return
        
        critical = stock[stock["quantity"] <= stock["min_qty"]]
        
        # Метрики
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Критически мало", len(critical))
        with col2:
            st.metric("Всего позиций", len(stock))
        with col3:
            st.metric("Общий остаток", f"{stock['quantity'].sum():,.0f}")
        with col4:
            active_orders = len(orders[orders["status"] == "new"]) if not orders.empty else 0
            st.metric("Активных заявок", active_orders)
        
        # Проблемные позиции
        if not critical.empty:
            st.subheader("⚠️ Критические позиции")
            for _, row in critical.iterrows():
                percent = safe_division(row["quantity"], row["min_qty"]) * 100
                st.warning(
                    f"**{row['item']}** — осталось **{row['quantity']} {row['unit']}** "
                    f"(минимум {row['min_qty']}) — {percent:.0f}% от нормы"
                )
    
    with t2:
        st.subheader("Текущие остатки на складе")
        
        # Поиск
        search = st.text_input("🔍 Поиск по товару", key="med_search")
        
        df = stock.copy()
        if search:
            df = df[df["item"].str.contains(search, case=False, na=False)]
        
        # Добавляем статус
        if not df.empty:
            df["Статус"] = df.apply(
                lambda row: "⚠️ Критично" if row["quantity"] <= row["min_qty"] 
                else "✅ Норма", axis=1
            )
        
        st.dataframe(
            rus(df, "stock"),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Статус": st.column_config.TextColumn(
                    "Статус",
                    help="Текущее состояние запаса"
                )
            }
        )
        
        # Критические позиции отдельно
        if not critical.empty:
            with st.expander("⚠️ Критические позиции", expanded=True):
                st.dataframe(rus(critical, "stock"), use_container_width=True, hide_index=True)
    
    with t3:
        st.subheader("Списание со склада")
        
        if stock.empty:
            st.info("Нет товаров для списания")
            return
        
        with st.form("spisanie_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                item = st.selectbox(
                    "Выберите товар",
                    options=sorted(stock["item"].unique())
                )
                
                # Получаем информацию о товаре
                item_data = stock[stock["item"] == item].iloc[0]
                current_qty = float(item_data["quantity"])
                unit = item_data["unit"]
                
                st.info(f"💰 Текущий остаток: **{current_qty} {unit}**")
                
            with col2:
                qty = st.number_input(
                    "Количество для списания",
                    min_value=0.01,
                    max_value=float(current_qty),
                    step=0.01,
                    format="%.2f"
                )
                
                reason = st.selectbox(
                    "Причина списания",
                    ["Использовано", "Брак", "Просрочено", "Другое"]
                )
            
            comment = st.text_area("Комментарий / Пациент")
            
            submitted = st.form_submit_button(
                "🗑️ СПИСАТЬ",
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if qty <= 0:
                    st.error("Введите корректное количество")
                elif qty > current_qty:
                    st.error(f"Недостаточно! Доступно: {current_qty} {unit}")
                else:
                    try:
                        # Обновляем остатки
                        stock.loc[stock["item"] == item, "quantity"] -= qty
                        if save_raw("stock", stock):
                            # Добавляем запись в историю закупок
                            new_record = pd.DataFrame([{
                                "date": date.today().strftime("%Y-%m-%d"),
                                "item": f"[СПИСАНО] {item}",
                                "category": item_data["category"],
                                "qty": qty,
                                "unit": unit,
                                "price": 0,
                                "total": 0,
                                "supplier": "",
                                "comment": f"{reason}: {comment}",
                                "photo": "",
                                "added_by": "Медсестра"
                            }])
                            
                            updated_purchases = pd.concat([purchases, new_record], ignore_index=True)
                            save_raw("purchases", updated_purchases)
                            
                            load_all_data(force=True)
                            StateManager.add_notification(f"Списано {qty} {unit} {item}", "success")
                            st.balloons()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка при списании: {e}")
    
    with t4:
        st.subheader("Создать заявку на закупку")
        
        with st.form("order_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                item = st.text_input(
                    "Что нужно купить?",
                    placeholder="Например: Перчатки нитриловые размер M"
                )
                
                qty = st.number_input(
                    "Количество",
                    min_value=1,
                    step=1,
                    format="%d"
                )
            
            with col2:
                unit = st.selectbox(
                    "Единица измерения",
                    ["шт", "упак", "коробка", "литр", "пара", "рулон", "комплект"]
                )
                
                priority = st.select_slider(
                    "Приоритет",
                    options=["Низкий", "Средний", "Высокий", "Критический"],
                    value="Средний"
                )
            
            comment = st.text_area("Комментарий")
            
            submitted = st.form_submit_button(
                "📨 ОТПРАВИТЬ ЗАЯВКУ",
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if not item.strip():
                    st.error("Укажите название товара")
                else:
                    try:
                        new_order = pd.DataFrame([{
                            "item": item.strip(),
                            "qty": qty,
                            "unit": unit,
                            "comment": comment,
                            "ordered_by": "Медсестра",
                            "ordered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "new",
                            "priority": priority
                        }])
                        
                        updated_orders = pd.concat([orders, new_order], ignore_index=True)
                        if save_raw("orders", updated_orders):
                            load_all_data(force=True)
                            StateManager.add_notification("Заявка отправлена!", "success")
                            st.balloons()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка при создании заявки: {e}")

# ===================== СНАБЖЕНИЕ =====================
def snab_interface():
    """Интерфейс снабжения"""
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "📨 Заявки", "🛒 Закупка", "📜 История", "📦 Склад", 
        "📈 Аналитика", "🖼 Чеки", "📊 Отчеты"
    ])
    
    with t1:
        st.subheader("Новые заявки")
        
        if st.button("🔄 Обновить заявки", use_container_width=True):
            load_all_data(force=True)
            StateManager.add_notification("Заявки обновлены", "success")
            st.rerun()
        
        if orders.empty:
            st.info("Нет заявок")
        else:
            # Группируем по статусу
            pending = orders[orders["status"] == "new"].copy()
            in_progress = orders[orders["status"] == "in_progress"].copy()
            completed = orders[orders["status"] == "done"].copy()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Новые", len(pending))
            with col2:
                st.metric("В работе", len(in_progress))
            with col3:
                st.metric("Выполнено", len(completed))
            
            if not pending.empty:
                st.subheader("📋 Новые заявки")
                
                # Сортировка по приоритету
                priority_order = {"Критический": 0, "Высокий": 1, "Средний": 2, "Низкий": 3}
                if "priority" in pending.columns:
                    pending["priority_num"] = pending["priority"].map(priority_order)
                    pending = pending.sort_values("priority_num")
                
                for idx, row in pending.iterrows():
                    priority_color = {
                        "Критический": "🔴",
                        "Высокий": "🟠",
                        "Средний": "🟡",
                        "Низкий": "🟢"
                    }.get(row.get("priority", "Средний"), "⚪")
                    
                    with st.expander(
                        f"{priority_color} {row['item']} — {row['qty']} {row['unit']} "
                        f"({row.get('priority', 'Средний')} приоритет)"
                    ):
                        st.caption(f"От: {row['ordered_by']} | {row['ordered_at']}")
                        if row.get('comment'):
                            st.write(f"📝 {row['comment']}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("✅ Взять в работу", key=f"progress_{idx}", use_container_width=True):
                                orders.loc[idx, "status"] = "in_progress"
                                if save_raw("orders", orders):
                                    load_all_data(force=True)
                                    StateManager.add_notification("Заявка взята в работу", "success")
                                    st.rerun()
                        with col2:
                            if st.button("✅ Выполнено", key=f"done_{idx}", use_container_width=True):
                                orders.loc[idx, "status"] = "done"
                                if save_raw("orders", orders):
                                    load_all_data(force=True)
                                    StateManager.add_notification("Заявка выполнена", "success")
                                    st.rerun()
                        with col3:
                            if st.button("❌ Отклонить", key=f"reject_{idx}", use_container_width=True):
                                orders.loc[idx, "status"] = "rejected"
                                if save_raw("orders", orders):
                                    load_all_data(force=True)
                                    StateManager.add_notification("Заявка отклонена", "warning")
                                    st.rerun()
    
    with t2:
        st.subheader("Добавить новую закупку")
        
        with st.form("purchase_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                item = st.text_input("Название товара*")
                category = st.selectbox(
                    "Категория*",
                    ["Расходный материал", "Медикаменты", "Инструменты", 
                     "Канцелярия", "Хозтовары", "Оборудование", "Прочее"]
                )
                qty = st.number_input("Количество*", min_value=0.01, step=0.01)
                unit = st.selectbox(
                    "Единица измерения*",
                    ["шт", "упак", "коробка", "литр", "кг", "пара", "рулон", "комплект"]
                )
            
            with col2:
                price = st.number_input("Цена за единицу, ₸*", min_value=0.0, step=0.01)
                supplier = st.text_input("Поставщик*")
                location = st.text_input("Место хранения", placeholder="Например: Стеллаж А, полка 3")
            
            no_track = st.checkbox("Не учитывать на складе (расходный материал)")
            comment = st.text_area("Комментарий")
            
            files = st.file_uploader(
                "Прикрепить чек/договор",
                accept_multiple_files=True,
                type=["png", "jpg", "jpeg", "pdf", "xlsx", "docx"]
            )
            
            submitted = st.form_submit_button(
                "🛒 ДОБАВИТЬ ЗАКУПКУ",
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                # Валидация
                if not all([item, category, qty, unit, price, supplier]):
                    st.error("Заполните все обязательные поля (отмечены *)")
                else:
                    try:
                        total_price = qty * price
                        
                        # Сохраняем файлы
                        photo_paths = []
                        if files:
                            for file in files:
                                safe_name = f"{date.today()}_{item}_{file.name}".replace(" ", "_")
                                safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
                                file_path = os.path.join(PHOTO_DIR, safe_name)
                                with open(file_path, "wb") as f:
                                    f.write(file.getbuffer())
                                photo_paths.append(file_path)
                        
                        # Добавляем запись в purchases
                        new_purchase = pd.DataFrame([{
                            "date": date.today().strftime("%Y-%m-%d"),
                            "item": item,
                            "category": category,
                            "qty": qty,
                            "unit": unit,
                            "price": price,
                            "total": total_price,
                            "supplier": supplier,
                            "comment": comment,
                            "photo": ";".join(map(str, photo_paths)),
                            "added_by": "Снабжение"
                        }])
                        
                        updated_purchases = pd.concat([purchases, new_purchase], ignore_index=True)
                        
                        if save_raw("purchases", updated_purchases):
                            # Обновляем склад если нужно
                            if not no_track:
                                if item in stock["item"].values:
                                    stock.loc[stock["item"] == item, "quantity"] += qty
                                    if location:
                                        stock.loc[stock["item"] == item, "location"] = location
                                else:
                                    new_stock = pd.DataFrame([{
                                        "item": item,
                                        "category": category,
                                        "unit": unit,
                                        "quantity": qty,
                                        "min_qty": 5,
                                        "max_qty": 50,
                                        "location": location if location else ""
                                    }])
                                    stock = pd.concat([stock, new_stock], ignore_index=True)
                                
                                save_raw("stock", stock)
                            
                            load_all_data(force=True)
                            StateManager.add_notification(f"Закупка {item} добавлена", "success")
                            st.balloons()
                            st.rerun()
                    
                    except Exception as e:
                        st.error(f"Ошибка при добавлении закупки: {e}")
    
    with t3:
        st.subheader("История закупок")
        
        if purchases.empty:
            st.info("Нет данных о закупках")
        else:
            # Фильтры
            col1, col2, col3 = st.columns(3)
            with col1:
                start_date = st.date_input(
                    "С",
                    value=date.today() - timedelta(days=30)
                )
            with col2:
                end_date = st.date_input("По", value=date.today())
            with col3:
                supplier_filter = st.multiselect(
                    "Поставщик",
                    options=sorted(purchases["supplier"].unique())
                )
            
            # Применяем фильтры
            filtered = purchases.copy()
            filtered["date_dt"] = pd.to_datetime(filtered["date"])
            filtered = filtered[
                (filtered["date_dt"].dt.date >= start_date) &
                (filtered["date_dt"].dt.date <= end_date)
            ]
            
            if supplier_filter:
                filtered = filtered[filtered["supplier"].isin(supplier_filter)]
            
            # Отображаем
            st.dataframe(
                rus(filtered, "purchases"),
                use_container_width=True,
                hide_index=True
            )
            
            # Скачивание
            if not filtered.empty:
                csv = filtered.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "📥 Скачать историю",
                    csv,
                    f"purchases_{start_date}_{end_date}.csv",
                    "text/csv",
                    use_container_width=True
                )
    
    with t4:
        st.subheader("Управление складом")
        
        if stock.empty:
            st.info("Склад пуст")
        else:
            # Редактирование
            edited = st.data_editor(
                rus(stock.copy(), "stock"),
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "Минимум": st.column_config.NumberColumn(
                        "Минимум",
                        help="Минимальный остаток для заказа",
                        min_value=0,
                        step=1
                    ),
                    "Максимум": st.column_config.NumberColumn(
                        "Максимум",
                        help="Максимальный желаемый остаток",
                        min_value=0,
                        step=1
                    )
                }
            )
            
            if st.button("💾 Сохранить изменения", type="primary", use_container_width=True):
                # Обратное преобразование колонок
                rev_map = {
                    "Товар": "item",
                    "Категория": "category",
                    "Ед.изм": "unit",
                    "Остаток": "quantity",
                    "Минимум": "min_qty",
                    "Максимум": "max_qty",
                    "Расположение": "location"
                }
                
                edited_eng = edited.rename(columns=rev_map)
                
                if save_raw("stock", edited_eng):
                    load_all_data(force=True)
                    StateManager.add_notification("Остатки сохранены", "success")
                    st.rerun()
    
    with t5:
        st.subheader("Аналитика расходов")
        
        if purchases.empty:
            st.info("Нет данных для аналитики")
        else:
            # Подготовка данных
            purchases["date_dt"] = pd.to_datetime(purchases["date"])
            purchases = purchases.dropna(subset=["date_dt"])
            
            # Выбор периода
            col1, col2 = st.columns(2)
            with col1:
                period = st.selectbox(
                    "Период",
                    ["Месяц", "Квартал", "Год", "Произвольно"]
                )
            
            with col2:
                if period == "Произвольно":
                    start_date = st.date_input(
                        "Начало",
                        value=date.today() - timedelta(days=30)
                    )
                    end_date = st.date_input("Конец", value=date.today())
                    filtered = purchases[
                        (purchases["date_dt"].dt.date >= start_date) &
                        (purchases["date_dt"].dt.date <= end_date)
                    ]
                else:
                    # Последний полный период
                    last_date = purchases["date_dt"].max()
                    if period == "Месяц":
                        start_date = last_date - timedelta(days=30)
                    elif period == "Квартал":
                        start_date = last_date - timedelta(days=90)
                    else:  # Год
                        start_date = last_date - timedelta(days=365)
                    
                    filtered = purchases[purchases["date_dt"] >= start_date]
            
            if filtered.empty:
                st.warning("Нет данных за выбранный период")
            else:
                # Основные метрики
                total_spent = filtered["total"].sum()
                avg_purchase = filtered["total"].mean()
                unique_items = filtered["item"].nunique()
                unique_suppliers = filtered["supplier"].nunique()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Всего потрачено", format_currency(total_spent))
                col2.metric("Средний чек", format_currency(avg_purchase))
                col3.metric("Уникальных товаров", unique_items)
                col4.metric("Поставщиков", unique_suppliers)
                
                # Графики
                tab1, tab2, tab3 = st.tabs(["По категориям", "По времени", "По поставщикам"])
                
                with tab1:
                    # Расходы по категориям
                    cat_data = filtered.groupby("category")["total"].sum().sort_values(ascending=False)
                    
                    fig = px.pie(
                        values=cat_data.values,
                        names=cat_data.index,
                        title="Распределение расходов по категориям",
                        hole=0.3
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Таблица по категориям
                    cat_df = cat_data.reset_index()
                    cat_df.columns = ["Категория", "Сумма"]
                    cat_df["Сумма"] = cat_df["Сумма"].apply(format_currency)
                    cat_df["Доля"] = (cat_data.values / total_spent * 100).round(1).astype(str) + "%"
                    st.dataframe(cat_df, use_container_width=True, hide_index=True)
                
                with tab2:
                    # Динамика по дням
                    daily = filtered.groupby(filtered["date_dt"].dt.date)["total"].sum().reset_index()
                    daily.columns = ["Дата", "Сумма"]
                    
                    fig = px.line(
                        daily,
                        x="Дата",
                        y="Сумма",
                        title="Динамика расходов",
                        markers=True
                    )
                    fig.update_layout(xaxis_title="Дата", yaxis_title="Сумма, ₸")
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab3:
                    # Расходы по поставщикам
                    supplier_data = filtered.groupby("supplier")["total"].sum().sort_values(ascending=False)
                    
                    fig = px.bar(
                        x=supplier_data.index,
                        y=supplier_data.values,
                        title="Расходы по поставщикам",
                        labels={"x": "Поставщик", "y": "Сумма, ₸"}
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Таблица по поставщикам
                    supplier_df = supplier_data.reset_index()
                    supplier_df.columns = ["Поставщик", "Сумма"]
                    supplier_df["Сумма"] = supplier_df["Сумма"].apply(format_currency)
                    supplier_df["Доля"] = (supplier_data.values / total_spent * 100).round(1).astype(str) + "%"
                    st.dataframe(supplier_df, use_container_width=True, hide_index=True)
                
                # Топ-10 закупок
                st.subheader("🏆 Топ-10 самых дорогих закупок")
                top10 = filtered.nlargest(10, "total")[
                    ["date", "item", "category", "supplier", "qty", "unit", "price", "total"]
                ].copy()
                top10["total"] = top10["total"].apply(format_currency)
                top10["price"] = top10["price"].apply(format_currency)
                top10 = top10.rename(columns={
                    "date": "Дата",
                    "item": "Товар",
                    "category": "Категория",
                    "supplier": "Поставщик",
                    "qty": "Кол-во",
                    "unit": "Ед.изм",
                    "price": "Цена",
                    "total": "Сумма"
                })
                st.dataframe(top10, use_container_width=True, hide_index=True)
    
    with t6:
        st.subheader("Чеки и документы")
        
        # Проверяем наличие папки с чеками
        if not os.path.exists(PHOTO_DIR):
            st.info("Папка с чеками не найдена")
        else:
            files = sorted(Path(PHOTO_DIR).iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if not files:
                st.info("Нет загруженных чеков")
            else:
                # Поиск
                search = st.text_input("🔍 Поиск по названию", key="receipt_search")
                
                if search:
                    files = [f for f in files if search.lower() in f.name.lower()]
                
                # Отображение
                cols_per_row = 4
                for i in range(0, len(files), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, file in enumerate(files[i:i+cols_per_row]):
                        with cols[j]:
                            name = file.name
                            if len(name) > 30:
                                name = name[:27] + "..."
                            
                            st.caption(name)
                            
                            if file.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]:
                                st.image(str(file), use_container_width=True)
                            elif file.suffix.lower() == ".pdf":
                                st.markdown(f"📄 [PDF файл]({file})")
                            else:
                                st.markdown(f"📎 {file.suffix.upper()} файл")
                            
                            # Кнопка скачивания
                            with open(file, "rb") as f:
                                st.download_button(
                                    "📥 Скачать",
                                    f.read(),
                                    file_name=file.name,
                                    key=f"download_{file.name}",
                                    use_container_width=True
                                )
    
    with t7:
        st.subheader("Генерация отчетов")
        
        report_type = st.selectbox(
            "Тип отчета",
            ["Расходы по категориям", "Остатки на складе", "Движение товаров", "Эффективность закупок"]
        )
        
        if report_type == "Расходы по категориям":
            if not purchases.empty:
                # Подготовка данных
                purchases["month"] = pd.to_datetime(purchases["date"]).dt.to_period("M")
                monthly_cat = purchases.groupby(["month", "category"])["total"].sum().unstack(fill_value=0)
                
                fig = px.area(
                    monthly_cat,
                    title="Динамика расходов по категориям",
                    labels={"value": "Сумма, ₸", "month": "Месяц"}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        elif report_type == "Остатки на складе":
            if not stock.empty:
                # Текущие остатки
                col1, col2 = st.columns(2)
                
                with col1:
                    # Круговая диаграмма по категориям
                    cat_stock = stock.groupby("category")["quantity"].sum()
                    fig = px.pie(
                        values=cat_stock.values,
                        names=cat_stock.index,
                        title="Распределение запасов по категориям"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Товары с минимальным остатком
                    critical = stock[stock["quantity"] <= stock["min_qty"]].nlargest(10, "quantity")
                    if not critical.empty:
                        fig = px.bar(
                            critical,
                            x="item",
                            y="quantity",
                            title="Товары с критическим остатком",
                            labels={"quantity": "Остаток", "item": "Товар"}
                        )
                        st.plotly_chart(fig, use_container_width=True)
        
        elif report_type == "Движение товаров":
            if not purchases.empty:
                # Частота закупок
                freq = purchases.groupby("item").size().sort_values(ascending=False).head(20)
                
                fig = px.bar(
                    x=freq.index,
                    y=freq.values,
                    title="Топ-20 часто закупаемых товаров",
                    labels={"x": "Товар", "y": "Количество закупок"}
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
        
        elif report_type == "Эффективность закупок":
            if not purchases.empty:
                # Средняя цена по товарам
                avg_price = purchases.groupby("item")["price"].agg(["mean", "min", "max"]).round(2)
                avg_price.columns = ["Средняя", "Мин.", "Макс."]
                avg_price = avg_price.sort_values("Средняя", ascending=False).head(20)
                
                st.subheader("Топ-20 товаров по средней цене")
                avg_price["Средняя"] = avg_price["Средняя"].apply(format_currency)
                avg_price["Мин."] = avg_price["Мин."].apply(format_currency)
                avg_price["Макс."] = avg_price["Макс."].apply(format_currency)
                st.dataframe(avg_price, use_container_width=True)
        
        # Кнопка экспорта
        if st.button("📥 Сгенерировать и скачать отчет", type="primary", use_container_width=True):
            # Здесь можно реализовать создание PDF/Excel отчета
            st.info("Функция генерации отчетов в разработке")

# ===================== АДМИН =====================
def admin_interface():
    """Интерфейс администратора"""
    st.title("🔐 АДМИН-ПАНЕЛЬ")
    
    atabs = st.tabs([
        "📊 Обзор",
        "✏️ Редактирование",
        "👥 Пользователи",
        "🗑 Опасная зона",
        "💾 Бэкап",
        "📊 Логи",
        "⚙️ Настройки"
    ])
    
    with atabs[0]:
        st.subheader("Общая статистика")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего закупок", len(purchases))
        with col2:
            st.metric("Позиций на складе", len(stock))
        with col3:
            st.metric("Активных заявок", len(orders[orders["status"] == "new"]))
        with col4:
            total_files = len(list(Path(PHOTO_DIR).glob("*")))
            st.metric("Файлов чеков", total_files)
        
        # Детальная статистика
        if not purchases.empty:
            purchases["date_dt"] = pd.to_datetime(purchases["date"])
            st.subheader("Динамика закупок")
            
            monthly = purchases.groupby(purchases["date_dt"].dt.to_period("M"))["total"].sum()
            fig = px.line(
                x=monthly.index.astype(str),
                y=monthly.values,
                title="Ежемесячные расходы",
                labels={"x": "Месяц", "y": "Сумма, ₸"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with atabs[1]:
        st.subheader("Редактирование таблиц")
        
        table_choice = st.selectbox(
            "Выберите таблицу",
            ["purchases", "stock", "orders"]
        )
        
        df = get_raw(table_choice)
        
        # Предпросмотр
        st.caption(f"Всего записей: {len(df)}")
        
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{table_choice}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Сохранить изменения", type="primary", use_container_width=True):
                if save_raw(table_choice, edited_df):
                    load_all_data(force=True)
                    StateManager.add_notification(f"Таблица {table_choice} сохранена", "success")
                    st.rerun()
        
        with col2:
            if st.button("🔄 Отменить изменения", use_container_width=True):
                st.rerun()
    
    with atabs[2]:
        st.subheader("Управление пользователями")
        
        # Здесь можно добавить управление пользователями
        st.info("Функция управления пользователями в разработке")
        
        # Пример формы для добавления пользователя
        with st.expander("➕ Добавить пользователя"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Логин")
                new_role = st.selectbox("Роль", ["med", "snab", "admin"])
            with col2:
                new_password = st.text_input("Пароль", type="password")
                new_password_confirm = st.text_input("Подтверждение пароля", type="password")
            
            if st.button("Создать пользователя"):
                if new_password != new_password_confirm:
                    st.error("Пароли не совпадают")
                else:
                    st.success(f"Пользователь {new_username} создан (демо-режим)")
    
    with atabs[3]:
        st.subheader("🗑 Опасная зона")
        
        st.warning("""
        ⚠️ **Внимание!** Действия в этом разделе необратимы.
        Будьте предельно осторожны!
        """)
        
        # Очистка таблицы
        st.markdown("### Очистка таблицы")
        table_to_clear = st.selectbox(
            "Выберите таблицу для очистки",
            ["purchases", "stock", "orders"],
            key="clear_table"
        )
        
        confirm1 = st.checkbox("Я понимаю, что все данные в таблице будут удалены", key="confirm_clear")
        
        if st.button(f"🗑 ОЧИСТИТЬ {table_to_clear.upper()}", type="primary"):
            if confirm1:
                if delete_all_from_table(table_to_clear):
                    load_all_data(force=True)
                    StateManager.add_notification(f"Таблица {table_to_clear} очищена", "warning")
                    st.rerun()
            else:
                st.error("Подтвердите действие")
        
        st.divider()
        
        # Полное уничтожение
        st.markdown("### ☢️ ПОЛНОЕ УНИЧТОЖЕНИЕ БАЗЫ")
        st.error("Это удалит ВСЕ данные и файлы без возможности восстановления!")
        
        confirm2 = st.text_input("Введите 'УНИЧТОЖИТЬ' для подтверждения")
        confirm3 = st.checkbox("Я осознаю последствия и принимаю их")
        
        if st.button("☢️ УНИЧТОЖИТЬ ВСЁ", type="primary"):
            if confirm2 == "УНИЧТОЖИТЬ" and confirm3:
                # Удаляем все таблицы
                for table in ["purchases", "stock", "orders"]:
                    delete_all_from_table(table)
                
                # Удаляем папку с чеками
                if os.path.exists(PHOTO_DIR):
                    shutil.rmtree(PHOTO_DIR)
                    os.makedirs(PHOTO_DIR)
                
                load_all_data(force=True)
                StateManager.add_notification("⚠️ Все данные уничтожены", "error")
                st.rerun()
            else:
                st.error("Неверное подтверждение")
    
    with atabs[4]:
        st.subheader("Резервное копирование")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📦 Создать бэкап")
            if st.button("Создать полный бэкап", type="primary", use_container_width=True):
                with st.spinner("Создание бэкапа..."):
                    backup_data = create_backup()
                    if backup_data:
                        st.download_button(
                            "📥 Скачать бэкап",
                            backup_data.getvalue(),
                            f"OLYMPUS_BACKUP_{date.today()}.zip",
                            "application/zip",
                            use_container_width=True
                        )
                        StateManager.add_notification("Бэкап создан", "success")
        
        with col2:
            st.markdown("### 🔄 Восстановить из бэкапа")
            uploaded_file = st.file_uploader(
                "Загрузите файл бэкапа",
                type=["zip"]
            )
            
            if uploaded_file and st.button("Восстановить", use_container_width=True):
                with st.spinner("Восстановление..."):
                    if restore_from_backup(uploaded_file):
                        load_all_data(force=True)
                        StateManager.add_notification("Восстановление завершено", "success")
                        st.rerun()
        
        # Информация о последних бэкапах
        st.divider()
        st.markdown("### 📋 Последние бэкапы")
        
        backup_dir = Path("backups")
        if not backup_dir.exists():
            backup_dir.mkdir(exist_ok=True)
        
        backups = sorted(backup_dir.glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
        
        if backups:
            for backup in backups:
                size = backup.stat().st_size / 1024 / 1024  # в МБ
                modified = datetime.fromtimestamp(backup.stat().st_mtime)
                st.text(f"{modified.strftime('%Y-%m-%d %H:%M')} - {backup.name} ({size:.1f} МБ)")
        else:
            st.info("Нет сохраненных бэкапов")
    
    with atabs[5]:
        st.subheader("Логи системы")
        
        # Отображаем уведомления как логи
        if st.session_state.notifications:
            for notif in reversed(st.session_state.notifications):
                emoji = {
                    "success": "✅",
                    "error": "❌",
                    "warning": "⚠️",
                    "info": "ℹ️"
                }.get(notif["type"], "📌")
                
                st.markdown(f"{emoji} **{notif['time'].strftime('%H:%M:%S')}** - {notif['message']}")
        else:
            st.info("Логи пусты")
        
        if st.button("Очистить логи", use_container_width=True):
            st.session_state.notifications = []
            st.rerun()
    
    with atabs[6]:
        st.subheader("Настройки системы")
        
        # Настройки темы
        theme = st.selectbox(
            "Тема оформления",
            ["Светлая", "Темная", "Системная"],
            index=0
        )
        
        # Настройки уведомлений
        st.markdown("### Уведомления")
        email_notifications = st.checkbox("Email-уведомления", value=False)
        telegram_notifications = st.checkbox("Telegram-уведомления", value=False)
        
        if email_notifications:
            st.text_input("Email для уведомлений")
        
        # Настройки склада
        st.markdown("### Настройки склада")
        default_min_qty = st.number_input("Минимальный остаток по умолчанию", value=5, min_value=1)
        default_max_qty = st.number_input("Максимальный остаток по умолчанию", value=50, min_value=1)
        
        if st.button("💾 Сохранить настройки", type="primary"):
            StateManager.add_notification("Настройки сохранены", "success")
            st.rerun()

# ===================== ОСНОВНАЯ ПРОГРАММА =====================
def main():
    """Главная функция"""
    
    # Проверка авторизации
    if st.session_state.role is None:
        login_screen()
    else:
        # Показываем боковую панель
        show_sidebar()
        
        # Основной интерфейс в зависимости от роли
        if st.session_state.role == "med":
            med_interface()
        elif st.session_state.role == "snab":
            snab_interface()
        elif st.session_state.role == "admin":
            admin_interface()
        
        # Футер
        st.markdown("""
        <div style='text-align:center; padding:40px 0 20px; color:#64748b; font-size:0.9rem;'>
            <hr style='margin:20px 0; opacity:0.2;'>
            © 2026 КДЛ OLYMPUS • Версия 2.0 • Все права защищены
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
