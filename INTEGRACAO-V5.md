# Integração V5 — 01/11/2026

Foi implementado um pipeline executável de aquisição, câmera, projeção, marcadores ESP e planejamento de mira. A suíte local tem **73 testes aprovados**, incluindo leitura Win32 real e desenho GDI real em processos/janelas próprios. **O cheat completo ainda não foi validado nem está pronto para uso no Blood Strike.** A seleção automática de adversários permanece sem dados demonstrados de equipe, vida e visibilidade; nenhum evento real de mouse foi enviado.

## Código entregue

| Componente | Comportamento implementado | Limite relevante |
|---|---|---|
| `camera_capture.py` | Cadeia GetGameplay → Player → Camera, validada por RTTI de IGameplay/ClientPlayer/ICamera e IEntity; leituras de câmera iguais antes/depois do registro | Câmera candidata da propriedade Player.Camera; viewport final não observado |
| `scene.py` / `pipeline.py` | Captura → projeção → comandos de overlay → decisão de mira; rejeita origens de anchors diferentes; esconde marcadores antigos | Igualdade de anchors é condição local do modelo, não prova global de rebase ou geração |
| `win32_overlay.py` | Janela GDI em camada, transparente a cliques, sem tomar foco; superfície com repaint e limpeza de recursos | Testado em janelas próprias ocultas; apresentação visível junto ao jogo não testada |
| `python_owner.py` | Lê associação nativo/Python, dicionários combinados, MRO, owner marcado e instância AvatarModel | Resultado é candidato a modelo Avatar de owner jogador; não identifica adversário ou modelo principal |
| `aim.py` | Escolha do alvo classificado no raio, suavização dependente de tempo, limite de passo, deadzone e recusa de dados antigos | Exige classificação de adversário, estados explícitos e calibração de contagens/pixel |
| `win32_input.py` | Pacote x64 de movimento relativo e caminho SendInput, com checagens de idade, foco, dono da janela e tecla | Testes usaram API falsa para envio; zero eventos no sistema; sensibilidade/aceleração não calibradas no jogo |
| `live.py` / CLI | Loop de observação por PID/HWND explícitos, conferência de amostra, tamanho de viewport e posição da janela | Fonte implementada; não executada no processo protegido; não despacha mira |

## Como reproduzir os testes

Python 3.12+ x64, biblioteca padrão, na raiz do projeto:

```powershell
python tools/run_tests.py --output-dir reports/tests-v5
```

Relatórios: `reports/tests-v5/summary.json`, `junit.xml` e `console.txt` da execução registrada. Os hashes dos fontes vinculam o resultado ao código testado. A execução local Windows/Python 3.12.14 terminou com **73 testes, zero falhas, zero erros e zero skips**. Há nove testes nativos obrigatórios no Windows: quatro do leitor/processo filho, quatro de GDI/janelas ocultas e um de integração leitura → projeção → pixels → planejamento. Os testes CPython 3.14 usam blocos de bytes sintéticos; não executam um interpretador do alvo.

A CI permanece configurada para Windows/Linux e Python 3.12/3.13, sem execução remota afirmada. Estes são testes do projeto, sem suíte ou certificação fornecida pela NetEase. A execução de 26/10 com 40 testes permanece como histórico e não certifica os fontes novos.

Para um snapshot que contenha as cadeias de câmera e registro:

```powershell
python -m ExternalCore scene captura.json --output quadro.json --svg quadro.svg
```

O formato de entrada continua `bloodstrike-external-memory-v1`, com identidade declarada, procedência e segmentos de memória. O resultado indica candidatos, rejeições, frescor e decisão de mira. O SVG recebe a procedência da entrada; um fixture não é rotulado como captura do jogo. `snapshot`/`capture` antigos continuam disponíveis. `watch --help` descreve o loop nativo implementado; essa operação não foi executada contra o jogo nesta entrega.

## Classificação: o que avançou

Os scripts demonstram que `PlayerCombatAvatar` recebe `IsPlayerCombatAvatar=True` pelo decorador `with_tag`. `MHelper.CreateModel` cria um IEntity e atribui um ActorComponent a `entity.Skeleton`; `SimpleModel.Load` grava os atributos `.owner` e `.instance` no wrapper do IEntity. **Armas também podem receber um owner jogador.** Por isso o leitor exige adicionalmente uma instância na hierarquia AvatarModel, identificada por MRO, nome e módulo declarado; o namespace foi conferido no `IMPORT_NAME` do produtor, sem inferi-lo somente de `co_filename`.

