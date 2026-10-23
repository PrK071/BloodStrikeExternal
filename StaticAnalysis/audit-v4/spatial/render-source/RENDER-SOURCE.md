# CameraProjection: produtores candidatos e origem do contexto

Mesma amostra em disco, SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. Base preferencial `0x140000000`; endereços abaixo são RVAs. Nenhum acesso a processo ou execução do alvo. Complemento novo, sem substituir os relatórios espaciais anteriores.

## Resultado

Foi recuperado o dispatcher concreto do registro CameraProjection e um caminho que entrega seu contexto: **`0x222ed0` → `0x7dac30` → `0x766370` → callback selecionado por índice**. Nesse caminho, o RDX recebido pelo callback é o **segundo argumento original de `0x222ed0`**. O callback de CameraProjection continua lendo `[[contexto+0xb8]+0xfa0]`.

Foram encontrados **quatro caminhos de atualização que copiam 64 bytes de um método virtual +0x70 para um bloco +0xfa0..+0xfd0**, e um inicializador que coloca identidade nessa faixa. A identidade entre os blocos desses produtores e `[contexto+0xb8]` ainda não foi demonstrada. Não se atribui +0xfa0 a ICamera nem se apresenta uma cadeia fechada até ICamera.

## Dispatcher e argumentos

A referência ao início do registro global `0x80f6dc8`, além do registrador `0x750070`, aparece em `0x766370`:

| RVA | Bytes | Instrução / efeito |
|---|---|---|
| `0x766374` | `4c 8b d2` | guarda RDX de entrada em R10 |
| `0x766377` | `0f b6 c1` | índice unsigned de um byte em CL |
| `0x76637a` | `4c 8d 0c 40` | R9=índice×3 |
| `0x76637e` | `48 8d 05 43 0a 99 07` | RAX=endereço do registro `0x80f6dc8` |
| `0x766385` | `49 8b d0` | RDX=R8 de entrada |
| `0x766388` | `49 8b ca` | RCX=RDX original |
| `0x76638b` | `42 ff 14 c8` | chama ponteiro `[registro+índice×0x18]` |

Os bytes efetivamente relidos estão em `candidate-functions.json`; a tabela acima resume a cadeia. O dispatcher não faz guarda de índice ou nulo nesse trecho.

O adaptador `0x7dac30` testa R9 e, se não nulo, move R8=RCX, RDX=R9, ECX=byte DL e faz tail jump em `0x7dac49` para `0x766370`. Se R9 é nulo, segue caminho de erro.

O único caller direto E8 validado encontrado desse adaptador está em `0x223579`, na função `0x222ed0`. O prólogo salva o segundo argumento em `[rsp_original+0x10]`. Após sete pushes e subtração de stack 0x90, em `0x223536` recupera esse valor de `[rsp_atual+0xd8]` para RBX. Em `0x223576`, RCX=RBX. Logo esse segundo argumento chega como **RDX do callback** depois dos rearranjos dos dois helpers.

No mesmo callsite, EDX vem de byte de uma tabela `[RCX]`; R9 é o endereço de saída `R15 + WORD[descritor+0x20]`; R8D contém `WORD[descritor+0x22]`. O adaptador descarta o R8 original ao preparar os argumentos do dispatcher. Existem ramos de cópia direta vizinhos (`0x223580` e `0x223598`), portanto não se deve afirmar que todo descritor passa por callback. `dispatcher-tailcaller.json`, `tailcaller-callers.json` e `tailcaller-caller-functions.json` preservam os bytes e fluxo.

A identificação do dono/tipo do segundo argumento de `0x222ed0`, todos os seus callers e a população de seu campo +0xb8 permanecem abertas. Esse é o limite explícito da proveniência de RDX nesta etapa.

## Produtores da faixa +0xfa0

A busca validada de instruções contendo a codificação disp32 `a0 0f 00 00` produziu 219 ocorrências. A triagem separou 142 ocorrências com RSP/RBP, 24 imediatos/outros, 48 candidatos de memória e cinco stores vetoriais priorizados. RBP pode ser base de objeto em algum código; a categoria de triagem não descarta definitivamente esses candidatos.

### Inicializador `0x789fe0`

Em `0x78a17a`–`0x78a1ab`, copia quatro vetores de `0x4f0f400`–`0x4f0f430` para argumento RCX +0xfa0..+0xfd0. Os 16 floats de origem são `1,0,0,0; 0,1,0,0; 0,0,1,0; 0,0,0,1`: identidade 4×4. A rotina também inicializa faixas vizinhas. Isso prova um escritor inicial, não a atualização da projeção de uma câmera ativa.

