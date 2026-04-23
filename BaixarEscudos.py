import pandas as pd
from curl_cffi import requests
import os
import time

# Cria uma pasta chamada 'escudos' se ela não existir
if not os.path.exists('escudos'):
    os.makedirs('escudos')

# Lê os IDs únicos dos times da sua planilha
print("Lendo a planilha...")
df = pd.read_excel('dimensao_campeonato_completo.xlsx')

# Pega todos os IDs da casa e de fora, junta tudo e tira os repetidos
ids_casa = df['ID_Casa'].dropna().unique().tolist()
ids_fora = df['ID_Fora'].dropna().unique().tolist()
todos_ids = list(set(ids_casa + ids_fora))

print(f"Total de escudos únicos para baixar: {len(todos_ids)}")

# Baixa cada escudo
for team_id in todos_ids:
    caminho_arquivo = f"escudos/{int(team_id)}.png"

    # Se o escudo já existe, pula para não baixar de novo
    if os.path.exists(caminho_arquivo):
        print(f"Escudo {team_id} já existe, pulando...")
        continue

    url = f"https://api.sofascore.app/api/v1/team/{int(team_id)}/image"

    try:
        print(f"Baixando escudo do time {team_id}...")
        # A arma secreta para passar pelo Cloudflare
        resposta = requests.get(url, impersonate="chrome", timeout=10)

        if resposta.status_code == 200:
            with open(caminho_arquivo, 'wb') as f:
                f.write(resposta.content)
            print(f"✅ Sucesso!")
        else:
            print(f"❌ Erro ao baixar (Status: {resposta.status_code})")

    except Exception as e:
        print(f"❌ Erro na conexão: {e}")

    # Dá uma pequena pausa para o Sofascore não achar que é um ataque DDoS
    time.sleep(1)

print("Processo concluído!")