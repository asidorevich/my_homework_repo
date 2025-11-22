import streamlit as st
import sqlite3
import pandas as pd
import os
import base64
from datetime import datetime, date
from pathlib import Path

# ===================== КОНФИГ =====================
st.set_page_config(page_title="OLYMPUS", page_icon="mountain", layout="wide", initial_sidebar_state="expanded")
DB_FILE = "olympus.db"
PHOTO_DIR = "чеки"
LOGO = "logo.png"
os.makedirs(PHOTO_DIR, exist_ok=True)

# ===================== КРАСИВЫЕ СТИЛИ =====================
st.markdown("""
<style>
    .main, .stApp {background: linear-gradient(135deg, #f8faff 0%, #e6f3ff 100%); color: #1a2a44;}
    html, body, [class*="css"] {font-size: 19px !important;}
    .stDataFrame, .stDataEditor, .stDataFrame table, .stDataEditor table {
        font-size: 20px !important;
    }
    .stDataFrame th, .stDataFrame td, .stDataEditor th, .stDataEditor td {
        font-size: 20px !important;
        padding: 16px 12px !important;
        font-weight: 600;
    }
    div[data-testid="stTabs"] > div[role="tablist"] {
        position: relative;
        border-bottom: none !important;
        padding: 20px 0 50px 0;
        gap: 20px;
        justify-content: center;
        background: transparent;
    }
    .olympus-underline {
        position: absolute;
        bottom: 18px;
        left: 0;
        height: 6px;
        background: linear-gradient(90deg, #ff8c42, #00d4ff);
        border-radius: 4px;
        transition: all 0.7s cubic-bezier(0.22, 0.61, 0.36, 1);
        box-shadow: 0 0 30px rgba(255,140,66,0.8), 0 0 40px rgba(0,212,255,0.7);
        z-index: 10;
        pointer-events: none;
    }
    div[role="tablist"] button {
        background: rgba(255, 255, 255, 0.95) !important;
        color: #2c4a7a !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
        padding: 18px 42px !important;
        border-radius: 18px !important;
        border: none !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.12) !important;
        transition: all 0.4s ease !important;
        min-width: 190px;
        backdrop-filter: blur(10px);
        margin: 0 8px;
    }
    div[role="tablist"] button:hover {
        transform: translateY(-6px) scale(1.03);
        box-shadow: 0 15px 35px rgba(0,0,0,0.18) !important;
        color: #ff8c42 !important;
    }
    div[role="tablist"] button[data-state="active"] {
        font-weight: 900 !important;
        color: white !important;
        background: linear-gradient(45deg, #ff8c42, #00d4ff) !important;
        box-shadow: 0 12px 35px rgba(255,140,66,0.5) !important;
        transform: translateY(-4px);
        z-index: 11;
    }
    .stButton>button {
        background: linear-gradient(45deg, #ff8c42, #00d4ff) !important;
        color: white !important;
        border: none !important;
        border-radius: 16px !important;
        padding: 16px 40px !important;
        font-weight: bold !important;
        font-size: 1.3rem !important;
        box-shadow: 0 6px 20px rgba(255,140,66,0.4);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 30px rgba(255,140,66,0.6);
    }
    h1,h2,h3,h4,h5,h6 {
        background: linear-gradient(90deg, #ff8c42, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
    }
    .css-1d391kg, .stDataFrame, .stDataEditor {
        background: white !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.08) !important;
        overflow: hidden;
    }
    /* Стиль для большой кнопки обновления */
    .big-refresh {
        text-align: center;
        margin: 40px 0 30px 0;
    }
</style>
<script>
    document.addEventListener("DOMContentLoaded", () => {
        const tabList = document.querySelector('div[data-testid="stTabs"] > div[role="tablist"]');
        if (!tabList) return;
        let underline = document.querySelector('.olympus-underline');
        if (!underline) {
            underline = document.createElement("div");
            underline.className = "olympus-underline";
            tabList.appendChild(underline);
        }
        function updateUnderline() {
            const active = tabList.querySelector('button[data-state="active"]');
            if (active) {
                const aRect = active.getBoundingClientRect();
                const lRect = tabList.getBoundingClientRect();
                underline.style.left = (aRect.left - lRect.left + tabList.scrollLeft) + "px";
                underline.style.width = aRect.width + "px";
            }
        }
        setTimeout(updateUnderline, 100);
        new MutationObserver(updateUnderline).observe(tabList, {attributes: true, childList: true, subtree: true});
        window.addEventListener('resize', updateUnderline);
        tabList.addEventListener('click', () => setTimeout(updateUnderline, 50));
    });
</script>
""", unsafe_allow_html=True)

