import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ========================
# CONFIG
# ========================
st.set_page_config(page_title="Controle Financeiro", layout="wide")

# ========================
# 📱 MOBILE-FIRST CSS + BOTTOM NAV
# ========================
st.markdown("""
<style>

.block-container {
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
    padding-bottom: 80px; /* espaço para bottom nav */
}

/* CARD */
.card {
    background-color: #161B22;
    padding: 16px;
    border-radius: 14px;
    text-align: center;
    margin-bottom: 10px;
}

/* BOTTOM NAV */
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 65px;
    background-color: #161B22;
    display: flex;
    justify-content: space-around;
    align-items: center;
    border-top: 1px solid #2A2F3A;
    z-index: 9999;
}

.nav-item {
    text-decoration: none;
    font-size: 22px;
    color: #9CA3AF;
}

.nav-item.active {
    color: #4F8BF9;
}

</style>
""", unsafe_allow_html=True)

# ========================
# 💳 CARD FUNCTION
# ========================
def card(titulo, valor, cor="#4F8BF9"):
    st.markdown(f"""
        <div class="card">
            <div style="color:#9CA3AF; font-size:14px;">{titulo}</div>
            <div style="color:{cor}; font-size:26px; font-weight:600;">
                {valor}
            </div>
        </div>
    """, unsafe_allow_html=True)

# ========================
# 🔒 LOGIN
# ========================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acesso restrito")
    senha = st.text_input("Senha", type="password")

    if senha == st.secrets["app_password"]:
        st.session_state.autenticado = True
        st.rerun()
    else:
        st.warning("Digite a senha para acessar")
        st.stop()

# ========================
# 🔐 GOOGLE SHEETS
# ========================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"],
    scope
)

client = gspread.authorize(creds)
sheet = client.open("Controle Financeiro").sheet1

# ========================
# 📥 DADOS
# ========================
dados = sheet.get_all_records()

if dados:
    df = pd.DataFrame(dados)
else:
    df = pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Valor", "Descrição"])

# ========================
# 🔧 TRATAMENTO
# ========================
df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
df["Tipo"] = df["Tipo"].astype(str).str.strip()
df["Categoria"] = df["Categoria"].astype(str).str.strip()
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
df["Mes"] = df["Data"].dt.to_period("M").astype(str)

# ========================
# VARIÁVEIS
# ========================
CATEGORIAS = {
    "Receita": ["Salário", "Outros"],
    "Despesa": ["Aluguel", "Energia", "Água", "Lazer", "Financiamento", "Carro", "Internet"]
}

# ========================
# FILTRO
# ========================
if not df.empty:
    meses = df["Mes"].dropna().drop_duplicates().sort_values()
    mes_atual_str = datetime.today().strftime("%Y-%m")

    mes = st.selectbox(
        "📅 Mês",
        meses,
        index=list(meses).index(mes_atual_str) if mes_atual_str in list(meses) else 0
    )

    df_filtrado = df[df["Mes"] == mes]
else:
    df_filtrado = df.copy()

# ========================
# 🧭 BOTTOM NAV STATE
# ========================
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

# clique via query params (opcional)
query = st.query_params
if "page" in query:
    st.session_state.page = query["page"][0]

page = st.session_state.page

# ========================
# 📱 BOTTOM NAV
# ========================
st.markdown(f"""
<div class="bottom-nav">
    <a class="nav-item {'active' if page=='dashboard' else ''}" href="?page=dashboard">📊</a>
    <a class="nav-item {'active' if page=='add' else ''}" href="?page=add">➕</a>
    <a class="nav-item {'active' if page=='list' else ''}" href="?page=list">📋</a>
    <a class="nav-item {'active' if page=='stats' else ''}" href="?page=stats">📈</a>
    <a class="nav-item {'active' if page=='settings' else ''}" href="?page=settings">⚙️</a>
</div>
""", unsafe_allow_html=True)

# ========================
# ➕ ADICIONAR
# ========================
if page == "add":
    st.title("➕ Adicionar transação")

    tipo = st.selectbox("Tipo", ["Receita", "Despesa"])

    with st.form("form"):
        col1, col2 = st.columns(2)

        with col1:
            data = st.date_input("Data", datetime.today())

        with col2:
            categoria = st.selectbox("Categoria", CATEGORIAS[tipo])
            valor = st.number_input("Valor", min_value=0.0, format="%.2f")

        descricao = st.text_input("Descrição")

        submit = st.form_submit_button("Adicionar")

    if submit:
        if valor > 0:
            sheet.append_row([
                str(data),
                tipo,
                categoria,
                float(valor),
                descricao
            ])
            st.success("Transação adicionada!")
            st.rerun()

# ========================
# 📊 DASHBOARD
# ========================
if page == "dashboard":
    st.title("📊 Dashboard")

    receitas = df[df["Tipo"] == "Receita"]["Valor"].sum()
    despesas = df[df["Tipo"] == "Despesa"]["Valor"].sum()
    saldo = receitas - despesas

    c1, c2, c3 = st.columns(3)
    with c1:
        card("Receitas", f"R$ {receitas:.2f}", "#22C55E")
    with c2:
        card("Despesas", f"R$ {despesas:.2f}", "#EF4444")
    with c3:
        card("Saldo", f"R$ {saldo:.2f}", "#3B82F6")

    st.divider()

    receitas_mes = df_filtrado[df_filtrado["Tipo"] == "Receita"]["Valor"].sum()
    despesas_mes = df_filtrado[df_filtrado["Tipo"] == "Despesa"]["Valor"].sum()
    saldo_mes = receitas_mes - despesas_mes

    c1, c2, c3 = st.columns(3)
    with c1:
        card("Receitas (mês)", f"R$ {receitas_mes:.2f}", "#22C55E")
    with c2:
        card("Despesas (mês)", f"R$ {despesas_mes:.2f}", "#EF4444")
    with c3:
        card("Saldo (mês)", f"R$ {saldo_mes:.2f}", "#3B82F6")

# ========================
# 📋 LISTA
# ========================
if page == "list":
    st.title("📋 Lançamentos")

    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True,
        height=500
    )

# ========================
# 📈 STATS
# ========================
if page == "stats":
    st.title("📈 Análises")

    despesas_df = df_filtrado[df_filtrado["Tipo"] == "Despesa"]

    if not despesas_df.empty:
        resumo = despesas_df.groupby("Categoria", as_index=False)["Valor"].sum()

        fig = px.bar(
            resumo,
            x="Categoria",
            y="Valor",
            text="Valor"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados no período")

# ========================
# ⚙️ CONFIG
# ========================
if page == "settings":
    st.title("⚙️ Configurações")

    if st.button("⚠️ Apagar todos os dados"):
        senha = st.text_input("Confirme a senha", type="password")

        if senha == st.secrets["app_password"]:
            sheet.clear()
            sheet.append_row(["Data", "Tipo", "Categoria", "Valor", "Descrição"])
            st.success("Dados apagados")
            st.rerun()
