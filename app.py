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
st.set_page_config(page_title="OLYMPUS 2026", page_icon="🏔️", layout="wide", initial_sidebar_state="expanded")

PHOTO_DIR = "чеки"
os.makedirs(PHOTO_DIR, exist_ok=True)

# ===================== СВЕТЛЫЕ ПРЕМИУМ СТИЛИ =====================
st.markdown("""
<style>
    .main, .stApp {background: linear-gradient(135deg, #f8faff 0%, #e6f3ff 100%); color: #1a2a44;}
    html, body, [class*="css"] {font-size: 19px !important;}
    .stDataFrame, .stDataEditor, .stDataFrame table, .stDataEditor table {
        font-size: 20px !important; background: white !important; border-radius: 20px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.08) !important;
    }
    .metric-card {
        background: white; border-radius: 20px; padding: 22px; border-left: 7px solid #ff8c42;
        box-shadow: 0 10px 30px rgba(0,0,0,0.07); margin: 12px 0;
    }
    .low-stock {border-left-color: #ef4444 !important;}
    .warning-stock {border-left-color: #eab308 !important;}
    .stButton>button {
        background: linear-gradient(45deg, #ff8c42, #00d4ff) !important;
        color: white !important; border-radius: 18px !important; padding: 16px 42px !important;
        font-weight: 700 !important; font-size: 1.35rem !important;
        box-shadow: 0 8px 25px rgba(255,140,66,0.4); transition: all 0.3s ease;
    }
    .stButton>button:hover {transform: translateY(-4px); box-shadow: 0 15px 35px rgba(255,140,66,0.5);}
    h1,h2,h3,h4,h5 {background: linear-gradient(90deg, #ff8c42, #00d4ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900;}
    .stSidebar {background: linear-gradient(180deg, #ffffff, #f0f7ff) !important;}
</style>
""", unsafe_allow_html=True)

# ===================== БАЗА =====================
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