# ===================== РУССКИЕ ЗАГОЛОВКИ =====================
def rus(df, kind):
    if df.empty: return df
    maps = {
        "purchases": {"rename": {"date":"Дата","item":"Товар","category":"Категория","qty":"Кол-во","unit":"Ед.изм",
                                "price":"Цена за ед., ₸","total":"Сумма, ₸","supplier":"Поставщик",
                                "comment":"Комментарий","photo":"Чек","added_by":"Кем добавлено"},
                     "order": ["Дата","Товар","Категория","Кол-во","Ед.изм","Цена за ед., ₸","Сумма, ₸","Поставщик","Комментарий","Чек","Кем добавлено"]},
        "stock": {"rename": {"item":"Товар","category":"Категория","unit":"Ед.изм","quantity":"Остаток","min_qty":"Минимум"},
                  "order": ["Товар","Категория","Ед.изм","Остаток","Минимум"]},
        "orders": {"rename": {"item":"Товар","qty":"Кол-во","unit":"Ед.изм","comment":"Комментарий",
                             "ordered_by":"Кем заказано","ordered_at":"Когда","status":"Статус"},
                   "order": ["Когда","Товар","Кол-во","Ед.изм","Комментарий","Кем заказано","Статус"]}
    }
    m = maps.get(kind, {"rename":{}, "order":[]})
    df = df.rename(columns=m["rename"])
    return df[[c for c in m["order"] if c in df.columns]]

