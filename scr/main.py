from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import datetime
import google.generativeai as genai
from statsbombpy.sb import events, matches, competitions
from dateutil.parser import parse
from transformers import pipeline

GEMINI_TOKEN = "retirada"
HUGGINGFACE_TOKEN = "retirada"
def configurar_modelo_linguagem():
    """Configura o modelo de linguagem (Gemini ou HuggingFace)"""
    try:
        genai.configure(api_key=GEMINI_TOKEN)
        modelo = genai.GenerativeModel("gemini-pro")
        return {"tipo": "gemini", "modelo": modelo}
    except Exception as gemini_error:
        try:
            modelo = pipeline(
                "text-generation",
                model="gpt2",
                max_length=500,
                num_return_sequences=1,
                temperature=0.8
            )
            return {"tipo": "huggingface", "modelo": modelo}
        except Exception as huggingface_error:
            return None

app = FastAPI(title="API de Análise de Futebol")

class DadosJogador(BaseModel):
    nome: str
    passes: int
    passes_completos: int
    precisao_passes: float
    finalizacoes: int
    gols: int
    desarmes: int
    interceptacoes: int
    dribles: int
    duelos_aereos: int
    faltas_cometidas: int
    faltas_sofridas: int

class ResumoPartida(BaseModel):
    gols_casa: int
    gols_fora: int
    time_casa: str
    time_fora: str
    eventos_importantes: List[Dict[str, str]]
    narracao: Optional[str] = None

class ComparacaoJogadores(BaseModel):
    jogador1: Dict[str, float]
    jogador2: Dict[str, float]

@app.get("/")
async def redirecionar_docs():
    """Redireciona para a documentação da API"""
    return RedirectResponse(url="/docs")

def obter_competicoes():
    """Obtém todas as competições disponíveis"""
    try:
        return competitions()
    except Exception as erro:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter competições: {str(erro)}"
        )

def obter_partidas(id_competicao: int, id_temporada: int):
    """Obtém partidas para uma competição e temporada específicas"""
    try:
        return matches(competition_id=id_competicao, season_id=id_temporada)
    except Exception as erro:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter partidas: {str(erro)}"
        )

def obter_eventos_partida(id_partida: int):
    """Obtém eventos de uma partida específica"""
    try:
        dados = events(match_id=id_partida)
        if "player" in dados.columns:
            dados["player"] = dados["player"].fillna("Desconhecido")
        return dados
    except Exception as erro:
        raise HTTPException(
            status_code=404, 
            detail=f"Partida não encontrada: {str(erro)}"
        )

def calcular_estatisticas_jogador(dados_partida: pd.DataFrame, 
                                nome_jogador: str) -> Dict:
    """Calcula estatísticas detalhadas do jogador"""
    dados_jogador = dados_partida[dados_partida["player"] == nome_jogador]
    
    passes_total = len(dados_jogador[dados_jogador["type"] == "Pass"])
    passes_completos = len(dados_jogador[
        (dados_jogador["type"] == "Pass") & 
        (dados_jogador["pass_outcome"].isna())
    ])
    
    estatisticas = {
        "passes": passes_total,
        "passes_completos": passes_completos,
        "precisao_passes": round((passes_completos / passes_total * 100), 1) if passes_total > 0 else 0,
        "finalizacoes": len(dados_jogador[dados_jogador["type"] == "Shot"]),
        "gols": len(dados_jogador[
            (dados_jogador["type"] == "Shot") & 
            (dados_jogador["shot_outcome"] == "Goal")
        ]),
        "desarmes": len(dados_jogador[dados_jogador["type"] == "Tackle"]),
        "interceptacoes": len(dados_jogador[dados_jogador["type"] == "Interception"]),
        "dribles": len(dados_jogador[dados_jogador["type"] == "Dribble"]),
        "duelos_aereos": len(dados_jogador[dados_jogador["type"] == "Aerial"]),
        "faltas_cometidas": len(dados_jogador[dados_jogador["type"] == "Foul Committed"]),
        "faltas_sofridas": len(dados_jogador[dados_jogador["type"] == "Foul Won"])
    }
    
    return estatisticas

