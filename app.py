import streamlit as st
import pandas as pd
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

# ========================
# CONFIG
# ========================
st.set_page_config(page_title="Controle Financeiro", layout="wide")

# ========================
# 🎨 ESTILO VISUAL
# ========================
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        /* melhora cards métricos */
        div[data-testid="metric-container"] {
            background-color: #161B22;
            border-radius: 12px;
            padding: 15px;
        }

        /* remove poluição visual */
        th, td {
            font-size: 14px;
        }
    </style>
""", unsafe_allow_html=True)

# ========================
# 🔒 AUTENTICAÇÃO
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
        "📅 Selecione o mês",
        meses,
        index=list(meses).index(mes_atual_str) if mes_atual_str in list(meses) else 0
    )

    df_filtrado = df[df["Mes"] == mes]
else:
    df_filtrado = df.copy()

# ========================
# UI
# ========================
st.title("💰 Controle Financeiro")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Resumo",
    "📋 Lançamentos",
    "➕ Adicionar",
    "📈 Análises",
    "⚙️ Gerenciamento"
])

# ========================
# 📊 RESUMO
# ========================
with tab1:
    st.subheader("📊 Visão geral")

    receitas = df[df["Tipo"] == "Receita"]["Valor"].sum()
    despesas = df[df["Tipo"] == "Despesa"]["Valor"].sum()
    saldo = receitas - despesas

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Receitas", f"R$ {receitas:.2f}")
    c2.metric("💸 Despesas", f"R$ {despesas:.2f}")
    c3.metric("📊 Saldo", f"R$ {saldo:.2f}")

    st.divider()

    st.subheader("📅 Resumo do mês")

    receitas_mes = df_filtrado[df_filtrado["Tipo"] == "Receita"]["Valor"].sum()
    despesas_mes = df_filtrado[df_filtrado["Tipo"] == "Despesa"]["Valor"].sum()
    saldo_mes = receitas_mes - despesas_mes

    c1, c2, c3 = st.columns(3)
    c1.metric("Receitas (mês)", f"R$ {receitas_mes:.2f}")
    c2.metric("Despesas (mês)", f"R$ {despesas_mes:.2f}")
    c3.metric("Saldo (mês)", f"R$ {saldo_mes:.2f}")

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
            valor_pago = lancado["Valor"].sum()
            st.success(f"🟢 {conta['nome']} — R$ {valor_pago:.2f}")

# ========================
# 📋 LANÇAMENTOS
# ========================
with tab2:
    st.subheader("📋 Todos os lançamentos")

    st.caption("💡 Use o filtro de mês para análise")

    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True
    )

# ========================
# ➕ ADICIONAR
# ========================
with tab3:
    st.subheader("➕ Nova transação")

    tipo = st.selectbox("Tipo", ["Receita", "Despesa"], key="tipo_add")

    with st.form("form"):
        col1, col2 = st.columns(2)

        with col1:
            data = st.date_input("Data", datetime.today())

        with col2:
            categoria = st.selectbox("Categoria", CATEGORIAS[tipo])
            valor = st.number_input("Valor", min_value=0.0, format="%.2f")

        descricao = st.text_input("Descrição")

        submitted = st.form_submit_button("Adicionar")

    if submitted:
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
        else:
            st.warning("Valor inválido")

# ========================
# 📈 ANÁLISES
# ========================
with tab4:
    st.subheader("📈 Gastos por categoria")

    despesas_df = df_filtrado[df_filtrado["Tipo"] == "Despesa"]

    if despesas_df.empty:
        st.info("Nenhuma despesa no mês")
    else:
        resumo = despesas_df.groupby("Categoria", as_index=False)["Valor"].sum()

        fig = px.bar(
            resumo,
            x="Categoria",
            y="Valor",
            text="Valor"
        )

        st.plotly_chart(fig, use_container_width=True)

# ========================
# ⚙️ GERENCIAMENTO
# ========================
with tab5:
    st.subheader("⚙️ Gerenciamento")

    if "confirmar_exclusao" not in st.session_state:
        st.session_state.confirmar_exclusao = False

    if st.button("⚠️ Apagar todos os dados"):
        st.session_state.confirmar_exclusao = True

    if st.session_state.confirmar_exclusao:
        senha_admin = st.text_input("Confirme a senha", type="password")

        if senha_admin == st.secrets["app_password"]:
            sheet.clear()
            sheet.append_row(["Data", "Tipo", "Categoria", "Valor", "Descrição"])
            st.success("Dados apagados com sucesso")
            st.session_state.confirmar_exclusao = False
            st.rerun()
        elif senha_admin:
            st.error("Senha incorreta")
