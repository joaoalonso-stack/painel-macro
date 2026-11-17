# Painel Macro

Painel diário do cenário macro brasileiro para apoiar decisões de alocação numa gestora "macro casa". Projeto de portfólio independente, feito só com dados públicos.

## Objetivo
Reunir num só lugar dados de alta frequência (SGS/BCB), expectativas do Focus, a curva DI1 e a leitura da comunicação do Copom, com um rascunho de nota matinal revisado por humano.

## Como usar (por enquanto)

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python -m data.atualizar      # baixa/atualiza os caches em data/cache/
python -m analytics.resumo    # variações, realizado x Focus e Selic implícita x Focus
python -m copom.resumo        # tom dos comunicados/atas e reação do DI1 (baixa os textos na 1ª vez)
streamlit run app/painel.py   # painel: Indicadores, Curva, Expectativas, Copom, Nota matinal
python -m reports.nota        # grava o rascunho da nota em reports/saida/nota_AAAA-MM-DD.md
pytest                        # testes sem rede (o AppTest do painel usa os caches locais)
```

O índice de tom do Copom conta termos hawkish e dovish de um léxico em português e calcula (hawkish − dovish) / (hawkish + dovish). O estudo de evento mede a variação do DI1 de 1 e 2 anos entre o fechamento anterior e o posterior a cada comunicado e ata.

A Selic implícita vem da curva DI1 interpolada flat-forward: para cada reunião do Copom, a taxa a termo entre a data em que a decisão passa a valer e a data da reunião seguinte. A diferença para a mediana do Focus por reunião é o prêmio de mercado.

Os caches ficam em `data/cache/*.parquet` e não vão para o git.

| Cache         | Fonte                         | Conteúdo                                              |
|---------------|-------------------------------|-------------------------------------------------------|
| `sgs`         | SGS/BCB via python-bcb        | IPCA, IBC-Br, Selic (meta e efetiva), PTAX, desemprego, primário e conta corrente (% PIB, 12 m) |
| `focus_anual` | Focus (Olinda) via python-bcb | Mediana anual de IPCA, Selic, PIB e câmbio            |
| `focus_selic` | Focus (Olinda) via python-bcb | Selic esperada por reunião do Copom                   |
| `di1`         | B3 via PYield                 | Curva DI1 (ajuste e fechamento) por pregão, desde 2018 |

Convenções: datas em ISO, taxas em % a.a., dias úteis base 252.

## Status
Etapas 1 a 5 concluídas (coleta, analytics, Copom, painel Streamlit e nota matinal), mais os blocos de cenário: movimento de mercado (vértices DI1, inclinação, curva hoje x 30 dias), prêmio histórico curva x Focus, trajetória e desancoragem das expectativas do Focus e Copom analítico (o que mudou no texto, distribuição das reações). Próximos: inflação e juro real (bloco D), atividade/fiscal/externo (bloco E) e atualização agendada (bloco G).
