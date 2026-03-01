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

# ===================== КОНФИГ =====================
st.set_page_config(
    page_title="OLYMPUS 2026",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

PHOTO_DIR = "чеки"
os.makedirs(PHOTO_DIR, exist_ok=True)

# ===================== СТИЛИ (оставил твои + небольшие правки) =====================
st.markdown("""
<style>
    .main, .stApp {background: linear-gradient(135deg, #f8faff 0%, #e6f3ff 100%); color: #1a2a44;}
    html, body, [class*="css"] {font-size: 19px !important;}
    div[data-testid="stTabs"] > div[role="tablist"] {
        gap: 20px !important;
        justify-content: center;
        flex-wrap: wrap;
    }
    div[data-testid="stTabs"] button {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        padding: 22px 40px !important;
        border-radius: 22px !important;
        min-width: 170px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    div[data-testid="stTabs"] button:hover {
        transform: translateY(-4px);
        box-shadow: 0 15px 35px rgba(255,140,66,0.3);
    }
    div[data-testid="stTabs"] button[data-state="active"] {
        background: linear-gradient(45deg, #ff8c42, #00d4ff) !important;
        color: white !important;
        transform: scale(1.05);
    }
    @media (max-width: 768px) {
        div[data-testid="stTabs"] button {
            font-size: 1.55rem !important;
            padding: 18px 26px !important;
            min-width: 140px;
        }
        .stButton>button {font-size: 1.45rem !important; padding: 18px 32px !important;}
        h1 {font-size: 2.9rem !important;}
    }
    .metric-card {
        background: white; border-radius: 20px; padding: 22px;
        border-left: 7px solid #ff8c42; box-shadow: 0 10px 30px rgba(0,0,0,0.07);
        margin: 12px 0;
    }
    .stButton>button {
        background: linear-gradient(45deg, #ff8c42, #00d4ff) !important;
        color: white !important; border-radius: 18px !important;
        font-weight: 700 !important; font-size: 1.4rem !important;
        box-shadow: 0 8px 25px rgba(255,140,66,0.4);
    }
    h1,h2,h3,h4 {
        background: linear-gradient(90deg, #ff8c42, #00d4ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 900;
    }
    .stSidebar {background: linear-gradient(180deg, #ffffff, #f0f7ff) !important;}
</style>
""", unsafe_allow_html=True)

# ===================== БАЗА ДАННЫХ =====================
@st.cache_resource
def get_engine():
    return create_engine(st.secrets["db_url"])

def get_raw(table):
    with get_engine().connect() as conn:
        return pd.read_sql(f"SELECT * FROM {table}", conn)

def save_raw(table, df):
    with get_engine().connect() as conn:
        df.to_sql(table, conn, if_exists="replace", index=False)
        conn.commit()

def delete_all_from_table(table):
    with get_engine().connect() as conn:
        conn.execute(text(f"DELETE FROM {table}"))
        conn.commit()

# ===================== ДАННЫЕ =====================
def load_all_data(force=False):
    if "data" not in st.session_state or force:
        st.session_state.data = {
            "purchases": get_raw("purchases"),
            "stock": get_raw("stock"),
            "orders": get_raw("orders")
        }

load_all_data()
purchases = st.session_state.data["purchases"]
stock = st.session_state.data["stock"]
orders = st.session_state.data["orders"]

# ===================== ПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def rus(df, kind):
    if df.empty: return df
    maps = {
        "purchases": {
            "rename": {"date":"Дата","item":"Товар","category":"Категория","qty":"Кол-во","unit":"Ед.изм",
                       "price":"Цена за ед., ₸","total":"Сумма, ₸","supplier":"Поставщик",
                       "comment":"Комментарий","photo":"Чек","added_by":"Кем добавлено"},
            "order": ["Дата","Товар","Категория","Кол-во","Ед.изм","Цена за ед., ₸","Сумма, ₸","Поставщик","Комментарий","Чек","Кем добавлено"]
        },
        "stock": {
            "rename": {"item":"Товар","category":"Категория","unit":"Ед.изм","quantity":"Остаток","min_qty":"Минимум"},
            "order": ["Товар","Категория","Ед.изм","Остаток","Минимум"]
        },
        "orders": {
            "rename": {"item":"Товар","qty":"Кол-во","unit":"Ед.изм","comment":"Комментарий",
                       "ordered_by":"Кем заказано","ordered_at":"Когда","status":"Статус"},
            "order": ["Когда","Товар","Кол-во","Ед.изм","Комментарий","Кем заказано","Статус"]
        }
    }
    m = maps.get(kind, {"rename":{}, "order":[]})
    df = df.rename(columns=m["rename"])
    return df[[c for c in m["order"] if c in df.columns]]

def get_stock_status_color(qty, min_qty):
    try:
        q, m = float(qty), float(min_qty)
        if q <= 0: return "#ffcccc"
        if q <= m * 1.5: return "#fff3cd"
        return "#e6ffe6"
    except:
        return "white"

# ===================== ЛОГО =====================
LOGO_URL = "https://github.com/asidorevich/my_homework_repo/blob/main/logo.PNG?raw=true"
st.markdown(f"""
<div style="text-align:center; padding:25px 0 15px;">
    <img src="{LOGO_URL}" width="125" style="border-radius:50%; border:6px solid #fff; box-shadow: 0 0 40px rgba(0,212,255,0.4);">
    <h1 style="font-size:4.1rem; margin:12px 0 0 0;">OLYMPUS</h1>
    <p style="font-size:1.4rem; color:#ff8c42; letter-spacing:5px;">2026</p>
</div>
""", unsafe_allow_html=True)

# ===================== АВТОРИЗАЦИЯ =====================
if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h2 style='text-align:center; color:#ff8c42;'>Вход в систему</h2>", unsafe_allow_html=True)
        role = st.selectbox("Роль", ["Медсестра (списание)", "Снабжение (закупки)", "🔐 Администратор"])
        pwd = st.text_input("Пароль", type="password")
        if st.button("🔑 ВОЙТИ", use_container_width=True, type="primary"):
            if role == "Медсестра (списание)" and pwd == "med123":
                st.session_state.role = "med"
            elif role == "Снабжение (закупки)" and pwd == "olympus2025":
                st.session_state.role = "snab"
            elif role == "🔐 Администратор" and pwd == "godmode2026":
                st.session_state.role = "admin"
            else:
                st.error("❌ Неверный пароль")
            st.rerun()
    st.stop()

# ===================== САЙДБАР =====================
crit = stock[(stock["quantity"] <= stock["min_qty"]) & (stock["quantity"] > 0)]
zero = stock[stock["quantity"] <= 0]

st.sidebar.image(LOGO_URL, width=140)

colA, colB = st.sidebar.columns(2)
colA.metric("Критично мало", len(crit), delta_color="inverse")
colB.metric("Закончилось", len(zero), delta_color="inverse")

if len(crit) + len(zero) > 0:
    st.sidebar.warning(f"⚠️ Требует внимания: {len(crit) + len(zero)} позиций")

total = purchases["total"].sum() if not purchases.empty and "total" in purchases.columns else 0
st.sidebar.metric("Всего потрачено", f"{total:,.0f} ₸")

if st.sidebar.button("🔄 Обновить все данные", type="primary", use_container_width=True):
    load_all_data(force=True)
    st.toast("✅ Данные обновлены!", icon="🔄")
    st.rerun()

if st.sidebar.button("🚪 Выйти", use_container_width=True):
    st.session_state.role = None
    st.rerun()

# ===================== МЕДСЕСТРА =====================
if st.session_state.role == "med":
    tabs = st.tabs(["🏠 Дашборд", "📦 Остатки", "📉 Списание", "📨 Заявка", "🗒 История списаний"])

    with tabs[0]:
        st.subheader("📊 Главная панель")
        col1, col2, col3 = st.columns(3)
        col1.metric("Критически мало", len(crit))
        col2.metric("Всего позиций", len(stock))
        col3.metric("Общий остаток", f"{stock['quantity'].sum():,.0f}")

        if not crit.empty:
            st.subheader("⚠️ Проблемные позиции")
            for _, row in crit.iterrows():
                st.error(f"**{row['item']}** — осталось **{row['quantity']} {row['unit']}** (мин {row['min_qty']})")

    with tabs[1]:
        st.subheader("Текущие остатки на складе")
        search = st.text_input("🔍 Поиск по товару или категории", key="med_stock_search")
        df_show = stock.copy()
        if search:
            q = search.lower()
            df_show = df_show[
                df_show["item"].str.lower().str.contains(q) |
                df_show["category"].str.lower().str.contains(q)
            ]

        def style_stock(row):
            bg = get_stock_status_color(row["quantity"], row["min_qty"])
            return [f"background-color: {bg}"] * len(row)

        styled = rus(df_show, "stock").style.apply(style_stock, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)

    with tabs[2]:
        st.subheader("Списание со склада")
        with st.form("spisanie_form", clear_on_submit=True):
            item = st.selectbox("Выберите товар", options=sorted(stock["item"].unique()))
            current = stock.loc[stock["item"] == item, "quantity"].iloc[0]
            unit = stock.loc[stock["item"] == item, "unit"].iloc[0]
            st.info(f"Доступно: **{current}** {unit}")
            qty = st.number_input("Списать количество", min_value=0.01, step=0.01, format="%.2f")
            comment = st.text_input("Пациент / № анализа / причина")
            if st.form_submit_button("🗑 СПИСАТЬ", type="primary", use_container_width=True):
                if qty > current:
                    st.error(f"Недостаточно! Остаток: {current} {unit}")
                else:
                    stock.loc[stock["item"] == item, "quantity"] -= qty
                    save_raw("stock", stock)

                    new_row = pd.DataFrame([{
                        "date": date.today().strftime("%Y-%m-%d"),
                        "item": f"[СПИСАНО] {item}",
                        "category": "Списание",
                        "qty": qty,
                        "unit": unit,
                        "price": 0,
                        "total": 0,
                        "supplier": "",
                        "comment": comment,
                        "photo": "",
                        "added_by": "Медсестра"
                    }])
                    save_raw("purchases", pd.concat([purchases, new_row], ignore_index=True))

                    load_all_data(force=True)
                    st.toast(f"✅ Списано {qty} {unit} — {item}", icon="🗑️")
                    st.balloons()
                    st.rerun()

    with tabs[3]:
        st.subheader("Создать заявку на закупку")
        with st.form("zakaz_form", clear_on_submit=True):
            popular = [""] + sorted(stock["item"].unique().tolist())
            selected = st.selectbox("Что нужно?", options=popular)
            if selected == "":
                item_name = st.text_input("Введите название товара", placeholder="Например: Перчатки нитриловые L")
            else:
                item_name = selected

            qty = st.number_input("Количество", min_value=1, step=1)
            unit = st.selectbox("Ед. изм.", ["шт", "упак", "коробка", "литр", "пара", "рулон"])
            comment = st.text_area("Комментарий / примечание")

            if st.form_submit_button("📨 ОТПРАВИТЬ ЗАЯВКУ", type="primary", use_container_width=True):
                if not item_name.strip():
                    st.error("Укажите название товара")
                else:
                    new_order = pd.DataFrame([{
                        "item": item_name.strip(),
                        "qty": qty,
                        "unit": unit,
                        "comment": comment,
                        "ordered_by": "Медсестра",
                        "ordered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "status": "new"
                    }])
                    save_raw("orders", pd.concat([orders, new_order], ignore_index=True))
                    load_all_data(force=True)
                    st.toast("✅ Заявка отправлена в снабжение", icon="📨")
                    st.balloons()
                    st.rerun()

    with tabs[4]:
        st.subheader("История списаний")
        spis = purchases[purchases["category"] == "Списание"].copy()
        if spis.empty:
            st.info("Пока списаний не было")
        else:
            spis["Дата"] = pd.to_datetime(spis["date"]).dt.strftime("%d.%m.%Y")
            spis_show = spis[["Дата", "item", "qty", "unit", "comment"]].rename(columns={
                "item": "Позиция", "qty": "Кол-во", "unit": "Ед.", "comment": "Причина / пациент"
            })
            st.dataframe(spis_show.sort_values("Дата", ascending=False), use_container_width=True, hide_index=True)

# ===================== СНАБЖЕНИЕ =====================
elif st.session_state.role == "snab":
    tabs = st.tabs(["📨 Заявки", "🛒 Закупка", "📜 История", "📦 Склад", "📈 Аналитика", "🖼 Чеки"])

    with tabs[0]:
        st.subheader("Новые заявки от медсестёр")
        if st.button("🔄 ОБНОВИТЬ ЗАЯВКИ", type="primary", use_container_width=True):
            load_all_data(force=True)
            st.rerun()

        pending = orders[orders["status"] == "new"]
        if pending.empty:
            st.success("Нет активных заявок")
        else:
            st.dataframe(rus(pending, "orders"), use_container_width=True, hide_index=True)
            for idx, row in pending.iterrows():
                with st.expander(f"{row['item']}  —  {row['qty']} {row['unit']}"):
                    st.caption(f"От: {row['ordered_by']}  |  {row['ordered_at']}")
                    if row.get('comment'): st.write(row['comment'])
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Выполнено", key=f"done_{idx}"):
                        orders.loc[idx, "status"] = "done"
                        save_raw("orders", orders)
                        load_all_data(force=True)
                        st.rerun()
                    if c2.button("❌ Отклонить", key=f"rej_{idx}"):
                        orders.loc[idx, "status"] = "rejected"
                        save_raw("orders", orders)
                        load_all_data(force=True)
                        st.rerun()

    # ... (остальные вкладки снабжения остаются почти без изменений, 
    #      можешь вставить их из твоего исходного кода — они уже хороши)

# ===================== АДМИН (без изменений) =====================
else:
    st.title("🔐 АДМИН-ПАНЕЛЬ • GOD MODE 2026")
    # ... (твой оригинальный код админ-панели остаётся без изменений)

st.markdown("""
<div style='text-align:center; padding:60px 0 30px; color:#64748b; font-size:1rem;'>
    © 2026 КДЛ OLYMPUS • Система учёта расходников
</div>
""", unsafe_allow_html=True)