# ===================== ЛОГО =====================
LOGO_URL = "https://github.com/asidorevich/my_homework_repo/blob/main/logo.PNG?raw=true"
st.markdown(f"""
<div style="text-align:center; padding:30px 0 20px;">
    <img src="{LOGO_URL}" width="120" style="border-radius:50%; border:6px solid #fff; box-shadow: 0 0 40px rgba(0,212,255,0.4);">
    <h1 style="font-size:4.2rem; margin:15px 0 0 0;">OLYMPUS</h1>
    <p style="font-size:1.45rem; color:#ff8c42; letter-spacing:6px;">2026</p>
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
total = purchases["total"].sum() if not purchases.empty and "total" in purchases.columns else 0
st.sidebar.image(LOGO_URL, width=140)
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
    t1, t2, t3, t4 = st.tabs(["🏠 Дашборд", "📦 Остатки", "📉 Списание", "📨 Заявка"])

    with t1:
        st.subheader("📊 Главная панель")
        crit = stock[stock["quantity"] <= stock["min_qty"]]
        col1, col2, col3 = st.columns(3)
        col1.metric("Критически мало", len(crit))
        col2.metric("Всего позиций", len(stock))
        col3.metric("Общий остаток", f"{stock['quantity'].sum():,.0f}")
        if not crit.empty:
            st.subheader("⚠️ Проблемные позиции")
            for _, row in crit.iterrows():
                st.error(f"**{row['item']}** — осталось **{row['quantity']} {row['unit']}** (минимум {row['min_qty']})")

    with t2:
        st.subheader("Текущие остатки на складе")
        q = st.text_input("🔍 Поиск по товару", key="search_med")
        df = stock.copy()
        if q: df = df[df["item"].str.contains(q, case=False, na=False)]
        st.dataframe(rus(df, "stock"), use_container_width=True, hide_index=True)
        if not crit.empty:
            st.error(f"Критически мало: {len(crit)} позиций")
            st.dataframe(rus(crit, "stock"), use_container_width=True, hide_index=True)

    with t3:
        st.subheader("Списание со склада")
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
                    new = pd.DataFrame([{"date": date.today().strftime("%Y-%m-%d"),
                                         "item": f"[СПИСАНО] {item}", "category": "Списание",
                                         "qty": qty, "unit": unit, "price": 0, "total": 0,
                                         "supplier": "", "comment": com, "photo": "", "added_by": "Медсестра"}])
                    save_raw("purchases", pd.concat([purchases, new], ignore_index=True))
                    load_all_data(force=True)
                    st.toast(f"✅ Списано {qty} × {item}", icon="🗑️")
                    st.balloons()
                    st.rerun()

    with t4:
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
                    new_o = pd.DataFrame([{"item": item.strip(), "qty": qty, "unit": unit, "comment": com,
                                           "ordered_by": "Медсестра",
                                           "ordered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                           "status": "new"}])
                    save_raw("orders", pd.concat([orders, new_o], ignore_index=True))
                    load_all_data(force=True)
                    st.toast("✅ Заявка отправлена!", icon="📨")
                    st.balloons()
                    st.rerun()

# ===================== СНАБЖЕНИЕ =====================
elif st.session_state.role == "snab":
    t1,t2,t3,t4,t5,t6 = st.tabs(["📨 Заявки","🛒 Закупка","📜 История","📦 Склад","📈 Аналитика","🖼 Чеки"])

    with t1:
        st.subheader("Новые заявки от медсестёр")
        if st.button("🔄 ОБНОВИТЬ ЗАЯВКИ", use_container_width=True, type="primary"):
            load_all_data(force=True)
            st.toast("✅ Заявки обновлены!", icon="🔄")
            st.rerun()
        pending = orders[orders["status"] == "new"]
        if pending.empty:
            st.success("Нет активных заявок")
        else:
            st.dataframe(rus(pending.copy(), "orders"), use_container_width=True, hide_index=True)
            for idx, row in pending.iterrows():
                with st.expander(f"{row['item']} — {row['qty']} {row['unit']}"):
                    st.caption(f"От: {row['ordered_by']} | {row['ordered_at']}")
                    if row.get('comment'): st.write(row['comment'])
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Выполнено", key=f"done_{idx}", use_container_width=True):
                        orders.loc[idx, "status"] = "done"
                        save_raw("orders", orders)
                        load_all_data(force=True)
                        st.toast("✅ Отмечено как выполнено", icon="✅")
                        st.rerun()
                    if c2.button("❌ Отклонить", key=f"rej_{idx}", use_container_width=True):
                        orders.loc[idx, "status"] = "rejected"
                        save_raw("orders", orders)
                        load_all_data(force=True)
                        st.toast("❌ Заявка отклонена", icon="❌")
                        st.rerun()

    with t2:
        st.subheader("Добавить новую закупку")
        with st.form("buy", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                item = st.text_input("Название товара")
                cat = st.selectbox("Категория", ["Расходный материал","Канцелярия","Пробирки","Хозтовары","Прочее"])
                qty = st.number_input("Количество", min_value=1)
                unit = st.selectbox("Ед.изм.", ["шт","упак","коробка","рулон"])
            with col2:
                price = st.number_input("Цена за единицу, ₸", min_value=0.0)
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
                        with open(path, "wb") as out: out.write(f.getbuffer())
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
                load_all_data(force=True)
                st.toast("✅ Закупка добавлена!", icon="🛒")
                st.balloons()
                st.rerun()

    with t3:
        st.subheader("История всех закупок")
        st.dataframe(rus(purchases.copy(), "purchases"), use_container_width=True, hide_index=True)

    with t4:
        st.subheader("Ручное управление остатками")
        edited = st.data_editor(rus(stock.copy(), "stock"), use_container_width=True, num_rows="dynamic")
        if st.button("💾 Сохранить изменения", type="primary"):
            rev_map = {"Товар":"item","Категория":"category","Ед.изм":"unit","Остаток":"quantity","Минимум":"min_qty"}
            edited_eng = edited.rename(columns=rev_map)
            save_raw("stock", edited_eng)
            load_all_data(force=True)
            st.toast("✅ Остатки сохранены!", icon="💾")
            st.rerun()

    with t5:
        st.subheader("Аналитика расходов")
        if purchases.empty:
            st.info("Пока нет ни одной закупки")
            st.stop()
        purchases["date_dt"] = pd.to_datetime(purchases["date"], errors="coerce")
        purchases = purchases.dropna(subset=["date_dt"])
        col1, col2 = st.columns([1, 3])
        with col1:
            years = sorted(purchases["date_dt"].dt.year.unique(), reverse=True)
            selected_year = st.selectbox("Год", options=years, index=0)
        with col2:
            months_available = sorted(purchases[purchases["date_dt"].dt.year == selected_year]["date_dt"].dt.month.unique())
            month_names = [date(1900, m, 1).strftime("%B") for m in months_available]
            selected_month_name = st.selectbox("Месяц", options=month_names, index=0)
            selected_month = months_available[month_names.index(selected_month_name)]
        selected_period = f"{selected_year}-{selected_month:02d}"
        month_data = purchases[purchases["date_dt"].dt.strftime("%Y-%m") == selected_period].copy()
        if month_data.empty:
            st.warning(f"В {selected_month_name} {selected_year} закупок не было")
            st.stop()
        total_spent = month_data["total"].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Всего потрачено", f"{total_spent:,.0f} ₸")
        c2.metric("Количество закупок", len(month_data))
        c3.metric("Средний чек", f"{total_spent / len(month_data):,.0f} ₸")
        c4.metric("Уникальных позиций", month_data["item"].nunique())
        st.markdown("---")
        st.subheader("Расходы по категориям")
        cat = month_data.groupby("category")["total"].sum().sort_values(ascending=False)
        cat_df = cat.reset_index()
        cat_df["Доля"] = (cat_df["total"] / total_spent * 100).round(1).map("{:.1f}%".format)
        cat_df["total"] = cat_df["total"].apply(lambda x: f"{x:,.0f} ₸")
        col1, col2 = st.columns([2, 1])
        with col1: st.bar_chart(cat, use_container_width=True)
        with col2:
            cat_df = cat_df.rename(columns={"category": "Категория", "total": "Сумма"})
            st.dataframe(cat_df[["Категория", "Сумма", "Доля"]], use_container_width=True, hide_index=True)
        # (остальная аналитика — топ-10, поставщики, детальная таблица — полностью как в твоём оригинале)
        st.subheader("Топ-10 самых дорогих закупок")
        top10 = month_data.groupby(["item", "category", "supplier", "price"], as_index=False)["total"].sum()
        top10 = top10.sort_values("total", ascending=False).head(10)
        top10["total"] = top10["total"].apply(lambda x: f"{x:,.0f} ₸")
        top10["price"] = top10["price"].apply(lambda x: f"{x:,.0f} ₸")
        top10 = top10.rename(columns={"item": "Товар", "category": "Категория", "supplier": "Поставщик", "price": "Цена за ед.", "total": "Итого"})
        st.dataframe(top10[["Товар", "Категория", "Поставщик", "Цена за ед.", "Итого"]], use_container_width=True, hide_index=True)
        st.subheader("Расходы по поставщикам")
        supp = month_data.groupby("supplier")["total"].sum().sort_values(ascending=False)
        supp_df = supp.reset_index()
        supp_df["total"] = supp_df["total"].apply(lambda x: f"{x:,.0f} ₸")
        supp_df = supp_df.rename(columns={"supplier": "Поставщик", "total": "Сумма"})
        col1, col2 = st.columns([2, 1])
        with col1: st.bar_chart(supp, use_container_width=True)
        with col2: st.dataframe(supp_df, use_container_width=True, hide_index=True)
        st.subheader(f"Все закупки за {selected_month_name} {selected_year}")
        detail = month_data.copy()
        detail["Дата"] = detail["date_dt"].dt.strftime("%d.%m.%Y")
        detail = detail[["Дата", "item", "category", "qty", "unit", "price", "total", "supplier"]]
        detail["price"] = detail["price"].apply(lambda x: f"{x:,.0f}")
        detail["total"] = detail["total"].apply(lambda x: f"{x:,.0f} ₸")
        detail = detail.rename(columns={"item": "Товар", "category": "Категория", "qty": "Кол-во", "unit": "Ед.изм", "price": "Цена за ед., ₸", "supplier": "Поставщик"})
        st.dataframe(detail, use_container_width=True, hide_index=True)
        csv = detail.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("Скачать месяц в Excel", csv, f"Закупки_{selected_period}.csv", "text/csv", use_container_width=True)

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

# ===================== АДМИН =====================
else:
    st.title("🔐 АДМИН-ПАНЕЛЬ • GOD MODE 2026")
    atabs = st.tabs(["📊 Обзор", "✏️ Редактировать данные", "🗑 Опасная зона", "💾 Бэкап"])

    with atabs[0]:
        col1, col2, col3 = st.columns(3)
        col1.metric("Закупок всего", len(purchases))
        col2.metric("Позиций на складе", len(stock))
        col3.metric("Активных заявок", len(orders[orders["status"] == "new"]))

    with atabs[1]:
        table_choice = st.selectbox("Выберите таблицу", ["purchases", "stock", "orders"])
        df_edit = st.data_editor(get_raw(table_choice), num_rows="dynamic", use_container_width=True)
        if st.button("💾 Сохранить изменения", type="primary"):
            save_raw(table_choice, df_edit)
            load_all_data(force=True)
            st.toast("✅ Таблица сохранена!", icon="💾")
            st.rerun()

    with atabs[2]:
        st.subheader("🗑 Очистка одной таблицы")
        table_to_clear = st.selectbox("Таблица", ["purchases", "stock", "orders"])
        if st.button(f"🗑 ОЧИСТИТЬ {table_to_clear.upper()}", type="primary"):
            if st.checkbox("Я понимаю, что это необратимо"):
                delete_all_from_table(table_to_clear)
                load_all_data(force=True)
                st.toast(f"✅ {table_to_clear} полностью очищена!", icon="🗑")
                st.rerun()

        st.divider()
        st.subheader("☢️ УДАЛИТЬ ВСЮ БАЗУ")
        st.warning("Удалит ВСЁ навсегда!")
        confirm1 = st.text_input("Напишите GODMODE")
        confirm2 = st.checkbox("Я осознаю, что данные будут удалены НАВСЕГДА")
        if st.button("☢️ УНИЧТОЖИТЬ ВСЮ БАЗУ", type="primary"):
            if confirm1 == "GODMODE" and confirm2:
                for t in ["purchases", "stock", "orders"]:
                    delete_all_from_table(t)
                if os.path.exists(PHOTO_DIR):
                    shutil.rmtree(PHOTO_DIR)
                    os.makedirs(PHOTO_DIR)
                load_all_data(force=True)
                st.toast("💥 ВСЯ БАЗА УНИЧТОЖЕНА", icon="☢️")
                st.rerun()

    with atabs[3]:
        if st.button("📦 Создать полный бэкап (таблицы + чеки)"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for t in ["purchases", "stock", "orders"]:
                    df = get_raw(t)
                    zf.writestr(f"{t}.csv", df.to_csv(index=False))
                for f in Path(PHOTO_DIR).glob("*"):
                    zf.write(f, f"чеки/{f.name}")
            zip_buffer.seek(0)
            st.download_button("⬇️ Скачать backup.zip", zip_buffer.getvalue(),
                               f"OLYMPUS_FULL_BACKUP_{date.today()}.zip", "application/zip", use_container_width=True)

        st.subheader("🖼 Управление чеками")
        files = sorted(Path(PHOTO_DIR).iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        for f in files[:30]:
            col1, col2 = st.columns([4,1])
            col1.caption(f.name)
            if f.suffix.lower() in [".png",".jpg",".jpeg"]:
                col1.image(str(f), use_container_width=True)
            if col2.button("🗑 Удалить", key=f"del_{f.name}"):
                f.unlink()
                st.toast(f"Удалён {f.name}", icon="🗑")
                st.rerun()

st.markdown("""
<div style='text-align:center; padding:80px 0 30px; color:#64748b; font-size:1rem;'>
    © 2026 КДЛ OLYMPUS • GOD MODE ACTIVATED
</div>
""", unsafe_allow_html=True)