def gerar_resumo_partida(dados_partida: pd.DataFrame) -> str:
    """Gera um resumo detalhado da partida"""
    if dados_partida is None:
        return "Dados da partida não disponíveis"
    
    eventos_importantes = []
    
    gols = dados_partida[
        (dados_partida["type"] == "Shot") & 
        (dados_partida["shot_outcome"] == "Goal")
    ]
    
    for _, gol in gols.iterrows():
        eventos_importantes.append({
            "minuto": gol["minute"],
            "tipo": "Gol",
            "jogador": gol["player"],
            "time": gol["team"]
        })
    
    cartoes = dados_partida[dados_partida["type"] == "Card"]
    for _, cartao in cartoes.iterrows():
        eventos_importantes.append({
            "minuto": cartao["minute"],
            "tipo": f"Cartão {cartao['card_type']}",
            "jogador": cartao["player"],
            "time": cartao["team"]
        })
    
    eventos_importantes.sort(key=lambda x: x["minuto"])
    
    if not eventos_importantes:
        return "Nenhum evento importante registrado na partida"
    
    resumo = "Eventos importantes da partida:\n\n"
    for evento in eventos_importantes:
        resumo += f"{evento['minuto']}' - {evento['tipo']}: {evento['jogador']} ({evento['time']})\n"
    
    return resumo

def gerar_narracao(dados_partida: pd.DataFrame, estilo: str) -> str:
    """Gera narração personalizada da partida usando modelo de linguagem"""
    config_modelo = configurar_modelo_linguagem()
    if config_modelo is None:
        return "Não foi possível gerar a narração. Configure um token válido."
    
    resumo = gerar_resumo_partida(dados_partida)
    
    estilos = {
        "Formal": "de forma técnica e objetiva, como um comentarista profissional",
        "Humorístico": "de forma bem-humorada e descontraída, com analogias engraçadas",
        "Técnico": "com foco em análise tática e técnica, detalhando as jogadas"
    }
    
    prompt = f"""
    Gere uma narração {estilos[estilo]} para esta partida de futebol:
    
    {resumo}
    
    Limite a narração a 3 parágrafos.
    """
    
    try:
        if config_modelo["tipo"] == "gemini":
            resposta = config_modelo["modelo"].generate_content(prompt)
            return resposta.text
    except Exception as e:
        return f"Erro ao gerar narração: {str(e)}"


@app.get("/competicoes")
async def listar_competicoes():
    """Lista todas as competições disponíveis"""
    return obter_competicoes().to_dict("records")

@app.get("/temporadas/{id_competicao}")
async def listar_temporadas(id_competicao: int):
    """Lista temporadas disponíveis para uma competição"""
    df_comp = obter_competicoes()
    temporadas = df_comp[df_comp["competition_id"] == id_competicao]["season_id"].unique()
    return sorted(temporadas.tolist())

@app.get("/times/{id_competicao}/{id_temporada}")
async def listar_times(id_competicao: int, id_temporada: int):
    """Lista times participantes de uma competição/temporada"""
    df_partidas = obter_partidas(id_competicao, id_temporada)
    times = sorted(set(df_partidas["home_team"].unique()) | 
                  set(df_partidas["away_team"].unique()))
    return times

@app.get("/partidas/{id_competicao}/{id_temporada}/{time_casa}/{time_fora}")
async def listar_partidas(
    id_competicao: int,
    id_temporada: int,
    time_casa: str,
    time_fora: str
):
    """Lista partidas disponíveis entre dois times"""
    df_partidas = obter_partidas(id_competicao, id_temporada)
    partidas_filtradas = df_partidas[
        (df_partidas["home_team"] == time_casa) &
        (df_partidas["away_team"] == time_fora)
    ]
    return partidas_filtradas.to_dict("records")

@app.get("/perfil_jogador/{id_partida}/{nome_jogador}", response_model=DadosJogador)
async def obter_perfil_jogador(id_partida: int, nome_jogador: str):
    """Retorna perfil detalhado de um jogador"""
    dados_partida = obter_eventos_partida(id_partida)
    estatisticas = calcular_estatisticas_jogador(dados_partida, nome_jogador)
    
    return DadosJogador(
        nome=nome_jogador,
        **estatisticas
    )

@app.get("/comparar_jogadores/{id_partida}/{jogador1}/{jogador2}", 
         response_model=ComparacaoJogadores)
