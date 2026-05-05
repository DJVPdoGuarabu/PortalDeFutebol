import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/escudos", StaticFiles(directory="escudos"), name="escudos")


# =========================================================================
# FUNÇÃO AUXILIAR: A MÁQUINA DE FAXINA
# =========================================================================
def processar_campeonato(caminho_dimensao, caminho_fato, nome_campeonato):
    df_dimensao = pd.read_excel(caminho_dimensao)
    df_fato = pd.read_excel(caminho_fato)

    df_dimensao['Campeonato'] = nome_campeonato
    df_fato.columns = df_fato.columns.str.strip()

    if 'Mando' in df_fato.columns and 'Period' in df_fato.columns:
        df_fato['Period'] = df_fato['Period'].astype(str).str.strip().str.upper()
        df_fato = df_fato[df_fato['Period'].isin(['ALL', 'MATCH', 'TOTAL'])]

        if df_fato.empty:
            df_fato = pd.read_excel(caminho_fato)
            df_fato.columns = df_fato.columns.str.strip()

        df_fato['Mando'] = df_fato['Mando'].astype(str).str.strip().str.lower()
        df_fato['Mando'] = df_fato['Mando'].replace({
            'home': 'Casa', 'away': 'Fora',
            '1': 'Casa', '2': 'Fora',
            'casa': 'Casa', 'fora': 'Fora'
        })

        if 'Period' in df_fato.columns:
            df_fato = df_fato.drop(columns=['Period'])

        df_fato_pivot = df_fato.pivot_table(index='Match_ID', columns='Mando', aggfunc='first')
        df_fato_pivot.columns = [f"{col[0]}_{col[1]}" for col in df_fato_pivot.columns]
        df_fato_pivot = df_fato_pivot.reset_index()
    else:
        df_fato_pivot = df_fato

    df_cruzado = pd.merge(df_dimensao, df_fato_pivot, on='Match_ID', how='left')
    return df_cruzado


# =========================================================================
# CARREGAMENTO GLOBAL: RODA APENAS UMA VEZ AO LIGAR O SERVIDOR!
# =========================================================================
print("Iniciando servidor... Lendo as planilhas do Excel para a memória RAM...")

tabelas_prontas = []

try:
    tabelas_prontas.append(
        processar_campeonato('dimensao_Premier_completo.xlsx', 'fatos_Premier_completo.xlsx', 'Premier League'))
except Exception as e:
    print(f"Aviso: Não encontrei os dados da Premier. ({e})")

try:
    tabelas_prontas.append(
        processar_campeonato('dimensao_Champions_completo.xlsx', 'fato_Champions_completo.xlsx', 'Champions League'))
except Exception as e:
    print(f"Aviso: Não encontrei os dados da Champions. ({e})")

try:
    tabelas_prontas.append(
        processar_campeonato('dimensao_Brasileirao_completo.xlsx', 'fatos_Brasileirao_completo.xlsx', 'Brasileirão'))
except Exception as e:
    print(f"Aviso: Não encontrei os dados do Brasileirão. ({e})")

# Consolida a base em uma variável global
if tabelas_prontas:
    df_completo = pd.concat(tabelas_prontas, ignore_index=True)
    df_completo = df_completo.astype(object)
    df_completo = df_completo.where(pd.notnull(df_completo), None)
    DADOS_GLOBAIS = df_completo.to_dict(orient='records')
    print("Sucesso! Planilhas carregadas na memória.")
else:
    DADOS_GLOBAIS = []
    print("Aviso Crítico: Nenhuma planilha foi carregada.")


# =========================================================================
# ROTAS DA API (AGORA SÃO INSTANTÂNEAS)
# =========================================================================

# Rota 1: Entrega a base inteira para o dashboard inicial
@app.get("/api/jogos")
def listar_jogos():
    return {
        "status": "sucesso",
        "total_jogos": len(DADOS_GLOBAIS),
        "dados": DADOS_GLOBAIS
    }


# Rota 2: Entrega APENAS um jogo para a tela de estatísticas
@app.get("/api/jogos/{match_id}")
def obter_jogo_especifico(match_id: str):
    # Procura na RAM apenas o jogo solicitado
    for jogo in DADOS_GLOBAIS:
        if str(jogo.get("Match_ID")) == str(match_id):
            # Retorno em formato de lista para não quebrar seu front-end atual
            return {"status": "sucesso", "dados": [jogo]}

    return {"status": "erro", "mensagem": "Jogo não encontrado"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)