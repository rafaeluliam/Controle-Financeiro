import streamlit as st
import pandas as pd
import calendar
from datetime import datetime

# ========================
# CONFIG
# ========================
st.set_page_config(page_title="Controle Financeiro", layout="wide")

# ========================
# 🔒 AUTENTICAÇÃO (ANTES DE TUDO)
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
# 🔐 CONEXÃO GOOGLE SHEETS
# ========================
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
# 📥 CARREGAR DADOS
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
    "Receita": ["Salário", "Freelance", "Outros"],
    "Despesa": ["Aluguel", "Energia", "Água", "Lazer", "Financiamento"]
}

CONTAS_FIXAS = [
    {"nome": "Aluguel", "categoria": "Aluguel"},
    {"nome": "Energia", "categoria": "Energia"},
    {"nome": "Água", "categoria": "Água"},
    {"nome": "Financiamento", "categoria": "Financiamento"},
]

# ========================
# UI
# ========================
st.title("💰 Controle Financeiro")

# ========================
# 📅 FILTRO
# ========================
if not df.empty:
    meses = df["Mes"].dropna().drop_duplicates().sort_values()
    mes_atual_str = datetime.today().strftime("%Y-%m")

    mes = st.selectbox(
        "Selecione o mês",
        meses,
        index=list(meses).index(mes_atual_str) if mes_atual_str in list(meses) else 0
    )

    df_filtrado = df[df["Mes"] == mes]
else:
    df_filtrado = df.copy()

# ========================
# 📌 CONTAS FIXAS
# ========================
st.subheader("📌 Contas do mês")

mes_atual = datetime.today().strftime("%Y-%m")
cols = st.columns(len(CONTAS_FIXAS))

for i, conta in enumerate(CONTAS_FIXAS):
    with cols[i]:
        lancado = df[
            (df["Categoria"] == conta["categoria"]) &
            (df["Mes"] == mes_atual)
        ]

        if lancado.empty:
            st.error(f"🔴 {conta['nome']}")
        else:
            valor_pago = lancado["Valor"].sum()
            st.success(f"🟢 {conta['nome']}\nR$ {valor_pago:.2f}")

# ========================
# ➕ ADICIONAR
# ========================
st.subheader("Adicionar transação")

tipo = st.selectbox("Tipo", ["Receita", "Despesa"])

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
    if valor > 0 and categoria:
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
        st.warning("Preencha corretamente")

# ========================
# 📊 RESUMO
# ========================
st.subheader("Resumo geral")

receitas = df[df["Tipo"] == "Receita"]["Valor"].sum()
despesas = df[df["Tipo"] == "Despesa"]["Valor"].sum()
saldo = receitas - despesas

c1, c2, c3 = st.columns(3)
c1.metric("Receitas", f"R$ {receitas:.2f}")
c2.metric("Despesas", f"R$ {despesas:.2f}")
c3.metric("Saldo", f"R$ {saldo:.2f}")

# ========================
# 📈 GRÁFICO
# ========================
st.subheader("Gastos por categoria")

despesas_df = df_filtrado[df_filtrado["Tipo"] == "Despesa"]

if despesas_df.empty:
    st.info("Nenhuma despesa no mês")
else:
    grafico = despesas_df.groupby("Categoria")["Valor"].sum()
    st.bar_chart(grafico)

# ========================
# 📋 TABELA
# ========================
st.dataframe(
    df_filtrado.style.format({"Valor": "R$ {:.2f}"}),
    use_container_width=True
)

# ========================
# 📊 RESUMO MÊS
# ========================
st.subheader("Resumo do mês")

receitas_mes = df_filtrado[df_filtrado["Tipo"] == "Receita"]["Valor"].sum()
despesas_mes = df_filtrado[df_filtrado["Tipo"] == "Despesa"]["Valor"].sum()
saldo_mes = receitas_mes - despesas_mes

c1, c2, c3 = st.columns(3)
c1.metric("Receitas (mês)", f"R$ {receitas_mes:.2f}")
c2.metric("Despesas (mês)", f"R$ {despesas_mes:.2f}")
c3.metric("Saldo (mês)", f"R$ {saldo_mes:.2f}")

# ========================
# 🔮 PREVISÃO
# ========================
st.subheader("Previsão do mês")

if not df_filtrado.empty:
    hoje = datetime.today()
    dias_mes = calendar.monthrange(hoje.year, hoje.month)[1]

    gasto_medio = despesas_mes / hoje.day if hoje.day > 0 else 0
    previsao = gasto_medio * dias_mes

    c1, c2 = st.columns(2)
    c1.metric("Média diária", f"R$ {gasto_medio:.2f}")
    c2.metric("Previsão", f"R$ {previsao:.2f}")

# ========================
# 🧹 GERENCIAMENTO (PROTEGIDO)
# ========================
st.subheader("Gerenciamento")

if "confirmar_exclusao" not in st.session_state:
    st.session_state.confirmar_exclusao = False

if st.button("⚠️ Apagar todos os dados"):
    st.session_state.confirmar_exclusao = True

if st.session_state.confirmar_exclusao:
    senha_admin = st.text_input("Confirme a senha para apagar", type="password")

    if senha_admin == st.secrets["app_password"]:
        sheet.clear()
        sheet.append_row(["Data", "Tipo", "Categoria", "Valor", "Descrição"])
        st.success("Dados apagados com sucesso")
        st.session_state.confirmar_exclusao = False
        st.rerun()
    elif senha_admin:
        st.error("Senha incorreta")