Foram encontrados callers diretos que passam áreas obtidas com tamanho solicitado 0x1300 ou 0x13c0 e guardam o resultado em campos diferentes. Exemplos: `0x2dfb0b` → campo pai +0x218; `0x372ae2` → pai +0xdd0; `0x3daf4f`, `0x8fd995` e `0xbc436f` → pai +0xdc0; `0x9c2003` → pai +8, e `0x9c202f`/`0x9c20e0` em blocos auxiliares. Isso reforça a distinção entre um bloco de dados e um campo direto de ICamera. Nenhum desses offsets de pai foi equiparado ao contexto +0xb8. Evidência: `initializer-callers.json`, `initializer-caller-functions.json`, `initializer-constants.json`.

### Atualização em `0xc47f9c`–`0xc47fbd`

Este trecho faz quatro stores contíguos de 16 bytes em destino RDI +0xfa0..+0xfd0, com dados obtidos da chamada virtual +0x70 do objeto R15 em `0xc47f8c`.

A entrada de rotina é `0xc46ca0`; o PE divide o prólogo e corpo em registros unwind adjacentes `0xc46ca0`, `0xc46cbf` e `0xc46cea`. O bloco `0xc46cea` não deve ser chamado de entrada fonte independente. No prólogo, R14 recebe o segundo argumento e RSI recebe o primeiro. Em `0xc46d8a` lê `[R14+8]`; em `0xc46daa` obtém R15 de +0x10 desse objeto. No ponto da escrita, recarrega RAX=`[R14+8]`, RCX=`[RAX+0x30]`, RDI=`[RCX+8]` e copia a saída do método virtual do R15 para RDI+0xfa0.

Cadeia local comprovada:

`R15 = [[arg2+8]+0x10]`

`destino = [[[arg2+8]+0x30]+8]`

`destino[0xfa0:0xfe0] = 64 bytes devolvidos por vcall R15, slot +0x70`

O tipo dinâmico de R15 e sua tabela efetiva nesse ponto não foram provados. O slot +0x70 coincide numericamente com um getter de matriz de PerspectiveCamera já recuperado, mas coincidência de slot não identifica tipo nem garante semântica. `producer-preceding-unwind.json` e `selected-producer-consumer-functions.json` guardam os trechos.

### Três atualizações semelhantes

`other-vector-writers.json` preserva outros três trechos que copiam os quatro vetores retornados por slot virtual +0x70 para destino +0xfa0..+0xfd0:

| Primeiro store | Último store | Objeto do vcall |
|---|---|---|
| `0x1e55b27` | `0x1e55b48` | R14 |
| `0x1e64df9` | `0x1e64e1a` | R14 |
| `0x1e6b416` | `0x1e6b437` | R15 |

São candidatos coerentes de atualização da mesma forma de bloco, mas o alias de objeto não foi fechado com o contexto do callback. Os registros unwind contendo esses stores são `0x1e547be`, `0x1e63bee`, `0x1e6a295`; não se presume que sejam os inícios lógicos das rotinas completas.

## Consumidor alternativo da mesma faixa

`0x1abd4a0` recebe contexto em R8, guarda em RSI (`0x1abd4ee`) e carrega RDI=`[RSI+0xb8]` (`0x1abd506`). Em `0x1abda17`–`0x1abda48`, copia RDI+0xfa0..+0xfd0 para saída RBX +0x590..+0x5c0 por stores `movntps`. Isso é um segundo consumidor local da **mesma forma de acesso contexto+0xb8 → bloco+0xfa0**, independente do callback pequeno `0x1abd000`. Ele reforça a interpretação de dados fornecidos à renderização, mas não resolve quem preenche o contexto ou qual passagem/câmera o usa.

## Critério de corte e lacunas

A pesquisa partiu de dois vínculos concretos: o registro global observado por `0x750070` e a faixa lida pelo callback. Foram priorizados stores vetoriais de 64 bytes, depois a proveniência de registros no dispatcher. Os demais acessos +0xfa0 estão catalogados com RVA, bytes e classificação em `fa0-candidates.json`/`candidate-triage.json`, sem promover coincidências numéricas a aliases.

A cobertura não inclui stores para a faixa por ponteiro já ajustado, cópias de bloco iniciadas antes de +0xfa0, instruções sem essa codificação disp32, código sem unwind, caminhos de outros módulos ou análise global de todos os aliases. As buscas de E8/E9 validam limites de instruções pelos registros unwind selecionados. Os JSON retêm esses registros e não afirmam CFG completo das rotinas com unwind dividido.

Para fechar a cadeia faltam: origem/tipo de arg2 de `0x222ed0`; escritores de seu +0xb8; vínculo desse valor ao destino dos quatro produtores; tipo do objeto do vcall +0x70; escolha de passagem/viewport; e eventual relação com o ICamera refletido. Sem esses elos, não se declara que CameraProjection seja a projeção final da tela nem que +0xfa0 seja um campo de ICamera.
