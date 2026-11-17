# Painel Macro – visão de casa

## Objetivo
Painel diário que reúne o cenário macro brasileiro para apoiar decisões de alocação numa gestora "macro casa": dados de alta frequência, expectativas, curva de juros e leitura da comunicação do Copom.

## Módulos
1. data/: coleta e cache local (parquet) de
   - SGS/BCB via python-bcb: IPCA, IBC-Br, Selic, câmbio, desemprego, resultado primário, conta corrente
   - Focus via python-bcb (Expectativas): IPCA, Selic, PIB e câmbio
   - Curva DI1 via PYield
2. analytics/:
   - Selic implícita na curva x mediana do Focus (prêmio de mercado)
   - Variação dos indicadores contra o mês anterior e contra o Focus
3. copom/: atas e comunicados do Copom, índice hawkish/dovish por reunião e estudo de evento (variação do DI1 de 1 e 2 anos no dia seguinte)
4. app/: painel em Streamlit com as seções acima
5. reports/: rascunho de nota matinal em markdown, sempre revisado por humano

## Regras
- Só dados públicos. Nunca usar material de ex-empregador.
- Toda função de cálculo tem teste em tests/ com um caso conferido à mão.
- Dados ficam em data/cache/, fora do git.
- Python 3.11+, pandas, funções pequenas e com docstring.
- Antes de mudanças grandes, propor o plano e esperar aprovação.
- Ao fim de cada sessão, atualizar a seção "Status" deste arquivo com o que foi feito e o que falta.

## Convenções
- Datas em ISO; taxas em % a.a.; dias úteis base 252.

