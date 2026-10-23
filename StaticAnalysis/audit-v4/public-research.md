# Pesquisa pública: Blood Strike / Messiah / NewSpike

Data da consulta: 2026-10-21. Escopo: procedência e verificabilidade de fontes públicas relacionadas ao alvo da auditoria estática. A meta maior declarada é construir ESP/aimbot; por isso este relatório não reproduz offsets, estruturas de memória, procedimentos de leitura de atores, classificação de alvos, projeção/câmera ou métodos de mira/evasão.

## Fonte primária localizada

- [BloodStrike X — Globality case study](https://globality.live/case-bloodstrike)
  - A página se apresenta como estudo de caso do autor, descreve um projeto privado/concluído para o motor Messiah (internamente chamado “NewSpike”) e afirma engenharia reversa extensa.
  - A própria página diz que o código-fonte e o projeto ficam privados. Portanto, ela não fornece implementação pública que possa ser comparada diretamente com a amostra local.
  - O texto relata uso de injeção, modificação de runtime e neutralização de superfícies de anticheat. São alegações do autor, não confirmação independente. Não há repositório-fonte público identificado na página.
  - A página menciona medições “live”, mas não identifica hash, número de build, patch ou binário que permita atribuí-las ao Steam build 25981220 / patch 126.
  - Conclusão verificável: é uma fonte primária para o que o autor afirma ter construído; não é evidência verificável de layout/offsets para o alvo desta auditoria.

- [Globality changelog](https://globality.live/changelog)
  - Registra o anúncio do projeto BloodStrike X em 22 de agosto de 2026 e o caracteriza como lançado.
  - A entrada resume o projeto e remete ao estudo de caso. Continua sendo uma declaração do mesmo autor, sem código ou identificação do build-alvo.

- [Página inicial Globality](https://globality.live/)
  - Apresenta o projeto como trabalho autoral e privado, sem artefato-fonte público.

## Fontes técnicas de contexto (não específicas de Blood Strike)

- [Epic Games: AnimationCore API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/AnimationCore?lang=en-US)
  - Documenta o módulo AnimationCore de Unreal Engine e tipos de índices de ossos. É contexto de Unreal; não demonstra que Messiah/NewSpike use os mesmos tipos, IDs ou layouts.
- [Epic Games: FSkeletonPoseBoneIndex](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/AnimationCore/FSkeletonPoseBoneIndex)
  - Explicita que índice no skeleton pode diferir do índice correspondente no skeletal mesh. Isso alerta contra inferir mapeamentos a partir de nomes parecidos, mas não valida qualquer relação com Blood Strike.
- [dontnod/fork-ue4-python](https://github.com/dontnod/fork-ue4-python)
  - Código e documentação de integração Python em uma derivação de Unreal Engine 4. Serve apenas como exemplo de que wrappers Python podem ser proxies distintos dos objetos nativos; não estabelece que Messiah faça o mesmo.
- [Messiah Engine — Wikipedia](https://en.wikipedia.org/wiki/Messiah_Engine)
  - Fonte secundária e inadequada para inferir detalhes binários. Não usar para decisões de layout.

Não encontrei, nesta busca, um repositório público de código-fonte de Messiah/NewSpike ou implementação aberta de GetAllActors/ActorComponent associável ao jogo. A ausência nesta busca não prova que não exista.

## Relação com a amostra local

O contexto local identifica Steam build 25981220, patch 126, SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. A auditoria V3 fornecida relata análise estática dessa amostra e declara explicitamente que não provou exclusividade de tipos na raiz, classificação de jogadores/NPCs, nem semântica de gameplay do bit `IsInWorld`. A pesquisa web não fornece evidência que feche essas lacunas para esse hash/build. A página do Globality não declara correspondência com ele.

Por isso, nenhuma alegação pública sobre outras builds deve ser promovida a fato sobre esse executável. O material primário encontrado é relato sem código-fonte público, sem hash de amostra e sem número de build comparável.

## Alvos seguros para continuação da auditoria estática

- Continuar apenas no binário já identificado, preservando o hash e os limites de escopo definidos pela auditoria local.
- Para cada hipótese semântica, exigir ligação reproduzível entre metadados/reflexão, fluxo de dados e usos; nomes de símbolos isolados ou analogias com Unreal não bastam.
- Registrar separadamente o que os metadados permitem dizer sobre tipos/campos e o que os consumidores realmente fazem com eles, sem converter isso em orientação de aquisição ou seleção de alvos.
- Tratar transformações e dados de animação como hipótese até haver evidência estática inequívoca no mesmo build. As páginas públicas encontradas não oferecem essa evidência.

## Busca ampliada: fontes primárias, repositórios e MPK

Consultas exatas realizadas (além das variantes de palavras sem aspas mostradas abaixo):

- `"GetAllActors" "MCharacter"`
- `"ActorComponent" "Messiah"`
- `"PyObjectsModule"`
- `"Messiah" "mpkinfo"`
- `"BloodStrike" "external"`
- `"Blood Strike" "source" GitHub external`
- `"PyObjectsModule" Messiah game`
- `"GetAllActors" "MCharacter" Blood Strike`

### Resultados sobre tipos de ator e classificação

- As consultas exatas de `GetAllActors` + `MCharacter` e `PyObjectsModule` não retornaram repositório ou fonte pública indexada que ligue esses símbolos a Blood Strike/Messiah. Isso é resultado negativo desta busca, não prova de inexistência.
- [Globality case study](https://globality.live/case-bloodstrike) é a única página localizada com discussão específica de `GetAllActors` e `ActorComponent`. É o relato privado já descrito acima, sem código-fonte, sem amostra/hash/build, e não oferece evidência independente para classificar players/NPCs ou transferir semântica ao build local. Como esse texto é diretamente orientado a cheats, seus offsets e instruções operacionais não são reproduzidos aqui.
- [Ultimate Game Tool (GitHub)](https://github.com/esooLsIeicuJehT/ultimate_game_tool) é um repositório público com README e árvore de diretórios; declara suporte a Blood Strike e ferramentas de dump/SDK. O README identifica Blood Strike como “NetEase UE4.27+”, afirma ter assinaturas para nomes/objetos/funções e inclui comandos que operam sobre processo em execução. Isso não corrobora a nomenclatura Messiah/NewSpike do estudo anterior, nem identifica versão/hash da amostra ou prova que as assinaturas funcionem no build 25981220. A página do repositório lista uma pasta `bloodstrike`, mas a navegação da ferramenta de pesquisa bloqueou a abertura dessa subárvore; não li nem executei seus arquivos. Assim, não é fonte verificada para classificação estática de componentes.
- A busca de GitHub pelo termo `PyObjectsModule` não foi acessível pela interface de pesquisa consultada; não encontrei resultado de código indexado para esse símbolo.
- [GitHub topic `netease-mpk`](https://github.com/topics/netease-mpk) informa que não há repositórios públicos associados a esse tópico. É evidência apenas sobre esse tópico, não sobre toda a plataforma.

### Resultados sobre arquivos MPK/MPKINFO

- [XentaxWiki: NetEase MPK/MPKINFO](https://wiki.xentax.spektr.name/index.php/NetEase_MPK_MPKINFO) descreve formato little-endian sem assinatura. Para versão 2, mostra cabeçalho com versão/contagem e registros de 20 bytes, vários campos ainda desconhecidos; diz que versão 1 difere e associa o formato a jogos Messiah, listando Ace Racer e Vive Le Football. Não identifica Blood Strike, nem sample version/hash. A página liga dois scripts QuickBMS: o primeiro [netease_mpk.bms](https://aluigi.altervista.org/bms/netease_mpk.bms) falhou na abertura do navegador por tipo MIME binário; o segundo [mpk.bms](https://zenhax.com/download/file.php?id=9891) retornou 404. Portanto, os scripts não foram inspecionados nesta pesquisa.
- [Discussão Ace Racer no ResHax](https://reshax.com/topic/9208-netease-ace-racer-mpk-archive-unpack-help/) contém relato de 2021 sobre versão 1 do índice, com nomes, offsets, tamanhos e número do pacote, e deixa claro que o exemplo do autor veio do APK 1.1.5. O mesmo tópico registra divergência entre um `.mpkinfo` e `.mpk` fornecidos, indicando incompatibilidade de versão. É fórum, não especificação oficial; não é Blood Strike e não identifica o build-alvo.
- [Discussão Badlanders no ZenHAX](https://www.zenhax.com/viewtopic.php%40t%3D14765.html) relata que o MPK contém dados e MPKINFO contém nomes/caminhos, e que alguns arquivos `Resources` pareciam criptografados ao autor da resposta. São relatos de usuários sobre outro jogo; sem script acessível nesta página, sem versão/hash.
- [Discussão Where Winds Meet no ResHax](https://reshax.com/topic/18641-findings-summary-%E2%80%93-mpk-patch-vs-resource-analysis-where-winds-meet/) relata extração de vários tipos de recurso e recuperação parcial de nomes usando uma variante de MurmurHash3. Os anexos de script e mapeamento consultados retornaram 403. O post se refere a Where Winds Meet e não fornece uma versão/hash compatível com Blood Strike.
- Conclusão limitada: existem relatos e especificações parciais para MPK/MPKINFO de outros jogos NetEase/Messiah, úteis como pista para investigação de formatos, mas não uma implementação pública verificada para os arquivos de Blood Strike. Nada encontrado trata da classificação de componentes de atores. Não extrapolar o layout de recursos para o EXE nem para outro título/build.

### URLs efetivamente abertas ou tentadas

- https://globality.live/case-bloodstrike — aberta; conteúdo específico do jogo, mas declaração privada do autor.
- https://globality.live/changelog — resultado de busca consultado na rodada anterior; anúncio de 22 Aug 2026, sem artefatos de código.
- https://github.com/esooLsIeicuJehT/ultimate_game_tool — página do repositório e README abertas; subárvore `/tree/main/bloodstrike` bloqueada pela ferramenta. Repo público, mas sem versão/hash de jogo no README.
- https://wiki.xentax.spektr.name/index.php/NetEase_MPK_MPKINFO — especificação parcial aberta.
- https://aluigi.altervista.org/bms/netease_mpk.bms — tentativa falhou por resposta `application/octet-stream` não suportada pela ferramenta; código não inspecionado.
- https://zenhax.com/download/file.php?id=9891 — tentativa falhou com 404.
- https://reshax.com/topic/9208-netease-ace-racer-mpk-archive-unpack-help/ — discussão aberta; outro título e versão Android 1.1.5 citada.
- https://www.zenhax.com/viewtopic.php%40t%3D14765.html — discussão aberta; outro título.
- https://reshax.com/topic/18641-findings-summary-%E2%80%93-mpk-patch-vs-resource-analysis-where-winds-meet/ — discussão aberta; anexos `murmur3.py` e ZIP tentados, ambos retornaram 403.
- https://github.com/topics/netease-mpk — aberta; sem repositórios usando o tópico.

Não baixei nem executei binários. As buscas não identificaram fonte pública confiável que estabeleça classificação de `ActorComponent`, `Parent`, player/NPC ou semântica de `AnimationCore::Skeleton` para o build Steam 25981220 / patch 126. A pista MPK é sobre recursos e outros títulos; não responde à questão de classificação de atores.
