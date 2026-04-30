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
# 🎨 CSS (CARDS)
# ========================
st.markdown("""
<style>

/* container do card */
.card-box {
    padding: 10px;
    border-radius: 14px;
    margin-bottom: 10px;
}

/* cores */
.card-verde {
    border: 1px solid #22C55E;
    background: linear-gradient(160deg, #0f1f17, #0a1410);
}

.card-vermelho {
    border: 1px solid #EF4444;
    background: linear-gradient(160deg, #1f1111, #140a0a);
}

.card-neutro {
    border: 1px solid #2A2F3A;
    background: linear-gradient(160deg, #161B22, #0F1117);
}

/* remove fundo padrão do metric */
div[data-testid="stMetric"] {
    background: transparent;
    border: none;
    box-shadow: none;
}

/* texto */
div[data-testid="stMetricLabel"] {
    font-size: 14px !important;
    color: #9CA3AF !important;
}

div[data-testid="stMetricValue"] {
    font-size: 26px !important;
    font-weight: 700;
}

div[data-testid="stMetricDelta"] {
    font-size: 13px !important;
}

</style>
""", unsafe_allow_html=True)

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
# CARD
# ========================
def card(titulo, valor, status="neutro", percentual=None):

    if status == "verde":
        classe = "card-verde"
        delta = f"{percentual:.1f}% da receita" if percentual else "Lançado"
        delta_color = "normal"

    elif status == "vermelho":
        classe = "card-vermelho"
        delta = "Não lançado"
        delta_color = "inverse"

    else:
        classe = "card-neutro"
        delta = None
        delta_color = "off"

    st.markdown(f'<div class="card-box {classe}">', unsafe_allow_html=True)

    st.metric(
        label=titulo,
        value=valor,
        delta=delta,
        delta_color=delta_color
    )

    st.markdown('</div>', unsafe_allow_html=True)

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
    menu = st.radio("Menu", ["➕ Adicionar", "📊 Dashboard", "📋 Lançamentos", "📈 Análises", "⚙️ Configurações"])

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