## Status
- Etapa 0 (estrutura): concluída em 2026-11-12. Pastas data/, analytics/, copom/, app/, reports/, tests/ com __init__.py; .venv com python-bcb, pyield, pandas, pyarrow, plotly, streamlit, pytest instalados e importando; .gitignore, README e git inicializados; repositório painel-macro no GitHub.
- Nota de ambiente: o Avast intercepta HTTPS. O pip >= 24.2 usa a loja de certificados do Windows e funciona; se um pip antigo falhar com CERTIFICATE_VERIFY_FAILED, usar o bundle em .venv/ca-bundle.pem via PIP_CERT. Em tempo de execução, data/__init__.py chama truststore.inject_into_ssl() pelo mesmo motivo.
- Etapa 1 (data/): concluída em 2026-11-12. Módulos cache.py (parquet, ttl), sgs.py (8 séries com códigos validados; download em janelas de 9 anos com 3 tentativas; incremental), focus.py (anual IPCA/Selic/PIB Total/Câmbio e Selic por reunião, baseCalculo 0, incremental), di1.py (PYield → pandas, taxas em % a.a.; histórico disponível desde 2018-01-02), atualizar.py (`python -m data.atualizar`, ~11 s incremental). 21 testes sem rede em tests/. Formato longo padrão: data, serie/indicador, valor.
- Etapa 2 (analytics/): concluída em 2026-11-12. data/copom.py (calendário via PYield, rótulo R{n}/{ano} por ordem da decisão no ano, cache 24 h). analytics/curva.py (fator/taxa base 252, interpolação flat-forward, taxa a termo, Selic implícita por período entre datas de efetividade das reuniões, comparação com Focus = prêmio). analytics/indicadores.py (variação contra um mês antes: % para ibc_br e câmbio, p.p. nas demais; IPCA acumulado no ano; realizado x Focus para IPCA, Selic e câmbio). analytics/resumo.py imprime as três tabelas (`python -m analytics.resumo`). 37 testes. Sanidade: a linha "atual" da implícita fica ~0,10 p.p. abaixo da meta, que é o spread CDI-Selic esperado.
- Decisões de modelagem: reunião conta como futura enquanto data_efetividade > data de referência; a última reunião da lista só fecha o período anterior; a implícita não é ajustada pelo spread CDI-Selic (mostrado na linha "atual").
- Etapa 3 (copom/): concluída em 2026-11-12. copom/fontes.py baixa comunicados e atas pela API do site do BCB (copom/comunicados, comunicados_detalhes, atas, atas_detalhes; quando textoAta vem nulo, extrai do PDF com pypdf) e guarda em copom_textos.parquet (166 documentos, reuniões >= 200, de 2016). copom/tom.py: índice = (hawkish − dovish)/(hawkish + dovish) com léxico em português (listas HAWKISH/DOVISH, limites de palavra). copom/evento.py: taxas de 1 e 2 anos interpoladas (252/504 du) por pregão; janela do comunicado = fechamento do dia da decisão → pregão seguinte; da ata = pregão anterior → dia da publicação; variação em bp; delta_indice = mudança de tom contra o documento anterior do mesmo tipo; correlações. copom/resumo.py imprime tudo (`python -m copom.resumo`; primeira carga ~6 min). 55 testes.
- Achados: comunicados são estruturalmente mais hawkish que atas no léxico (nível não comparável entre tipos; usar variação). Correlação tom x DI1 1a: 0,24 (comunicado, n=71) e ~0 (ata). Estudo de evento só existe desde 2018 (início do histórico DI1 no PYield).
- Etapa 4 (app/): concluída em 2026-11-12. `streamlit run app/painel.py`. app/dados.py (st.cache_data de 1 h sobre os caches parquet e as tabelas de analytics/copom; atualizar_tudo limpa o cache), app/graficos.py (funções puras → go.Figure: implícita x Focus, curva DI1 do dia, histórico de série, tom do Copom em barras agrupadas, reação do DI1 em bp com cor por polaridade), app/painel.py (seções Indicadores, Curva, Copom, Nota matinal; botão Atualizar dados; tema claro/escuro via st.context.theme). Paleta: slots 1-3 da paleta de referência do guia dataviz (azul, laranja, verde-água) e par azul/vermelho para polaridade; validador em node não rodou (node ausente nesta máquina), valores são os documentados como validados. 63 testes: figuras (fumaça) e AppTest por seção (pulado se faltarem caches). Visual ainda não conferido em navegador.
- Identidade visual (2026-11-17): tema neutro, sem marca de terceiros; ícone próprio em app/assets/icone.svg e icone-branco.svg; paleta dos gráficos = slots 1-3 da paleta de referência do guia dataviz (claro #2a78d6/#eb6834/#1baf7a, escuro #3987e5/#d95926/#199e70), polaridade vermelho (alta) e azul (queda); tinta neutra; tema Streamlit com fundo branco e sidebar grafite #1a1a19.
- Etapa 5 (reports/): concluída em 2026-11-12. reports/nota.py monta o markdown (indicadores, realizado x Focus, curva implícita x Focus com prêmio médio, último comunicado com tom e reação do DI1), com aviso de revisão humana no topo e no rodapé; grava em reports/saida/nota_AAAA-MM-DD.md (ignorado pelo git). `python -m reports.nota` ou botão na seção "Nota matinal" do painel (mostra e permite baixar). 69 testes.
- Melhorias de cenário (2026-11-12, blocos A, B, C e F aprovados pelo usuário): analytics/mercado.py (vértices 1a/2a/5a por pregão, variações d1/d7/d30 em bp, inclinações 2a−1a e 5a−2a, curva em data passada, movimento precificado para a próxima reunião em bp e probabilidade de 25 bp); analytics/premio.py (prêmio implícita−Focus recalculado pregão a pregão, indexado pela ordem da reunião, últimos 120 pregões); analytics/expectativas.py (trajetória das medianas do Focus por ano de referência, variação em 7 dias, desancoragem contra meta 3,0 ± 1,5); copom/termos.py (termos que entraram/saíram/subiram/desceram entre os dois últimos comunicados). Painel: seção Curva com cartões de mercado, curva hoje x 30 dias, prêmio histórico e inclinação; seção nova Expectativas; seção Copom com "o que mudou no texto", histograma das reações e dispersão tom x reação. Nota ganhou bloco "Mercado (DI1)". Gráficos novos em app/graficos.py: linhas (≤3 séries com linhas de referência), curvas_sobrepostas, histograma_reacao, dispersao_tom_reacao. 88 testes.
- Pendentes aprovados para depois: bloco D (IPCA 12m x meta, núcleos, IPCA-15, juro real ex-ante com Focus 12 meses suavizado), bloco E (IBC-Br anual e 3m/3m, dívida bruta, nominal, IDP x conta corrente), bloco G (tarefa agendada 8h dia útil, selo "atualizado em", aviso por ntfy).
- 2026-11-13: caches atualizados (SGS até 2026-11-13, Focus de 2026-11-06, DI1 até 2026-11-12, 166 textos do Copom), 88 testes passando, nota do dia regenerada e tudo publicado no GitHub (joaoalonso-stack/painel-macro) a pedido do usuário. Commits locais a cada etapa; push quando o usuário pedir.
- 2026-11-17: tema neutro (ver Identidade visual); 88 testes passando; repositório público no GitHub como portfólio. Visual não conferido em navegador.
