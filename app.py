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
# 🎨 CSS VISUAL LEVE
# ========================
st.markdown("""
<style>
.block-container {
    padding-top: 1.2rem;
    padding-left: 1rem;
    padding-right: 1rem;
}

/* melhora cards */
.card {
    background: linear-gradient(145deg, #161B22, #0F1117);
    padding: 18px;
    border-radius: 16px;
    text-align: center;
    margin-bottom: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}
</style>
""", unsafe_allow_html=True)

# ========================
# 💳 CARD
# ========================
def card(titulo, valor, cor="#4F8BF9"):
    st.markdown(f"""
        <div class="card">
            <div style="color:#9CA3AF; font-size:13px;">
                {titulo}
            </div>
            <div style="color:{cor}; font-size:28px; font-weight:700;">
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
# 🔐 GOOGLE SHEETS (CACHEADO)
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

@st.cache_data(ttl=60)
def load_data():
    dados = sheet.get_all_records()
    if dados:
        return pd.DataFrame(dados)
    return pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Valor", "Descrição"])

df = load_data()

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
# FILTRO MÊS (UX MELHOR)
# ========================
if not df.empty:
    meses = sorted(df["Mes"].dropna().unique())
    mes = st.selectbox("📅 Mês", meses, index=len(meses)-1)
    df_filtrado = df[df["Mes"] == mes]
else:
    df_filtrado = df.copy()

# ========================
# 🧭 SIDEBAR LIMPA (APP STYLE)
# ========================
with st.sidebar:
    st.markdown("## 💰 Finanças")
    st.markdown("---")

    menu = st.radio(
        "Menu",
        [
            "➕ Adicionar",
            "📊 Dashboard",
            "📋 Lançamentos",
            "📈 Análises",
            "⚙️ Configurações"
        ]
    )

    st.markdown("---")
    st.caption("Controle financeiro pessoal")

# ========================
# ➕ ADICIONAR
# ========================
if menu == "➕ Adicionar":
    st.title("➕ Nova transação")

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
            st.cache_data.clear()
            st.rerun()

# ========================
# 📊 DASHBOARD
# ========================
if menu == "📊 Dashboard":
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
# 📋 LANÇAMENTOS
# ========================
if menu == "📋 Lançamentos":
    st.title("📋 Lançamentos")

    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True,
        height=550
    )

# ========================
# 📈 ANÁLISES
# ========================
if menu == "📈 Análises":
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

        fig.update_layout(height=450, margin=dict(l=10, r=10, t=30, b=10))

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados no período")

# ========================
# ⚙️ CONFIGURAÇÕES
# ========================
if menu == "⚙️ Configurações":
    st.title("⚙️ Configurações")

    if st.button("⚠️ Apagar todos os dados"):
        senha = st.text_input("Confirme a senha", type="password")

        if senha == st.secrets["app_password"]:
            sheet.clear()
            sheet.append_row(["Data", "Tipo", "Categoria", "Valor", "Descrição"])
            st.success("Dados apagados")
            st.cache_data.clear()
            st.rerun()
