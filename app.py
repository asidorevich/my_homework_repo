import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from pathlib import Path
import zipfile
import io
import shutil
import sqlalchemy as sa
from sqlalchemy import create_engine, text

# ===================== КОНФИГ =====================
st.set_page_config(
    page_title="OLYMPUS 2026 | Управление",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

PHOTO_DIR = "чеки"
os.makedirs(PHOTO_DIR, exist_ok=True)

# ===================== СОВРЕМЕННЫЙ UI/UX =====================
st.markdown("""
<style>
    /* Современная корпоративная / медицинская палитра */
    .main, .stApp {background-color: #f8fafc; color: #334155;}
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}

    /* Стилизация табов */
    div[data-testid="stTabs"] > div[role="tablist"] {
        gap: 10px !important;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 5px;
        margin-bottom: 20px;
    }
    div[data-testid="stTabs"] button {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
        background-color: transparent;
        color: #64748b !important;
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }
    div[data-testid="stTabs"] button:hover {
        background-color: #f1f5f9;
        color: #0ea5e9 !important;
    }
    div[data-testid="stTabs"] button[data-state="active"] {
        background-color: #0ea5e9 !important;
        color: white !important;
        border-color: #0ea5e9;
        box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.2);
    }

    /* Карточки метрик */
    [data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #0ea5e9;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    /* Кнопки */
    .stButton>button[kind="primary"] {
        background-color: #0ea5e9 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(14, 165, 233, 0.3);
        transition: all 0.2s ease;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #0284c7 !important;
        transform: translateY(-1px);
    }
    
    /* Опасные кнопки */
    .btn-danger>button {
        background-color: #ef4444 !important;
        color: white !important;
    }

    /* Заголовки */
    h1, h2, h3 {color: #0f172a;}
    
    .stSidebar {background-color: #ffffff !important; border-right: 1px solid #e2e8f0;}
</style>
""", unsafe_allow_html=True)

# ===================== БАЗА ДАННЫХ =====================
@st.cache_resource
def get_engine():
    # Предполагается, что url базы прописан в .streamlit/secrets.toml
    # Например: db_url = "sqlite:///olympus.db"
    return create_engine(st.secrets.get("db_url", "sqlite:///olympus.db"))

def get_raw(table):
    engine = get_engine()
    # Защита от отсутствия таблицы при первом запуске
    try:
        with engine.connect() as conn:
            return pd.read_sql(f"SELECT * FROM {table}", conn)
    except Exception:
        # Возвращаем пустые датафреймы с нужной структурой
        cols = {
            "purchases": ["date", "item", "category", "qty", "unit", "price", "total", "supplier", "comment", "photo", "added_by"],
            "stock": ["item", "category", "unit", "quantity", "min_qty"],
            "orders": ["item", "qty", "unit", "comment", "ordered_by", "ordered_at", "status"]
        }
        return pd.DataFrame(columns=cols.get(table, []))

def save_raw(table, df):
    with get_engine().connect() as conn:
        df.to_sql(table, conn, if_exists="replace", index=False)
        conn.commit()

def delete_all_from_table(table):
    with get_engine().connect() as conn:
        try:
            conn.execute(text(f"DELETE FROM {table}"))
            conn.commit()
        except Exception:
            pass

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

# ===================== ЛОКАЛИЗАЦИЯ ТАБЛИЦ =====================
def rus(df, kind):
    if df.empty: return df
    maps = {
        "purchases": {
            "rename": {"date":"Дата", "item":"Товар", "category":"Категория", "qty":"Кол-во", "unit":"Ед.изм",
                       "price":"Цена за ед., ₸", "total":"Сумма, ₸", "supplier":"Поставщик",
                       "comment":"Комментарий", "photo":"Чек", "added_by":"Кто добавил"},
            "order": ["Дата","Товар","Категория","Кол-во","Ед.изм","Цена за ед., ₸","Сумма, ₸","Поставщик","Комментарий","Кто добавил"]
        },
        "stock": {
            "rename": {"item":"Товар", "category":"Категория", "unit":"Ед.изм", "quantity":"Остаток", "min_qty":"Минимум"},
            "order": ["Товар","Категория","Ед.изм","Остаток","Минимум"]
        },
        "orders": {
            "rename": {"item":"Товар", "qty":"Кол-во", "unit":"Ед.изм", "comment":"Комментарий",
                       "ordered_by":"Кто заказал", "ordered_at":"Когда", "status":"Статус"},
            "order": ["Когда","Товар","Кол-во","Ед.изм","Комментарий","Кто заказал","Статус"]
        }
    }
    m = maps.get(kind, {"rename":{}, "order":[]})
    df = df.rename(columns=m["rename"])
    return df[[c for c in m["order"] if c in df.columns]]

# ===================== АВТОРИЗАЦИЯ =====================
if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("""
        <div style='text-align:center; margin-bottom: 2rem;'>
            <h1 style='color: #0ea5e9; font-weight: 800;'>OLYMPUS 2026</h1>
            <p style='color: #64748b;'>Система управления складом и закупками</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            role = st.selectbox("Ваша должность", ["Медсестра (Списание)", "Снабжение (Закупки)", "🔐 Администратор"])
            pwd = st.text_input("Пароль", type="password")
            
            if st.button("Войти в систему", use_container_width=True, type="primary"):
                if role == "Медсестра (Списание)" and pwd == "med123":
                    st.session_state.role = "med"
                    st.rerun()
                elif role == "Снабжение (Закупки)" and pwd == "olympus2025":
                    st.session_state.role = "snab"
                    st.rerun()
                elif role == "🔐 Администратор" and pwd == "godmode2026":
                    st.session_state.role = "admin"
                    st.rerun()
                else:
                    st.error("❌ Неверный пароль")
    st.stop()

# ===================== САЙДБАР =====================
with st.sidebar:
    st.markdown("### 🏥 OLYMPUS")
    st.caption(f"Пользователь: **{st.session_state.role.upper()}**")
    st.divider()
    
    # Считаем только реальные покупки (без списаний)
    real_purchases = purchases[purchases["category"] != "Списание"] if not purchases.empty and "category" in purchases.columns else pd.DataFrame()
    total = real_purchases["total"].sum() if not real_purchases.empty and "total" in real_purchases.columns else 0
    
    st.metric("Затраты за все время", f"{total:,.0f} ₸")
    st.divider()

    if st.button("🔄 Обновить данные", use_container_width=True):
        with st.spinner("Синхронизация..."):
            load_all_data(force=True)
        st.toast("Данные успешно обновлены", icon="✅")
        st.rerun()

    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.role = None
        st.rerun()

# ===================== ПАНЕЛЬ: МЕДСЕСТРА =====================
if st.session_state.role == "med":
    t1, t2, t3, t4 = st.tabs(["🏠 Дашборд", "📦 Остатки", "📉 Списание", "📨 Заявка на закуп"])

    with t1:
        st.subheader("Главная панель склада")
        if not stock.empty:
            crit = stock[stock["quantity"] <= stock["min_qty"]]
            col1, col2, col3 = st.columns(3)
            col1.metric("Критически мало", len(crit))
            col2.metric("Всего позиций", len(stock))
            col3.metric("Общий остаток единиц", f"{stock['quantity'].sum():,.0f}")
            
            if not crit.empty:
                st.error(f"⚠️ **Внимание! Заканчиваются товары ({len(crit)} шт.):**")
                for _, row in crit.iterrows():
                    st.write(f"— {row['item']} (Осталось: **{row['quantity']} {row['unit']}**)")
        else:
            st.info("Склад пока пуст.")

    with t2:
        st.subheader("Текущие остатки")
        q = st.text_input("🔍 Быстрый поиск товара", placeholder="Введите название...")
        df = stock.copy()
        if q and not df.empty: 
            df = df[df["item"].str.contains(q, case=False, na=False)]
        st.dataframe(rus(df, "stock"), use_container_width=True, hide_index=True)

    with t3:
        st.subheader("Списание материалов")
        if stock.empty:
            st.warning("Нет товаров для списания.")
        else:
            with st.form("spis", clear_on_submit=True):
                item = st.selectbox("Выберите товар", options=sorted(stock["item"]))
                current_qty = float(stock.loc[stock["item"] == item, "quantity"].iloc[0])
                unit = stock.loc[stock["item"] == item, "unit"].iloc[0]
                
                st.info(f"Доступно на складе: **{current_qty} {unit}**")
                
                qty = st.number_input("Сколько списать?", min_value=0.1, max_value=current_qty, step=1.0)
                com = st.text_input("Пациент / Цель списания")
                
                if st.form_submit_button("Подтвердить списание", type="primary", use_container_width=True):
                    # Обновляем остаток
                    stock.loc[stock["item"] == item, "quantity"] -= qty
                    save_raw("stock", stock)
                    
                    # Записываем в историю как "Списание" (с ценой 0)
                    new = pd.DataFrame([{
                        "date": date.today().strftime("%Y-%m-%d"), 
                        "item": f"[СПИСАНО] {item}",
                        "category": "Списание", "qty": qty, "unit": unit,
                        "price": 0, "total": 0, "supplier": "-", "comment": com, 
                        "photo": "", "added_by": "Медсестра"
                    }])
                    
                    # Используем dropna(axis=1, how='all') чтобы избежать предупреждений Pandas
                    save_raw("purchases", pd.concat([purchases, new], ignore_index=True))
                    load_all_data(force=True)
                    st.success(f"✅ Успешно списано {qty} {unit} товара '{item}'")

    with t4:
        st.subheader("Создать заявку снабжению")
        with st.form("order", clear_on_submit=True):
            item = st.text_input("Что нужно купить?", placeholder="Например: Перчатки нитриловые размер M")
            col1, col2 = st.columns(2)
            qty = col1.number_input("Количество", min_value=1, step=1)
            unit = col2.selectbox("Ед. изм.", ["шт", "упак", "коробка", "литр", "пара", "рулон"])
            com = st.text_area("Дополнительный комментарий")
            
            if st.form_submit_button("Отправить заявку", type="primary", use_container_width=True):
                if not item.strip():
                    st.error("Укажите наименование товара")
                else:
                    new_o = pd.DataFrame([{
                        "item": item.strip(), "qty": qty, "unit": unit, "comment": com,
                        "ordered_by": "Медсестра",
                        "ordered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "status": "new"
                    }])
                    save_raw("orders", pd.concat([orders, new_o], ignore_index=True))
                    load_all_data(force=True)
                    st.success("✅ Заявка успешно отправлена в отдел снабжения!")

# ===================== ПАНЕЛЬ: СНАБЖЕНИЕ =====================
elif st.session_state.role == "snab":
    t1, t2, t3, t4, t5 = st.tabs(["📨 Заявки и Дефицит", "🛒 Внести закупку", "📦 Склад", "📈 Финансы", "📎 Документы"])

    with t1:
        colA, colB = st.columns(2)
        with colA:
            st.subheader("Новые заявки от клиники")
            pending = orders[orders["status"] == "new"] if not orders.empty else pd.DataFrame()
            if pending.empty:
                st.info("Нет активных заявок от медсестер.")
            else:
                for idx, row in pending.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{row['item']}** — {row['qty']} {row['unit']}")
                        st.caption(f"От: {row['ordered_by']} | {row['ordered_at']}")
                        if row.get('comment'): st.write(f"💬 {row['comment']}")
                        
                        c1, c2 = st.columns(2)
                        if c1.button("Принято", key=f"done_{idx}", type="primary", use_container_width=True):
                            orders.loc[idx, "status"] = "done"
                            save_raw("orders", orders)
                            load_all_data(force=True)
                            st.rerun()
                        if c2.button("Отклонить", key=f"rej_{idx}", use_container_width=True):
                            orders.loc[idx, "status"] = "rejected"
                            save_raw("orders", orders)
                            load_all_data(force=True)
                            st.rerun()
        
        with colB:
            st.subheader("Дефицит на складе (Автоматически)")
            crit = stock[stock["quantity"] <= stock["min_qty"]] if not stock.empty else pd.DataFrame()
            if crit.empty:
                st.success("Склад укомплектован, дефицита нет.")
            else:
                st.dataframe(rus(crit, "stock"), use_container_width=True, hide_index=True)

    with t2:
        st.subheader("Оформление новой закупки")
        with st.form("buy", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                item = st.text_input("Название товара")
                cat = st.selectbox("Категория", ["Расходный материал", "Реагенты", "Канцелярия", "Хозтовары", "Оборудование", "Прочее"])
                qty = st.number_input("Количество", min_value=1.0)
                unit = st.selectbox("Ед.изм.", ["шт", "упак", "коробка", "литр", "рулон"])
            with col2:
                price = st.number_input("Цена за единицу, ₸", min_value=0.0)
                supplier = st.text_input("Поставщик (Контрагент)")
                no_track = st.checkbox("Не приходовать на склад (сразу в расход/услуги)")
                files = st.file_uploader("Прикрепить чек/счет (PDF/JPG)", accept_multiple_files=True)
            
            if st.form_submit_button("Внести закупку в базу", type="primary", use_container_width=True):
                if not item:
                    st.error("Введите название товара")
                else:
                    total_price = qty * price
                    paths = []
                    if files:
                        for f in files:
                            safe_name = f"{date.today()}_{f.name}".replace(" ", "_")
                            safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
                            path = os.path.join(PHOTO_DIR, safe_name)
                            with open(path, "wb") as out: out.write(f.getbuffer())
                            paths.append(path)
                    
                    new_row = pd.DataFrame([{
                        "date": date.today().strftime("%Y-%m-%d"), "item": item, "category": cat,
                        "qty": qty, "unit": unit, "price": price, "total": total_price,
                        "supplier": supplier, "comment": "НЕ НА СКЛАДЕ" if no_track else "",
                        "photo": ";".join(paths), "added_by": "Снабжение"
                    }])
                    
                    save_raw("purchases", pd.concat([purchases, new_row], ignore_index=True))
                    
                    if not no_track:
                        if not stock.empty and item in stock["item"].values:
                            stock.loc[stock["item"] == item, "quantity"] += qty
                        else:
                            new_stock = pd.DataFrame([{"item":item, "category":cat, "unit":unit, "quantity":qty, "min_qty":5}])
                            stock = pd.concat([stock, new_stock], ignore_index=True) if not stock.empty else new_stock
                        save_raw("stock", stock)
                    
                    load_all_data(force=True)
                    st.success("✅ Закупка сохранена и склад обновлен!")

    with t3:
        st.subheader("Управление складом")
        st.caption("Здесь вы можете вручную откорректировать остатки после инвентаризации.")
        edited = st.data_editor(rus(stock.copy(), "stock"), use_container_width=True, num_rows="dynamic")
        if st.button("💾 Сохранить изменения склада", type="primary"):
            rev_map = {"Товар":"item","Категория":"category","Ед.изм":"unit","Остаток":"quantity","Минимум":"min_qty"}
            save_raw("stock", edited.rename(columns=rev_map))
            load_all_data(force=True)
            st.success("✅ Остатки сохранены!")

    with t4:
        st.subheader("Финансовая аналитика")
        # Исключаем "Списание" из финансовой аналитики
        real_purch = purchases[purchases["category"] != "Списание"].copy() if not purchases.empty else pd.DataFrame()
        
        if real_purch.empty:
            st.info("Нет данных о закупках для анализа.")
        else:
            real_purch["date_dt"] = pd.to_datetime(real_purch["date"], errors="coerce")
            real_purch = real_purch.dropna(subset=["date_dt"])
            
            col1, col2 = st.columns([1, 3])
            years = sorted(real_purch["date_dt"].dt.year.unique(), reverse=True)
            selected_year = col1.selectbox("Год", options=years)
            
            months_available = sorted(real_purch[real_purch["date_dt"].dt.year == selected_year]["date_dt"].dt.month.unique())
            month_names = [date(1900, m, 1).strftime("%B") for m in months_available]
            selected_month_name = col2.selectbox("Месяц", options=month_names)
            selected_month = months_available[month_names.index(selected_month_name)]
            
            selected_period = f"{selected_year}-{selected_month:02d}"
            month_data = real_purch[real_purch["date_dt"].dt.strftime("%Y-%m") == selected_period]
            
            total_spent = month_data["total"].sum()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Потрачено за месяц", f"{total_spent:,.0f} ₸")
            c2.metric("Кол-во закупок", len(month_data))
            c3.metric("Средний чек", f"{(total_spent / len(month_data)) if len(month_data) > 0 else 0:,.0f} ₸")
            c4.metric("Уникальных товаров", month_data["item"].nunique())
            
            st.markdown("---")
            st.write("#### Структура расходов (Категории)")
            cat_sum = month_data.groupby("category")["total"].sum().sort_values(ascending=False)
            st.bar_chart(cat_sum, color="#0ea5e9", use_container_width=True)

    with t5:
        st.subheader("Архив документов и чеков")
        files = sorted(Path(PHOTO_DIR).iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:20]
        if not files:
            st.info("Документов пока нет.")
        else:
            cols = st.columns(4)
            for i, f in enumerate(files):
                with cols[i % 4]:
                    st.caption(f.name[:25] + "...")
                    if f.suffix.lower() in [".png",".jpg",".jpeg"]:
                        st.image(str(f), use_container_width=True)
                    else:
                        with open(f, "rb") as pdf_file:
                            st.download_button("Скачать PDF", pdf_file.read(), file_name=f.name, key=f"dl_{f.name}")

# ===================== ПАНЕЛЬ: АДМИНИСТРАТОР =====================
else:
    st.markdown("<h2 style='color: #ef4444;'>🛠️ Панель Администратора (GOD MODE)</h2>", unsafe_allow_html=True)
    atabs = st.tabs(["📊 Обзор системы", "✏️ Редактор таблиц", "💾 Бэкап", "⚠️ Опасная зона"])

    with atabs[0]:
        c1, c2, c3 = st.columns(3)
        c1.metric("Всего строк закупок", len(purchases))
        c2.metric("Уникальных позиций склада", len(stock))
        c3.metric("Всего заявок", len(orders))

    with atabs[1]:
        st.info("Здесь можно напрямую редактировать таблицы БД. Осторожно!")
        table_choice = st.selectbox("Выберите таблицу", ["purchases", "stock", "orders"])
        df_edit = st.data_editor(get_raw(table_choice), num_rows="dynamic", use_container_width=True)
        if st.button("💾 Принудительно сохранить в БД", type="primary"):
            save_raw(table_choice, df_edit)
            load_all_data(force=True)
            st.success("Данные перезаписаны!")

    with atabs[2]:
        st.subheader("Создание резервной копии")
        st.write("Скачивает все таблицы в CSV и архив с чеками.")
        if st.button("📦 Сгенерировать ZIP-архив", type="primary"):
            with st.spinner("Создание архива..."):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for t in ["purchases", "stock", "orders"]:
                        zf.writestr(f"{t}.csv", get_raw(t).to_csv(index=False))
                    for f in Path(PHOTO_DIR).glob("*"):
                        zf.write(f, f"чеки/{f.name}")
                zip_buffer.seek(0)
            st.download_button("⬇️ Скачать backup.zip", zip_buffer.getvalue(),
                               f"OLYMPUS_BACKUP_{date.today()}.zip", "application/zip", use_container_width=True)

    with atabs[3]:
        st.error("Внимание! Действия ниже необратимы.")
        table_to_clear = st.selectbox("Очистить таблицу", ["purchases", "stock", "orders"])
        if st.button(f"🗑 ОЧИСТИТЬ {table_to_clear.upper()}"):
            delete_all_from_table(table_to_clear)
            load_all_data(force=True)
            st.success(f"Таблица {table_to_clear} очищена.")
            
        st.divider()
        st.write("#### Полный сброс системы")
        confirm1 = st.text_input("Введите 'УДАЛИТЬ ВСЕ' для подтверждения")
        if st.button("☢️ УНИЧТОЖИТЬ БАЗУ И ФАЙЛЫ"):
            if confirm1 == "УДАЛИТЬ ВСЕ":
                for t in ["purchases", "stock", "orders"]: delete_all_from_table(t)
                if os.path.exists(PHOTO_DIR):
                    shutil.rmtree(PHOTO_DIR)
                    os.makedirs(PHOTO_DIR)
                load_all_data(force=True)
                st.success("Система сброшена до заводских настроек.")
            else:
                st.warning("Неверное слово подтверждения.")

st.markdown("""
<div style='text-align:center; padding:40px 0 20px; color:#94a3b8; font-size:0.9rem;'>
    © 2026 Система управления «OLYMPUS» v2.0
</div>
""", unsafe_allow_html=True)
