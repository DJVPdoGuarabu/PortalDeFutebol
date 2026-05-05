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

# Mantido caso você ainda esteja servindo as imagens por aqui
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
# ROTA PRINCIPAL DA API
# =========================================================================
@app.get("/api/jogos")
def listar_jogos():
    try:
        tabelas_prontas = []

        # -------------------------------------------------------
        # 1. PREMIER LEAGUE
        # -------------------------------------------------------
        try:
            df_premier = processar_campeonato('dimensao_Premier_completo.xlsx', 'fatos_Premier_completo.xlsx', 'Premier League')
            tabelas_prontas.append(df_premier)
        except Exception as e:
            print(f"Aviso: Não encontrei os dados da Premier League. ({e})")

        # -------------------------------------------------------
        # 2. CHAMPIONS LEAGUE
        # -------------------------------------------------------
        try:
            df_champions = processar_campeonato('dimensao_Champions_completo.xlsx', 'fato_Champions_completo.xlsx', 'Champions League')
            tabelas_prontas.append(df_champions)
        except Exception as e:
            print(f"Aviso: Não encontrei os dados da Champions League. ({e})")

        # -------------------------------------------------------
        # 3. BRASILEIRÃO (NOVO!)
        # -------------------------------------------------------
        try:
            # Certifique-se de que os arquivos abaixo existem na sua pasta
            df_brasileirao = processar_campeonato('dimensao_Brasileirao_completo.xlsx', 'fatos_Brasileirao_completo.xlsx', 'Brasileirão')
            tabelas_prontas.append(df_brasileirao)
        except Exception as e:
            print(f"Aviso: Não encontrei os dados do Brasileirão. ({e})")

        # Se não achou NENHUM arquivo, retorna erro
        if not tabelas_prontas:
            raise ValueError("Nenhuma planilha de campeonato foi encontrada na pasta!")

        # -------------------------------------------------------
        # JUNTA TUDO E LIMPA VALORES NULOS
        # -------------------------------------------------------
        df_completo = pd.concat(tabelas_prontas, ignore_index=True)

        df_completo = df_completo.astype(object)
        df_completo = df_completo.where(pd.notnull(df_completo), None)

        dados_json = df_completo.to_dict(orient='records')

        return {
            "status": "sucesso",
            "total_jogos": len(dados_json),
            "dados": dados_json
        }

    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)