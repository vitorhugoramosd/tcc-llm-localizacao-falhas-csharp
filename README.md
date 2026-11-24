# Avaliação do desempenho de LLMs na localização de falhas em bases de código C#

Material de apoio do Trabalho de Conclusão de Curso de **Vitor Hugo Ramos dos Santos**, Bacharelado em Engenharia de Software da Universidade da Região de Joinville (Univille), 2026, sob orientação do Prof. Christiano Piccinin.

O trabalho avalia como o desempenho de LLMs na localização de falhas varia entre bases de código C# com diferentes níveis de cobertura de testes. Os modelos recebem o relato do problema (a issue) e indicam onde está o defeito, e o desempenho é comparado entre código com testes automatizados (SWE-Sharp-Bench) e código com baixa cobertura de testes (nopCommerce, com poucos testes, e ShareX, sem nenhum). O desempenho é medido pelas métricas Top-N e Mean Reciprocal Rank (MRR), nos níveis de arquivo e de método.

Este repositório reúne **tudo o que foi usado na execução piloto** (o MVP do TCC-I): os scripts, os defeitos, as consultas enviadas aos modelos, as respostas recebidas, as métricas, o script da Figura 9 e os testes que conferem os números publicados no Capítulo 4.

## O que tem aqui

```
preparacao/      seleção dos defeitos, referência de acerto e montagem das consultas
  01_candidatos.py          lista os commits candidatos no histórico do Git
  02_filtrar.py             aplica os critérios de elegibilidade  -> elegiveis_pre.json
  03_sortear.py             sorteio com a semente 20261107        -> ordem_sorteio.json
  04_buscar_issues.py       busca o texto das issues no GitHub    -> issues_piloto.json
  conferencia_issues.md     quais issues sorteadas foram aceitas ou excluídas, e por quê
  05_montar_consultas.py    referência de acerto (tree-sitter) e consultas -> ../piloto/
  issue_8369.md             texto da issue usada no teste preliminar
piloto/          execução do piloto
  piloto.py                 envia as consultas às APIs, grava as respostas e calcula as métricas
  defeitos.json             os 7 defeitos, com issue, commits e referência de acerto
  consultas/                as consultas de arquivo e de memorização, exatamente como foram enviadas
  respostas/                as respostas de cada modelo (um arquivo por defeito)
  resultados.csv            posição do acerto, tokens e tempo por defeito e modelo
  registros/                saída das execuções do Gemini e do Nemotron
testes/          testes automáticos
  test_metricas.py          regras de pontuação (posição, caminho encurtado, Top-N, MRR, leitura do JSON)
  test_reproducao.py        confere as Tabelas 2 a 5 do Capítulo 4, o custo do piloto, o sorteio e a referência de acerto
graficos/
  figura9.py                gera a Figura 9 do Capítulo 4 a partir de piloto/resultados.csv (requer matplotlib)
```

Os 7 defeitos do piloto serviram para ajustar o protocolo e, por isso, não entram na amostra da execução completa (TCC-II). Na coluna `perfil` de `defeitos.json` e `resultados.csv`, os rótulos são anteriores à nomenclatura final do TCC: "com testes" corresponde ao nopCommerce, tratado no texto como caso de poucos testes, e "legado (sem testes)" corresponde ao ShareX. Os dois pertencem ao conjunto de baixa cobertura de testes.

## Como reproduzir

### 1. Conferir os resultados publicados (não precisa de chave de API)

Requer só o Python 3.10 ou mais recente.

```
python -m unittest discover testes
cd piloto
python piloto.py resultados
```

Os testes recalculam, a partir das respostas gravadas, os valores das Tabelas 2, 3 e 4 do Capítulo 4, conferem a Tabela 5 e o custo do piloto a partir do `resultados.csv` e verificam que o sorteio com a semente registrada gera a mesma ordem usada no piloto. O comando `resultados` imprime a tabela de métricas e regrava o `resultados.csv`. Para gerar a Figura 9, instale a matplotlib (`pip install matplotlib==3.11.2`) e rode `python graficos/figura9.py` na pasta raiz.

### 2. Refazer a seleção dos defeitos e as consultas, a partir dos repositórios públicos

```
git clone https://github.com/nopSolutions/nopCommerce.git clones/nop
git clone https://github.com/ShareX/ShareX.git clones/sharex
pip install -r requirements.txt
cd preparacao
python 01_candidatos.py ../clones
python 02_filtrar.py ../clones
python 03_sortear.py
python 05_montar_consultas.py ../clones
```

