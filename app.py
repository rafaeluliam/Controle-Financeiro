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
# FORMATADOR BR
# ========================
def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ========================
# PARSER INPUT
# ========================
def parse_valor(valor_str):
    if not valor_str:
        return None
    valor_str = valor_str.strip()
    if "," in valor_str:
        valor_str = valor_str.replace(".", "").replace(",", ".")
    try:
        return float(valor_str)
    except:
        return None

# ========================
# CONVERSÃO
# ========================
def converter_valor(x):
    if pd.isna(x):
        return None
    x = str(x).strip()
    if "," in x:
        x = x.replace(".", "").replace(",", ".")
    try:
        return float(x)
    except:
        return None

# ========================
# CARD (CORRETO)
# ========================
def card(titulo, valor, status="neutro", percentual=None):

    if status == "verde":
        cor = "#22C55E"
        bg = "#0f1f17"
        texto_extra = f"{percentual:.1f}% da receita" if percentual else "Lançado"

    elif status == "vermelho":
        cor = "#EF4444"
        bg = "#1f1111"
        texto_extra = "Não lançado"

    else:
        cor = "#2A2F3A"
        bg = "#161B22"
        texto_extra = ""

    with st.container():  # 🔥 ESSA LINHA RESOLVE O BUG
        st.markdown(f"""
        <div style="
            background:{bg};
            border:1px solid {cor};
            border-radius:14px;
            padding:16px;
            margin-bottom:10px;
        ">
            <div style="font-size:15px; color:#9CA3AF;">
                {titulo}
            </div>

            <div style="font-size:26px; font-weight:700; color:white;">
                {valor}
            </div>

            <div style="font-size:13px; color:#9CA3AF;">
                {texto_extra}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ========================
# LOGIN
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
# GOOGLE SHEETS
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
# LOAD DATA
# ========================
@st.cache_data(ttl=60)
def load_data():
    dados = sheet.get_all_values()
    if len(dados) > 1:
        return pd.DataFrame(dados[1:], columns=dados[0])
    return pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Valor", "Descrição"])

df = load_data()

# ========================
# TRATAMENTO
# ========================
df["Data"] = pd.to_datetime(df["Data"], format="%Y-%m-%d", errors="coerce")
df["Tipo"] = df["Tipo"].astype(str).str.strip()
df["Categoria"] = df["Categoria"].astype(str).str.strip()
df["Valor"] = df["Valor"].apply(converter_valor)
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
    meses = sorted(df["Mes"].dropna().unique())
    mes = st.selectbox("📅 Mês", meses, index=len(meses)-1)
    df_filtrado = df[df["Mes"] == mes]
else:
    df_filtrado = df.copy()

# ========================
# SIDEBAR
# ========================
with st.sidebar:
    st.markdown("## 💰 Finanças")
    menu = st.radio(
        "Menu",
        ["➕ Adicionar", "📊 Dashboard", "📋 Lançamentos", "📈 Análises", "⚙️ Configurações"]
    )

# ========================
# ADICIONAR
# ========================
if menu == "➕ Adicionar":
    st.title("➕ Nova transação")

    tipo = st.selectbox("Tipo", ["Receita", "Despesa"])

    with st.form("form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            data = st.date_input("Data", datetime.today())

        with col2:
            categoria = st.selectbox("Categoria", CATEGORIAS[tipo])
            valor_input = st.text_input("Valor (ex: 20,77)")

        descricao = st.text_input("Descrição")
        submit = st.form_submit_button("Adicionar")

    valor = parse_valor(valor_input)

    if submit:
        if valor is not None and valor > 0:
            sheet.append_row([
                data.strftime("%Y-%m-%d"),
                tipo,
                categoria,
                f"{valor:.2f}".replace(".", ","),
                descricao
            ])
            st.success("Transação adicionada!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Valor inválido")

# ========================
# DASHBOARD
# ========================
if menu == "📊 Dashboard":
    st.title("📊 Dashboard")

    receitas = df[df["Tipo"] == "Receita"]["Valor"].sum()
    despesas = df[df["Tipo"] == "Despesa"]["Valor"].sum()
    saldo = receitas - despesas

    c1, c2, c3 = st.columns(3)

    with c1:
        card("Receitas", formatar_real(receitas))
    with c2:
        card("Despesas", formatar_real(despesas))
    with c3:
        card("Saldo", formatar_real(saldo))

    st.divider()
    st.subheader("Status das despesas do mês")

    despesas_mes_df = df_filtrado[df_filtrado["Tipo"] == "Despesa"]
    receitas_mes_df = df_filtrado[df_filtrado["Tipo"] == "Receita"]

    total_receita_mes = receitas_mes_df["Valor"].sum()

    cols = st.columns(3)

    for i, categoria in enumerate(CATEGORIAS["Despesa"]):
        df_cat = despesas_mes_df[despesas_mes_df["Categoria"] == categoria]

        if not df_cat.empty:
            valor = df_cat["Valor"].sum()
            percentual = (valor / total_receita_mes * 100) if total_receita_mes > 0 else 0
            status = "verde"
            texto = formatar_real(valor)
        else:
            status = "vermelho"
            percentual = None
            texto = "Não lançado"

        with cols[i % 3]:
            card(categoria, texto, status, percentual)

# ========================
# LANÇAMENTOS
# ========================
if menu == "📋 Lançamentos":
    df_exibicao = df_filtrado.copy()
    df_exibicao["Valor"] = df_exibicao["Valor"].apply(formatar_real)
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

# ========================
# ANÁLISES
# ========================
if menu == "📈 Análises":
    despesas_df = df_filtrado[df_filtrado["Tipo"] == "Despesa"]

    if not despesas_df.empty:
        resumo = despesas_df.groupby("Categoria", as_index=False)["Valor"].sum()
        fig = px.bar(resumo, x="Categoria", y="Valor", text="Valor")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados")

# ========================
# CONFIGURAÇÕES
# ========================
if menu == "⚙️ Configurações":

    if "confirmar_exclusao" not in st.session_state:
        st.session_state.confirmar_exclusao = False

    if st.button("⚠️ Apagar todos os dados"):
        st.session_state.confirmar_exclusao = True

    if st.session_state.confirmar_exclusao:
        senha = st.text_input("Confirme a senha", type="password")

        if st.button("Confirmar exclusão"):
            if senha == st.secrets["app_password"]:
                sheet.clear()
                sheet.append_row(["Data", "Tipo", "Categoria", "Valor", "Descrição"])
                st.success("Dados apagados com sucesso")
                st.session_state.confirmar_exclusao = False
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Senha incorreta")
