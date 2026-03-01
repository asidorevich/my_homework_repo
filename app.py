import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
from pathlib import Path
import zipfile
import io
import shutil
from sqlalchemy import create_engine, text
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

# ===================== БАЗОВЫЙ CSS =====================
st.markdown("""
<style>
    .main, .stApp {
        background: linear-gradient(135deg, #f8faff 0%, #e6f3ff 100%);
    }
    
    /* Увеличенные табы */
    div[data-testid="stTabs"] button {
        font-size: 1.2rem !important;
        padding: 10px 20px !important;
    }
    
    /* Метрики */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #ff8c42;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    
    /* Кнопки */
    .stButton > button {
        background: linear-gradient(45deg, #ff8c42, #ff6b6b) !important;
        color: white !important;
        border-radius: 10px !important;
    }
    
    /* Адаптация для мобильных */
    @media (max-width: 768px) {
        div[data-testid="stTabs"] button {
            font-size: 1rem !important;
            padding: 8px 12px !important;
        }
        h1 { font-size: 2rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ===================== БАЗА ДАННЫХ =====================
@st.cache_resource
def get_engine():
    """Подключение к БД"""
    try:
        return create_engine(st.secrets["db_url"])
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        return None

def get_raw(table):
    """Получение данных из таблицы"""
    try:
        engine = get_engine()
        if engine is None:
            return pd.DataFrame()
        with engine.connect() as conn:
            return pd.read_sql(f"SELECT * FROM {table}", conn)
    except:
        return pd.DataFrame()

def save_raw(table, df):
    """Сохранение данных в таблицу"""
    try:
        engine = get_engine()
        if engine is None:
            return False
        with engine.connect() as conn:
            df.to_sql(table, conn, if_exists="replace", index=False)
            conn.commit()
        return True
    except:
        return False

def delete_all_from_table(table):
    """Очистка таблицы"""
    try:
        engine = get_engine()
        if engine is None:
            return False
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM {table}"))
            conn.commit()
        return True
    except:
        return False

# ===================== ИНИЦИАЛИЗАЦИЯ =====================
if "data" not in st.session_state:
    st.session_state.data = {
        "purchases": pd.DataFrame(),
        "stock": pd.DataFrame(),
        "orders": pd.DataFrame()
    }
if "role" not in st.session_state:
    st.session_state.role = None

def load_all_data(force=False):
    """Загрузка всех данных"""
    if force:
        st.session_state.data = {
            "purchases": get_raw("purchases"),
            "stock": get_raw("stock"),
            "orders": get_raw("orders")
        }

load_all_data()
purchases = st.session_state.data["purchases"]
stock = st.session_state.data["stock"]
orders = st.session_state.data["orders"]

# ===================== ЛОГО =====================
LOGO_URL = "https://github.com/asidorevich/my_homework_repo/blob/main/logo.PNG?raw=true"

def show_logo():
    st.markdown(f"""
    <div style="text-align:center; padding:10px 0;">
        <img src="{LOGO_URL}" width="80" style="border-radius:50%;">
        <h1 style="font-size:2.5rem; margin:5px 0;">OLYMPUS</h1>
        <p style="color:#ff8c42;">2026</p>
    </div>
    """, unsafe_allow_html=True)

# ===================== РУССКИЕ ЗАГОЛОВКИ =====================
def rus(df, kind):
    """Перевод колонок на русский"""
    if df.empty:
        return df
    
    maps = {
        "purchases": {
            "rename": {
                "date": "Дата", "item": "Товар", "category": "Категория",
                "qty": "Кол-во", "unit": "Ед.изм", "price": "Цена, ₸",
                "total": "Сумма, ₸", "supplier": "Поставщик",
                "comment": "Комментарий", "photo": "Чек", "added_by": "Кто добавил"
            },
            "order": ["Дата", "Товар", "Категория", "Кол-во", "Ед.изм", 
                     "Цена, ₸", "Сумма, ₸", "Поставщик", "Комментарий"]
        },
        "stock": {
            "rename": {
                "item": "Товар", "category": "Категория", "unit": "Ед.изм",
                "quantity": "Остаток", "min_qty": "Минимум"
            },
            "order": ["Товар", "Категория", "Ед.изм", "Остаток", "Минимум"]
        },
        "orders": {
            "rename": {
                "item": "Товар", "qty": "Кол-во", "unit": "Ед.изм",
                "comment": "Комментарий", "ordered_by": "Кто заказал",
                "ordered_at": "Когда", "status": "Статус"
            },
            "order": ["Когда", "Товар", "Кол-во", "Ед.изм", "Комментарий", 
                     "Кто заказал", "Статус"]
        }
    }
    
    m = maps.get(kind, {"rename": {}, "order": []})
    df = df.rename(columns={k: v for k, v in m["rename"].items() if k in df.columns})
    return df[[c for c in m["order"] if c in df.columns]]

# ===================== ВХОД =====================
def login_screen():
    show_logo()
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### Вход в систему")
        
        role = st.selectbox(
            "Роль",
            ["Медсестра", "Снабжение", "Администратор"]
        )
        
        pwd = st.text_input("Пароль", type="password")
        
        if st.button("Войти", use_container_width=True, type="primary"):
            if role == "Медсестра" and pwd == "med123":
                st.session_state.role = "med"
                st.rerun()
            elif role == "Снабжение" and pwd == "olympus2025":
                st.session_state.role = "snab"
                st.rerun()
            elif role == "Администратор" and pwd == "godmode2026":
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Неверный пароль")

# ===================== САЙДБАР =====================
def show_sidebar():
    with st.sidebar:
        show_logo()
        
        total = purchases["total"].sum() if not purchases.empty and "total" in purchases.columns else 0
        st.metric("💰 Всего потрачено", f"{total:,.0f} ₸")
        
        if st.button("🔄 Обновить", use_container_width=True):
            load_all_data(force=True)
            st.rerun()
        
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.role = None
            st.rerun()

# ===================== МЕДСЕСТРА =====================
def med_interface():
    tabs = st.tabs(["📊 Дашборд", "📦 Остатки", "📉 Списание", "📨 Заявка"])
    
    with tabs[0]:
        st.subheader("Главная")
        
        if stock.empty:
            st.info("Нет данных")
            return
        
        critical = stock[stock["quantity"] <= stock["min_qty"]]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Критически мало", len(critical))
        col2.metric("Всего позиций", len(stock))
        col3.metric("Общий остаток", f"{stock['quantity'].sum():,.0f}")
        
        if not critical.empty:
            st.subheader("⚠️ Критические позиции")
            for _, row in critical.iterrows():
                st.error(f"**{row['item']}** — осталось {row['quantity']} {row['unit']}")
    
    with tabs[1]:
        st.subheader("Остатки")
        
        search = st.text_input("🔍 Поиск")
        df = stock.copy()
        if search:
            df = df[df["item"].str.contains(search, case=False, na=False)]
        
        st.dataframe(rus(df, "stock"), use_container_width=True, hide_index=True)
    
    with tabs[2]:
        st.subheader("Списание")
        
        if stock.empty:
            st.info("Нет товаров")
            return
        
        with st.form("spis_form"):
            item = st.selectbox("Товар", stock["item"].unique())
            
            item_data = stock[stock["item"] == item].iloc[0]
            current_qty = float(item_data["quantity"])
            unit = item_data["unit"]
            
            st.info(f"Доступно: {current_qty} {unit}")
            
            qty = st.number_input("Количество", min_value=0.01, max_value=current_qty, step=0.01)
            reason = st.text_input("Причина/Пациент")
            
            if st.form_submit_button("СПИСАТЬ", type="primary", use_container_width=True):
                if qty > 0:
                    # Обновляем остатки
                    stock.loc[stock["item"] == item, "quantity"] -= qty
                    save_raw("stock", stock)
                    
                    # Добавляем запись
                    new_record = pd.DataFrame([{
                        "date": date.today().strftime("%Y-%m-%d"),
                        "item": f"[СПИСАНО] {item}",
                        "category": item_data["category"],
                        "qty": qty,
                        "unit": unit,
                        "price": 0,
                        "total": 0,
                        "supplier": "",
                        "comment": reason,
                        "photo": "",
                        "added_by": "Медсестра"
                    }])
                    
                    save_raw("purchases", pd.concat([purchases, new_record], ignore_index=True))
                    load_all_data(force=True)
                    st.success(f"Списано {qty} {unit}")
                    st.rerun()
    
    with tabs[3]:
        st.subheader("Новая заявка")
        
        with st.form("order_form"):
            item = st.text_input("Что нужно?")
            qty = st.number_input("Количество", min_value=1, step=1)
            unit = st.selectbox("Ед.изм.", ["шт", "упак", "коробка", "литр"])
            comment = st.text_area("Комментарий")
            
            if st.form_submit_button("ОТПРАВИТЬ", type="primary", use_container_width=True):
                if item:
                    new_order = pd.DataFrame([{
                        "item": item,
                        "qty": qty,
                        "unit": unit,
                        "comment": comment,
                        "ordered_by": "Медсестра",
                        "ordered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "status": "new"
                    }])
                    
                    save_raw("orders", pd.concat([orders, new_order], ignore_index=True))
                    load_all_data(force=True)
                    st.success("Заявка отправлена")
                    st.rerun()

# ===================== СНАБЖЕНИЕ =====================
def snab_interface():
    tabs = st.tabs(["📨 Заявки", "🛒 Закупка", "📜 История", "📦 Склад", "📈 Аналитика"])
    
    with tabs[0]:
        st.subheader("Новые заявки")
        
        new_orders = orders[orders["status"] == "new"] if not orders.empty else pd.DataFrame()
        
        if new_orders.empty:
            st.info("Нет новых заявок")
        else:
            for idx, row in new_orders.iterrows():
                with st.expander(f"{row['item']} — {row['qty']} {row['unit']}"):
                    st.write(f"От: {row['ordered_by']} | {row['ordered_at']}")
                    if row.get('comment'):
                        st.write(row['comment'])
                    
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Выполнено", key=f"done_{idx}"):
                        orders.loc[idx, "status"] = "done"
                        save_raw("orders", orders)
                        load_all_data(force=True)
                        st.rerun()
                    if col2.button("❌ Отклонить", key=f"rej_{idx}"):
                        orders.loc[idx, "status"] = "rejected"
                        save_raw("orders", orders)
                        load_all_data(force=True)
                        st.rerun()
    
    with tabs[1]:
        st.subheader("Добавить закупку")
        
        with st.form("purchase_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                item = st.text_input("Товар*")
                category = st.selectbox("Категория*", 
                    ["Расходники", "Медикаменты", "Инструменты", "Хозтовары"])
                qty = st.number_input("Количество*", min_value=0.01, step=0.01)
                unit = st.selectbox("Ед.изм.*", ["шт", "упак", "коробка", "литр"])
            
            with col2:
                price = st.number_input("Цена за ед.*", min_value=0.0, step=0.01)
                supplier = st.text_input("Поставщик*")
            
            no_track = st.checkbox("Не учитывать на складе")
            files = st.file_uploader("Чеки", accept_multiple_files=True, type=["png","jpg","jpeg","pdf"])
            
            if st.form_submit_button("ДОБАВИТЬ", type="primary", use_container_width=True):
                if item and qty and price and supplier:
                    total = qty * price
                    
                    # Сохраняем чеки
                    photo_paths = []
                    if files:
                        for f in files:
                            path = os.path.join(PHOTO_DIR, f"{date.today()}_{item}_{f.name}")
                            with open(path, "wb") as out:
                                out.write(f.getbuffer())
                            photo_paths.append(str(path))
                    
                    # Добавляем закупку
                    new_purchase = pd.DataFrame([{
                        "date": date.today().strftime("%Y-%m-%d"),
                        "item": item,
                        "category": category,
                        "qty": qty,
                        "unit": unit,
                        "price": price,
                        "total": total,
                        "supplier": supplier,
                        "comment": "",
                        "photo": ";".join(photo_paths),
                        "added_by": "Снабжение"
                    }])
                    
                    save_raw("purchases", pd.concat([purchases, new_purchase], ignore_index=True))
                    
                    # Обновляем склад
                    if not no_track:
                        if item in stock["item"].values:
                            stock.loc[stock["item"] == item, "quantity"] += qty
                        else:
                            new_stock = pd.DataFrame([{
                                "item": item,
                                "category": category,
                                "unit": unit,
                                "quantity": qty,
                                "min_qty": 5
                            }])
                            stock = pd.concat([stock, new_stock], ignore_index=True)
                        
                        save_raw("stock", stock)
                    
                    load_all_data(force=True)
                    st.success("Закупка добавлена")
                    st.rerun()
    
    with tabs[2]:
        st.subheader("История закупок")
        if not purchases.empty:
            st.dataframe(rus(purchases, "purchases"), use_container_width=True, hide_index=True)
    
    with tabs[3]:
        st.subheader("Управление складом")
        
        if not stock.empty:
            edited = st.data_editor(rus(stock, "stock"), num_rows="dynamic", use_container_width=True)
            
            if st.button("💾 Сохранить"):
                rev_map = {
                    "Товар": "item", "Категория": "category", "Ед.изм": "unit",
                    "Остаток": "quantity", "Минимум": "min_qty"
                }
                save_raw("stock", edited.rename(columns=rev_map))
                load_all_data(force=True)
                st.success("Сохранено")
                st.rerun()
    
    with tabs[4]:
        st.subheader("Аналитика")
        
        if purchases.empty:
            st.info("Нет данных")
        else:
            # Простая статистика
            total = purchases["total"].sum()
            avg = purchases["total"].mean()
            count = len(purchases)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Всего", f"{total:,.0f} ₸")
            col2.metric("Средний чек", f"{avg:,.0f} ₸")
            col3.metric("Кол-во", count)
            
            # По категориям
            if "category" in purchases.columns:
                st.subheader("По категориям")
                cat_data = purchases.groupby("category")["total"].sum().sort_values(ascending=False)
                st.bar_chart(cat_data)

# ===================== АДМИН =====================
def admin_interface():
    st.title("🔐 АДМИН")
    
    tabs = st.tabs(["📊 Обзор", "✏️ Редактор", "🗑 Очистка", "💾 Бэкап"])
    
    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        col1.metric("Закупок", len(purchases))
        col2.metric("На складе", len(stock))
        col3.metric("Заявок", len(orders))
    
    with tabs[1]:
        table = st.selectbox("Таблица", ["purchases", "stock", "orders"])
        df = get_raw(table)
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("Сохранить"):
            save_raw(table, edited)
            load_all_data(force=True)
            st.success("Сохранено")
            st.rerun()
    
    with tabs[2]:
        st.warning("⚠️ Опасная зона")
        table = st.selectbox("Очистить таблицу", ["purchases", "stock", "orders"])
        
        if st.button(f"Очистить {table}"):
            if st.checkbox("Подтверждаю"):
                delete_all_from_table(table)
                load_all_data(force=True)
                st.success(f"{table} очищена")
                st.rerun()
    
    with tabs[3]:
        if st.button("Создать бэкап"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for t in ["purchases", "stock", "orders"]:
                    df = get_raw(t)
                    zf.writestr(f"{t}.csv", df.to_csv(index=False))
                
                if os.path.exists(PHOTO_DIR):
                    for f in Path(PHOTO_DIR).glob("*"):
                        zf.write(f, f"чеки/{f.name}")
            
            zip_buffer.seek(0)
            st.download_button(
                "Скачать бэкап",
                zip_buffer.getvalue(),
                f"backup_{date.today()}.zip"
            )

# ===================== ОСНОВНАЯ ПРОГРАММА =====================
def main():
    if st.session_state.role is None:
        login_screen()
    else:
        show_sidebar()
        
        if st.session_state.role == "med":
            med_interface()
        elif st.session_state.role == "snab":
            snab_interface()
        elif st.session_state.role == "admin":
            admin_interface()

if __name__ == "__main__":
    main()