Os scripts usam o histórico até 07/11/2026, 15h UTC, momento em que o piloto foi preparado. Nesse ponto, o ramo `develop` estava nos commits `e9a85452b6956f2381cb5122ef7c42366db2230f` (nopCommerce) e `e61d85bb4b2b713c3d04478cc3b1610a19ba635b` (ShareX). Com esses limites, os arquivos gerados são **idênticos, byte a byte**, aos deste repositório: `elegiveis_pre.json`, `ordem_sorteio.json`, `defeitos.json` e as 14 consultas. O passo `04_buscar_issues.py` é opcional, porque o texto das issues pode ter sido editado depois do piloto; o texto usado está guardado em `issues_piloto.json`.

### 3. Repetir as consultas aos modelos

Requer uma chave de API de cada provedor. As chaves são lidas de variáveis de ambiente e **nunca** devem ser gravadas nos arquivos do repositório. No Windows, use `set` no lugar de `export`.

| Modelo | Provedor | Comando usado no piloto |
|---|---|---|
| Claude Sonnet 5.5 | Anthropic (API compatível com o formato OpenAI) | `PILOTO_URL=https://api.anthropic.com/v1/chat/completions PILOTO_CHAVE=... PILOTO_SEM_TEMPERATURA=1 python piloto.py api claude claude-sonnet-5-5` |
| Gemini 3.5 Flash | Google AI Studio, plano gratuito | `PILOTO_URL=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions PILOTO_CHAVE=... python piloto.py api gemini gemini-3.5-flash` |
| Nemotron 3 Ultra | OpenRouter, plano gratuito | `OPENROUTER_API_KEY=... python piloto.py api nemotron nvidia/nemotron-3-ultra-550b-a55b:free` |
| Cohere North Mini Code | OpenRouter, plano gratuito | `OPENROUTER_API_KEY=... PILOTO_MAX_TOKENS=32000 python piloto.py api cohere cohere/north-mini-code:free` |

Parâmetros: temperatura zero quando o modelo permite (o Claude Sonnet 5.5 recusa esse parâmetro), nenhuma ferramenta de busca na internet declarada e limite de 8.000 tokens na resposta. No Cohere, as consultas que voltaram vazias com esse limite foram refeitas com 32.000 tokens, como registra o Capítulo 4. Para rodar de novo, mova ou apague a pasta do modelo em `respostas/`, porque o script pula os defeitos que já têm resposta.

As respostas dos LLMs não são totalmente determinísticas, e os provedores atualizam os modelos com o tempo. Uma nova execução pode, portanto, gerar respostas um pouco diferentes; as respostas originais do piloto ficam guardadas em `respostas/`.

### Custo do piloto

A coluna `custo_usd` do `resultados.csv` guarda apenas o custo devolvido pelo provedor, o que só acontece no OpenRouter, onde os dois modelos foram usados no plano gratuito (custo zero). O custo do Claude, informado no Capítulo 4, foi estimado a partir dos tokens registrados e do preço oficial do Claude Sonnet 5.5 na API da Anthropic, de US$ 2 por milhão de tokens de entrada e US$ 10 por milhão de tokens de saída (https://platform.claude.com/docs/en/about-claude/pricing, consultado em 24/11/2026):

```
808.860 tokens de entrada x US$ 2 / 1.000.000  = US$ 1,62
  7.110 tokens de saída   x US$ 10 / 1.000.000 = US$ 0,07
total                                          = US$ 1,69, cerca de US$ 0,24 por defeito
```

O Gemini foi usado no plano gratuito do Google AI Studio.

## Formato das respostas

Cada arquivo `respostas/<modelo>/<defeito>.json` guarda as listas devolvidas pelo modelo (`arquivos`, `metodos` e `memorizacao`) e, para cada consulta, um registro com o texto bruto da resposta, o identificador do modelo devolvido pelo provedor, os tokens de entrada e de saída e o tempo em segundos (`reg_arquivo`, `reg_metodo` e `reg_memorizacao`). Quando a resposta veio fora do formato e a consulta foi repetida, os dois registros aparecem.

A pasta `respostas/_descartados/` guarda o que não entrou nos resultados: as respostas parciais do Gemma, que não pôde ser executado no plano gratuito por causa do limite de tokens por minuto, e uma resposta do Nemotron registrada antes da regra de caminho encurtado.

## Licença e créditos

O código está sob a licença MIT (arquivo `LICENSE`). Os dados produzidos neste trabalho (respostas, tabelas e métricas) podem ser reutilizados com citação do trabalho. Os textos das issues e os trechos de código dos projetos nopCommerce (https://github.com/nopSolutions/nopCommerce) e ShareX (https://github.com/ShareX/ShareX) pertencem aos seus autores e foram reproduzidos apenas para fins de pesquisa.

## Como citar

SANTOS, Vitor Hugo Ramos dos. **Avaliação do desempenho de LLMs na localização de falhas em bases de código C#**: material do piloto. GitHub, 2026. Disponível em: https://github.com/vitorhugoramosd/tcc-llm-localizacao-falhas-csharp.
