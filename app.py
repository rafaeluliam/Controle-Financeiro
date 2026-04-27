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
# 🎨 CSS BÁSICO
# ========================
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ========================
# 💳 CARD
# ========================
def card(titulo, valor, cor="#4F8BF9"):
    st.markdown(f"""
        <div style="
            background-color:#161B22;
            padding:18px;
            border-radius:14px;
            text-align:center;
            margin-bottom:10px;
        ">
            <div style="color:#9CA3AF; font-size:14px;">{titulo}</div>
            <div style="color:{cor}; font-size:28px; font-weight:600;">
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

CONTAS_FIXAS = [
    {"nome": "Aluguel", "categoria": "Aluguel"},
    {"nome": "Energia", "categoria": "Energia"},
    {"nome": "Água", "categoria": "Água"},
    {"nome": "Financiamento", "categoria": "Financiamento"},
    {"nome": "Internet", "categoria": "Internet"},
]

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
# 🧭 SIDEBAR (APP STYLE)
# ========================
st.sidebar.title("💰 Financeiro")

menu = st.sidebar.radio(
    "Navegação",
    [
        "📊 Dashboard",
        "➕ Adicionar",
        "📋 Lançamentos",
        "📈 Análises",
        "⚙️ Configurações"
    ]
)

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

    st.subheader("📅 Mês selecionado")

    receitas_mes = df_filtrado[df_filtrado["Tipo"] == "Receita"]["Valor"].sum()
    despesas_mes = df_filtrado[df_filtrado["Tipo"] == "Despesa"]["Valor"].sum()
    saldo_mes = receitas_mes - despesas_mes

    c1, c2, c3 = st.columns(3)

    with c1:
        card("Receitas", f"R$ {receitas_mes:.2f}", "#22C55E")

    with c2:
        card("Despesas", f"R$ {despesas_mes:.2f}", "#EF4444")

    with c3:
        card("Saldo", f"R$ {saldo_mes:.2f}", "#3B82F6")

    st.divider()

    st.subheader("📌 Contas fixas")

    mes_atual = datetime.today().strftime("%Y-%m")

    for conta in CONTAS_FIXAS:
        lancado = df[
            (df["Categoria"] == conta["categoria"]) &
            (df["Mes"] == mes_atual)
        ]

        if lancado.empty:
            st.error(f"🔴 {conta['nome']}")
        else:
            st.success(f"🟢 {conta['nome']} — R$ {lancado['Valor'].sum():.2f}")

# ========================
# 📋 LANÇAMENTOS
# ========================
if menu == "📋 Lançamentos":
    st.title("📋 Lançamentos")

    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True,
        height=500
    )

# ========================
# 📈 ANÁLISES
# ========================
if menu == "📈 Análises":
    st.title("📈 Análises")

    despesas_df = df_filtrado[df_filtrado["Tipo"] == "Despesa"]

    if despesas_df.empty:
        st.info("Sem dados no período")
    else:
        resumo = despesas_df.groupby("Categoria", as_index=False)["Valor"].sum()

        fig = px.bar(
            resumo,
            x="Categoria",
            y="Valor",
            text="Valor",
            color="Valor"
        )

        fig.update_layout(
            plot_bgcolor="#0E1117",
            paper_bgcolor="#0E1117",
            font_color="#E6EDF3",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

# ========================
# ⚙️ CONFIG
# ========================
if menu == "⚙️ Configurações":
    st.title("⚙️ Configurações")

    st.warning("Área de gerenciamento")

    if st.button("⚠️ Apagar todos os dados"):
        senha = st.text_input("Confirme a senha", type="password")

        if senha == st.secrets["app_password"]:
            sheet.clear()
            sheet.append_row(["Data", "Tipo", "Categoria", "Valor", "Descrição"])
            st.success("Dados apagados")
            st.rerun()