Para cada Parent compatível, o leitor exige a associação N/H/A/W/P íntegra nas duas direções, MRO de PyIEntity, dicionário positivo suportado e o marcador booleano exato. Revalida a associação com nó/componente/ator e compara duas passagens de metadados. Uma confirmação produz `player`, com equipe/vida/visibilidade/jogador local desconhecidos. Ela nunca é convertida automaticamente em `opponent`; o seletor de mira rejeita esse candidato.

A relação estática universal `ActorComponent.Parent == modelo corporal principal` continua aberta. O leitor procura o vínculo nos dados de cada observação, recusando ausência/expiração/ambiguidade. Também não elimina todos os previews, modelos secundários ou duplicações de AvatarModel com o mesmo owner. São candidatos de modelo, não uma contagem garantida de jogadores ativos.

## Layouts e correções importantes

O layout CPython está vinculado a **3.14.0 GIL, Windows AMD64 LLP64**. Há confirmação nativa para o dicionário do wrapper em `P+0x10`, identidades dos tipos e singletons e campos usados. O leitor aceita apenas dicionários combinados e strings ASCII compactas; não adivinha split dicts, instâncias com managed dict ou atributos de builtins mantidos em tabelas do interpretador.

**Na 3.14, os itens da tupla começam em `+0x20`; `+0x18` é o hash em cache.** Isso foi conferido no header e no código nativo de acesso a item. Flags de PyTypeObject são lidas como unsigned long de 32 bits em `+0xa8`, conforme LLP64.

A errata em `StaticAnalysis/integration-evidence/gameplay-classifier-v5/ERRATA-STORE-ATTR.md` corrige leitores antigos que aplicavam `arg >> 1` a `STORE_ATTR`; esse opcode usa índice direto. Os nomes derivados desse opcode nos artifacts legados afetados não devem ser usados sem reinterpretação. Bytes, índices, RVAs e manifestos antigos foram preservados. O fluxo V5 de owner/modelo foi reinterpretado com o índice correto.

## Referências e invalidação

Nenhum endereço ou serial é tratado como geração de vida. As observações podem rejeitar muitas mudanças, mas não excluem A→B→A, reciclagem de endereço ou mudanças logo após o retorno. Não há fixação de objetos, GIL remoto ou chamada de APIs Python da engine. A comparação de metadados exclui contagens de referências e caches de hash de strings/tuplas, que não são gerações de identidade; tipos, entradas, ponteiros e demais campos relevantes continuam comparados. A idade começa no início da aquisição; aquisição/classificação demorada não transforma bytes antigos em novos. Marcadores antigos são escondidos, e o planejamento para.

O despacho de entrada usa foco, PID dono da janela e tecla no momento das consultas. Essas consultas e SendInput não constituem uma transação atômica do sistema. Contagens relativas dependem de sensibilidade/aceleração; o código exige calibração explícita e não promete equivalência entre contagem, pixel e ângulo. O loop de observação entregue não envia esses eventos.

Ainda exigem validação dinâmica em ambiente controlado: cadeia efetiva de câmera/viewport, atributos reais do owner e formas de dicionário, modelo principal versus cópias, transições de vida, equipe/estado/visibilidade e resposta da mira. Nenhum desses resultados foi inventado a partir dos testes próprios.

## Evidências novas

- `coordinate-bridge-v5/`: produtor de Transform.translation e limite da conversão de anchors.
- `gameplay-classifier-v5/`: tag, cadeia de owner, discriminador AvatarModel/WeaponModel, namespace e errata.
- `python-owner-v5/`: headers fixados, slots e dicionários, identidades e tupla 3.14, bytes e manifesto.
- `runtime-v5/delivery-verification.json`: identidade da amostra, bytes selecionados, hashes dos fontes testados e integridade dos 98 arquivos selados da V4.

O relatório da V4 e seus identificadores continuam preservados. Essa entrega acrescenta implementação e evidências; não reescreve uma hipótese antiga como fato de execução.
