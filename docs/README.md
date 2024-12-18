# 🎯 API de Análise de Futebol

## 📝 Descrição
API RESTful desenvolvida com FastAPI para análise detalhada de partidas de futebol utilizando dados do StatsBomb. A API oferece endpoints para consulta de estatísticas de jogadores, comparações de desempenho, linha do tempo de partidas e geração de narrações personalizadas utilizando IA.

## 🚀 Tecnologias Utilizadas

- FastAPI
- Pandas
- Google Generative AI (Gemini)
- Hugging Face Transformers
- StatsBombPy
- Pydantic
- Python 3.9+

## ⚙️ Configuração do Ambiente

### Pré-requisitos
- Python 3.9 ou superior
- pip (gerenciador de pacotes Python)

### Instalação

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITORIO](https://github.com/felipemelobginfnet/AT_DDDA_FA.git)
cd api-analise-futebol
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
export HUGGINGFACE_TOKEN="seu_token_aqui"    # Linux/Mac
set HUGGINGFACE_TOKEN="seu_token_aqui"       # Windows

export GEMINI_TOKEN="seu_token_aqui"         # Linux/Mac
set GEMINI_TOKEN="seu_token_aqui"            # Windows
```

## 🚀 Executando a API

1. Inicie o servidor:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. Acesse a documentação Swagger UI: `http://localhost:8000/docs`

## 📌 Endpoints Disponíveis

### Competições e Times
- `GET /competicoes`: Lista todas as competições disponíveis
- `GET /temporadas/{id_competicao}`: Lista temporadas de uma competição
- `GET /times/{id_competicao}/{id_temporada}`: Lista times participantes

### Análise de Jogadores
- `GET /perfil_jogador/{id_partida}/{nome_jogador}`: Obtém estatísticas detalhadas de um jogador
- `GET /comparar_jogadores/{id_partida}/{jogador1}/{jogador2}`: Compara estatísticas entre dois jogadores

### Análise de Partidas
- `GET /partidas/{id_competicao}/{id_temporada}/{time_casa}/{time_fora}`: Lista partidas entre dois times
- `GET /resumo_partida/{id_partida}`: Obtém resumo e narração da partida
- `GET /linha_tempo/{id_partida}`: Retorna linha do tempo de eventos

## 📋 Exemplos de Uso

### Obtendo Perfil de Jogador
```bash
curl -X GET "http://localhost:8000/perfil_jogador/3788884/Neymar"
```

Resposta:
```json
{
  "nome": "Neymar",
  "passes": 45,
  "passes_completos": 38,
  "precisao_passes": 84.4,
  "finalizacoes": 5,
  "gols": 2,
  "desarmes": 1,
  "interceptacoes": 2,
  "dribles": 8,
  "duelos_aereos": 3,
  "faltas_cometidas": 2,
  "faltas_sofridas": 6
}
```

### Obtendo Resumo da Partida
```bash
curl -X GET "http://localhost:8000/resumo_partida/3788884?estilo=Tecnico"
```

Resposta:
```json
{
  "gols_casa": 3,
  "gols_fora": 1,
  "time_casa": "Paris Saint-Germain",
  "time_fora": "Manchester City",
  "eventos_importantes": [
    {
      "minuto": "15",
      "tipo": "Gol",
      "jogador": "Neymar",
      "time": "Paris Saint-Germain"
    }
  ],
  "narracao": "Análise técnica da partida..."
}
```

## 📊 Modelos de Dados

### DadosJogador
```python
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
```

### ResumoPartida
```python
class ResumoPartida(BaseModel):
    gols_casa: int
    gols_fora: int
    time_casa: str
    time_fora: str
    eventos_importantes: List[Dict[str, str]]
    narracao: Optional[str] = None
```
