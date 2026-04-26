import streamlit as st
import pandas as pd
import os
import calendar
from datetime import datetime

# ========================
# Variáveis
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

FILE = "dados_financeiros.csv"

# ========================
# Criar arquivo se não existir
# ========================
if not os.path.exists(FILE):
    df = pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Valor", "Descrição"])
    df.to_csv(FILE, index=False)

# ========================
# Carregar dados
# ========================
df = pd.read_csv(FILE)

# 🔥 CORREÇÕES IMPORTANTES
df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
df["Tipo"] = df["Tipo"].astype(str).str.strip()
df["Categoria"] = df["Categoria"].astype(str).str.strip()
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

# Criar coluna de mês (evita bugs)
df["Mes"] = df["Data"].dt.to_period("M").astype(str)

# garantir variável
df_filtrado = df.copy()

# ========================
# Config página
# ========================
st.set_page_config(page_title="Controle Financeiro", layout="wide")

st.title("💰 Controle Financeiro")

# ========================
# 📅 Filtro por mês
# ========================

if not df.empty:
    meses = (
        df["Mes"]
        .dropna()
        .drop_duplicates()
        .sort_values()
    )

    mes_atual_str = datetime.today().strftime("%Y-%m")

    mes = st.selectbox(
        "Selecione o mês",
        meses,
        index=list(meses).index(mes_atual_str) if mes_atual_str in list(meses) else 0
    )

    df_filtrado = df[df["Mes"] == mes]

# ========================
# 📌 Contas do mês
# ========================
st.subheader("📌 Contas do mês")

hoje = datetime.today()
mes_atual = hoje.strftime("%Y-%m")

cols = st.columns(len(CONTAS_FIXAS))

for i, conta in enumerate(CONTAS_FIXAS):
    with cols[i]:
        nome = conta["nome"]
        categoria = conta["categoria"]

        lancado = df[
            (df["Categoria"] == categoria) &
            (df["Mes"] == mes_atual)
        ]

        if lancado.empty:
            st.error(f"🔴 {nome}")
        else:
            valor_pago = lancado["Valor"].sum()
            st.success(f"🟢 {nome}\nR$ {valor_pago:.2f}")

# ========================
# ➕ Adicionar transação
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
        nova_linha = pd.DataFrame(
            [[pd.to_datetime(data), tipo, categoria, valor, descricao]],
            columns=["Data", "Tipo", "Categoria", "Valor", "Descrição"]
        )

        df = pd.concat([df, nova_linha], ignore_index=True)

        # 👉 AQUI É O MAIS IMPORTANTE
        df["Mes"] = pd.to_datetime(df["Data"], errors="coerce").dt.to_period("M").astype(str)

        df.to_csv(FILE, index=False)

        st.success("Transação adicionada!")
        st.rerun()
    else:
        st.warning("Preencha os campos corretamente")

# ========================
# 📊 Resumo geral
# ========================
st.subheader("Resumo geral")

receitas = df[df["Tipo"] == "Receita"]["Valor"].sum()
despesas = df[df["Tipo"] == "Despesa"]["Valor"].sum()
saldo = receitas - despesas

col1, col2, col3 = st.columns(3)
col1.metric("Receitas", f"R$ {receitas:.2f}")
col2.metric("Despesas", f"R$ {despesas:.2f}")
col3.metric("Saldo", f"R$ {saldo:.2f}")

# ========================
# 📈 Gráfico por categoria
# ========================
st.subheader("Gastos por categoria")

despesas_df = df_filtrado[df_filtrado["Tipo"] == "Despesa"]

if despesas_df.empty:
    st.info("Nenhuma despesa encontrada para este mês")
else:
    grafico = despesas_df.groupby("Categoria")["Valor"].sum()
    st.bar_chart(grafico)

# ========================
# 📋 Tabela
# ========================
st.dataframe(
    df_filtrado.style.format({"Valor": "R$ {:.2f}"}),
    use_container_width=True
)

# ========================
# 📊 Resumo do mês
# ========================
st.subheader("Resumo do mês")

receitas_mes = df_filtrado[df_filtrado["Tipo"] == "Receita"]["Valor"].sum()
despesas_mes = df_filtrado[df_filtrado["Tipo"] == "Despesa"]["Valor"].sum()
saldo_mes = receitas_mes - despesas_mes

col1, col2, col3 = st.columns(3)
col1.metric("Receitas (mês)", f"R$ {receitas_mes:.2f}")
col2.metric("Despesas (mês)", f"R$ {despesas_mes:.2f}")
col3.metric("Saldo (mês)", f"R$ {saldo_mes:.2f}")


# ========================
# 🧹 Limpar dados
# ========================
st.subheader("Gerenciamento")

if st.button("⚠️ Apagar todos os dados"):
    df = pd.DataFrame(columns=df.columns)
    df.to_csv(FILE, index=False)
    st.warning("Todos os dados foram apagados!")