# ===================== БАЗА =====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, item TEXT, category TEXT, qty REAL, unit TEXT,
        price REAL, total REAL, supplier TEXT, comment TEXT, photo TEXT, added_by TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stock (
        item TEXT PRIMARY KEY, category TEXT, unit TEXT, quantity REAL DEFAULT 0, min_qty REAL DEFAULT 5)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, qty REAL, unit TEXT, comment TEXT,
        ordered_by TEXT, ordered_at TEXT, status TEXT DEFAULT 'new')''')
    conn.commit()
    conn.close()

def get_raw(table):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def save_raw(table, df):
    conn = sqlite3.connect(DB_FILE)
    df.to_sql(table, conn, if_exists="replace", index=False)
    conn.close()

init_db()

# ===================== СИНХРОНИЗАЦИЯ ДАННЫХ =====================
def load_fresh_data():
    st.session_state.data = {
        "purchases": get_raw("purchases"),
        "stock": get_raw("stock"),
        "orders": get_raw("orders")
    }

if "data" not in st.session_state:
    load_fresh_data()
load_fresh_data()

purchases = st.session_state.data["purchases"]
stock = st.session_state.data["stock"]
orders = st.session_state.data["orders"]

# ===================== ЛОГО =====================
if os.path.exists(LOGO):
    with open(LOGO, "rb") as f:
        logo64 = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <div style="text-align:center; padding:60px 0 40px;">
        <img src="data:image/png;base64,{logo64}" width="150" style="border-radius:50%; border: 6px solid white; box-shadow: 0 0 50px rgba(0,212,255,0.4);">
        <h1 style="font-size:5.5rem;">OLYMPUS</h1>
        <p style="font-size:1.6rem; color:#ff8c42; letter-spacing:5px;">GOD MODE 2026</p>
    </div>
    """, unsafe_allow_html=True)

# ===================== АВТОРИЗАЦИЯ =====================
if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    # ... весь твой красивый HTML-логин оставь как есть, только внутри кнопки:
    if st.button("ВОЙТИ", use_container_width=True, type="primary"):
        if role == "Снабжение (закупки)" and pwd == st.secrets["roles"]["snab_password"]:
            st.session_state.role = "snab"; st.rerun()
        elif role == "Медсестра (списание)" and pwd == st.secrets["roles"]["med_password"]:
            st.session_state.role = "med"; st.rerun()
        else:
            st.error("Неверный пароль")
# ===================== САЙДБАР =====================
total = purchases["total"].sum() if not purchases.empty and "total" in purchases.columns else 0
st.sidebar.metric("Всего потрачено", f"{total:,.0f} ₸")
if st.sidebar.button("Выйти"):
    st.session_state.role = None
    st.rerun()

# ===================== МЕДСЕСТРА =====================
if st.session_state.role == "med":
    t1, t2, t3 = st.tabs(["Остатки", "Списание", "Заказать"])
    # (всё как у вас было — без изменений)
    with t1:
        st.subheader("Текущие остатки на складе")
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Обновить", use_container_width=True):
                load_fresh_data()
                st.success("Остатки обновлены!")
                st.rerun()
        with col2:
            q = st.text_input("Поиск по товару", key="search_med", label_visibility="collapsed")
        df = stock.copy()
        if q:
            df = df[df["item"].str.contains(q, case=False, na=False)]
        st.dataframe(rus(df, "stock"), use_container_width=True)
        crit = stock[stock["quantity"] <= stock["min_qty"]]
        if len(crit) > 0:
            st.error(f"Критически мало: {len(crit)} позиций")
            st.dataframe(rus(crit, "stock"), use_container_width=True)

    with t2:
        st.subheader("Списание со склада")
        load_fresh_data()
        with st.form("spis", clear_on_submit=True):
            item = st.selectbox("Выберите товар", options=sorted(stock["item"]))
            current_qty = stock.loc[stock["item"] == item, "quantity"].iloc[0]
            unit = stock.loc[stock["item"] == item, "unit"].iloc[0]
            st.info(f"Доступно: **{current_qty}** {unit}")
            qty = st.number_input("Списать количество", min_value=0.01, step=0.01)
            com = st.text_input("Пациент / № анализа")
            if st.form_submit_button("СПИСАТЬ", type="primary", use_container_width=True):
                if qty > current_qty:
                    st.error(f"Недостаточно! Остаток: {current_qty}")
                else:
                    stock.loc[stock["item"] == item, "quantity"] -= qty
                    save_raw("stock", stock)
                    new = pd.DataFrame([{
                        "date": date.today().strftime("%Y-%m-%d"),
                        "item": f"[СПИСАНО] {item}",
                        "category": "Списание", "qty": qty, "unit": unit,
                        "price": 0, "total": 0, "supplier": "", "comment": com, "photo": "", "added_by": "Медсестра"
                    }])
                    new_p = pd.concat([purchases, new], ignore_index=True)
                    save_raw("purchases", new_p)
                    load_fresh_data()
                    st.success(f"Списано {qty} × {item}")
                    st.balloons()
                    st.rerun()

    with t3:
        st.subheader("Создать заявку на закупку")
        with st.form("order", clear_on_submit=True):
            item = st.text_input("Что нужно купить?", placeholder="Например: Перчатки нитриловые размер M")
            qty = st.number_input("Количество", min_value=1, step=1)
            unit = st.selectbox("Ед. изм.", ["шт", "упак", "коробка", "литр", "пара", "рулон"])
            com = st.text_area("Комментарий (по желанию)")
            if st.form_submit_button("ОТПРАВИТЬ ЗАЯВКУ", type="primary", use_container_width=True):
                if not item.strip():
                    st.error("Укажите товар")
                else:
                    new_o = pd.DataFrame([{
                        "item": item.strip(), "qty": qty, "unit": unit, "comment": com,
                        "ordered_by": "Медсестра",
                        "ordered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "status": "new"
                    }])
                    new_orders = pd.concat([orders, new_o], ignore_index=True)
                    save_raw("orders", new_orders)
                    load_fresh_data()
                    st.success("Заявка отправлена!")
                    st.balloons()
                    st.rerun()

# ===================== СНАБЖЕНИЕ =====================
else:
    t1,t2,t3,t4,t5,t6 = st.tabs(["Заявки","Закупка","История","Склад","Аналитика","Чеки"])

    with t1:
        st.subheader("Новые заявки от медсестёр")

        # БОЛЬШАЯ КНОПКА «ОБНОВИТЬ ЗАЯВКИ»
        st.markdown("<div class='big-refresh'>", unsafe_allow_html=True)
        if st.button("ОБНОВИТЬ ЗАЯВКИ", 
                     key="big_refresh_orders", 
                     use_container_width=True, 
                     type="primary"):
            load_fresh_data()
            st.success("Заявки обновлены!")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        load_fresh_data()
        pending = orders[orders["status"] == "new"]

        if pending.empty:
            st.success("Нет активных заявок")
        else:
            st.dataframe(rus(pending.copy(), "orders"), use_container_width=True)
            for idx, row in pending.iterrows():
                with st.expander(f"{row['item']} — {row['qty']} {row['unit']}"):
                    st.caption(f"От: {row['ordered_by']} | {row['ordered_at']}")
                    if row['comment']: 
                        st.write(row['comment'])
                    c1, c2 = st.columns(2)
                    if c1.button("Выполнено", key=f"done_{idx}", use_container_width=True):
                        orders.loc[idx, "status"] = "done"
                        save_raw("orders", orders)
                        load_fresh_data()
                        st.success("Отмечено как выполнено")
                        st.rerun()
                    if c2.button("Отклонить", key=f"rej_{idx}", use_container_width=True):
                        orders.loc[idx, "status"] = "rejected"
                        save_raw("orders", orders)
                        load_fresh_data()
                        st.rerun()

    # Остальные вкладки — полностью как у вас были
    with t2:
        st.subheader("Добавить новую закупку")
        load_fresh_data()
        with st.form("buy", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                item = st.text_input("Название товара")
                cat = st.selectbox("Категория", ["Реагенты","Перчатки","Шприцы","Пробирки","Хозтовары","Прочее"])
                qty = st.number_input("Количество", min_value=1)
                unit = st.selectbox("Ед.изм.", ["шт","упак","коробка","литр","рулон"])
            with col2:
                price = st.number_input("Цена за единицу, ₸", min_value=0)
                supplier = st.text_input("Поставщик")
            no_track = st.checkbox("Не учитывать на складе (не расходник)")
            files = st.file_uploader("Прикрепить чек/договор", accept_multiple_files=True, type=["png","jpg","jpeg","pdf"])
            if st.form_submit_button("ДОБАВИТЬ ЗАКУПКУ", type="primary", use_container_width=True):
                total_price = qty * price
                paths = ""
                if files:
                    for f in files:
                        safe_name = f"{date.today()}_{item}_{f.name}".replace(" ", "_")
                        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
                        path = os.path.join(PHOTO_DIR, safe_name)
                        with open(path, "wb") as out:
                            out.write(f.getbuffer())
                        paths += path + ";"
                new_row = pd.DataFrame([{
                    "date": date.today().strftime("%Y-%m-%d"), "item": item, "category": cat,
                    "qty": qty, "unit": unit, "price": price, "total": total_price,
                    "supplier": supplier, "comment": "НЕ НА СКЛАДЕ" if no_track else "",
                    "photo": paths, "added_by": "Снабжение"
                }])
                new_purch = pd.concat([purchases, new_row], ignore_index=True)
                save_raw("purchases", new_purch)
                if not no_track:
                    if item in stock["item"].values:
                        stock.loc[stock["item"] == item, "quantity"] += qty
                    else:
                        new_stock = pd.DataFrame([{"item":item, "category":cat, "unit":unit, "quantity":qty, "min_qty":5}])
                        stock = pd.concat([stock, new_stock], ignore_index=True)
                    save_raw("stock", stock)
                load_fresh_data()
                st.success("Закупка добавлена!")
                st.balloons()
                st.rerun()

    with t3:
        st.subheader("История всех закупок")
        load_fresh_data()
        st.dataframe(rus(purchases.copy(), "purchases"), use_container_width=True)

    with t4:
        st.subheader("Ручное управление остатками")
        load_fresh_data()
        edited = st.data_editor(rus(stock.copy(), "stock"), use_container_width=True)
        if st.button("Сохранить изменения", type="primary"):
            rev_map = {"Товар":"item","Категория":"category","Ед.изм":"unit","Остаток":"quantity","Минимум":"min_qty"}
            edited_eng = edited.rename(columns=rev_map)
            save_raw("stock", edited_eng)
            load_fresh_data()
            st.success("Остатки сохранены!")
            st.rerun()

    with t5:
        st.subheader("Аналитика расходов по месяцам")
        load_fresh_data()
        purchases["date_dt"] = pd.to_datetime(purchases["date"])
        purchases["year_month"] = purchases["date_dt"].dt.strftime("%Y-%m")
        monthly = purchases.groupby("year_month")["total"].sum().reset_index().sort_values("year_month", ascending=False)
        current_month_sum = purchases[purchases["date_dt"].dt.month == date.today().month]["total"].sum()
        st.metric("Потрачено в текущем месяце", f"{current_month_sum:,.0f} ₸")
        st.bar_chart(monthly.set_index("year_month")["total"], use_container_width=True)
        display = monthly.copy()
        display["total"] = display["total"].apply(lambda x: f"{x:,.0f} ₸")
        display.columns = ["Месяц", "Сумма"]
        st.dataframe(display, use_container_width=True)

    with t6:
        st.subheader("Последние чеки и документы")
        files = sorted(Path(PHOTO_DIR).iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:40]
        cols = st.columns(4)
        for i, f in enumerate(files):
            with cols[i % 4]:
                name = f.name.split("_", 2)[-1] if "_" in f.name else f.name
                st.caption(name[:30])
                if f.suffix.lower() in [".png",".jpg",".jpeg"]:
                    st.image(str(f), use_container_width=True)
                else:
                    with open(f, "rb") as pdf_file:
                        st.download_button("Скачать", pdf_file.read(), file_name=f.name, key=str(f))

st.markdown("<div style='text-align:center; padding:100px 0 30px; color:#888; font-size:1rem;'>© 2026 КДЛ OLYMPUS • GOD MODE 2026</div>", unsafe_allow_html=True)