async def comparar_jogadores(id_partida: int, jogador1: str, jogador2: str):
    """Compara estatísticas entre dois jogadores"""
    dados_partida = obter_eventos_partida(id_partida)
    estat1 = calcular_estatisticas_jogador(dados_partida, jogador1)
    estat2 = calcular_estatisticas_jogador(dados_partida, jogador2)
    
    return ComparacaoJogadores(
        jogador1=estat1,
        jogador2=estat2
    )

@app.get("/resumo_partida/{id_partida}", response_model=ResumoPartida)
async def obter_resumo_partida(id_partida: int, estilo: str = "Formal"):
    """Retorna resumo e narração da partida"""
    try:
        dados_partida = events(match_id=id_partida)
        
        if dados_partida is None or dados_partida.empty:
            raise HTTPException(
                status_code=404,
                detail="Partida não encontrada ou sem dados disponíveis"
            )
        
        if "player" in dados_partida.columns:
            dados_partida["player"] = dados_partida["player"].fillna("Desconhecido")
        
        times_unicos = dados_partida['team'].unique()
        if len(times_unicos) < 2:
            raise HTTPException(
                status_code=400,
                detail="Dados de partida incompletos: não foi possível identificar os times"
            )
        
        time_casa = times_unicos[0]
        time_fora = times_unicos[1]
        
        gols_casa = len(dados_partida[
            (dados_partida['team'] == time_casa) & 
            (dados_partida['type'] == 'Shot') & 
            (dados_partida['shot_outcome'] == 'Goal')
        ])
        
        gols_fora = len(dados_partida[
            (dados_partida['team'] == time_fora) & 
            (dados_partida['type'] == 'Shot') & 
            (dados_partida['shot_outcome'] == 'Goal')
        ])
        
        eventos_importantes = []
        
        gols = dados_partida[
            (dados_partida["type"] == "Shot") & 
            (dados_partida["shot_outcome"] == "Goal")
        ]
        
        for _, gol in gols.iterrows():
            eventos_importantes.append({
                "minuto": str(gol["minute"]),
                "tipo": "Gol",
                "jogador": gol["player"],
                "time": gol["team"]
            })
        
        cartoes = dados_partida[dados_partida["type"] == "Card"]
        for _, cartao in cartoes.iterrows():
            eventos_importantes.append({
                "minuto": str(cartao["minute"]),
                "tipo": f"Cartão {cartao['card_type']}",
                "jogador": cartao["player"],
                "time": cartao["team"]
            })
        
        eventos_importantes.sort(key=lambda x: int(x["minuto"]))
        
        narracao = gerar_narracao(dados_partida, estilo)
        
        return ResumoPartida(
            gols_casa=gols_casa,
            gols_fora=gols_fora,
            time_casa=time_casa,
            time_fora=time_fora,
            eventos_importantes=eventos_importantes,
            narracao=narracao
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar resumo da partida: {str(e)}"
        )
    

@app.get("/linha_tempo/{id_partida}")
async def obter_linha_tempo(
    id_partida: int,
    tipos_eventos: Optional[List[str]] = Query(None),
    minuto_inicial: Optional[int] = Query(0, ge=0, le=90),
    minuto_final: Optional[int] = Query(90, ge=0, le=90)
):
    """Retorna linha do tempo de eventos da partida"""
    dados_partida = obter_eventos_partida(id_partida)
    
    dados_filtrados = dados_partida[
        dados_partida["minute"].between(minuto_inicial, minuto_final)
    ]
    
    if tipos_eventos:
        dados_filtrados = dados_filtrados[
            dados_filtrados["type"].isin(tipos_eventos)
        ]
    
    eventos_timeline = []
    for _, evento in dados_filtrados.iterrows():
        detalhes = {}
        for campo in ["shot_outcome", "card_type", "pass_outcome"]:
            valor = evento.get(campo)
            if pd.isna(valor):
                detalhes[campo] = None
            elif isinstance(valor, float):
                detalhes[campo] = None if pd.isna(valor) else str(valor)
            else:
                detalhes[campo] = valor
                
        eventos_timeline.append({
            "minuto": str(evento["minute"]),
            "tipo": evento["type"],
            "jogador": evento["player"],
            "time": evento["team"],
            "detalhes": detalhes
        })
    
    return sorted(eventos_timeline, key=lambda x: int(x["minuto"]))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
