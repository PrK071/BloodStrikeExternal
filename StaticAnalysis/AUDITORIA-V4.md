# Auditoria V4 — identidade, categorias e invalidação

Data: 21/10/2026. Método: leitura do executável como arquivo PE, extração de CFG e metadados, conferência por iced-x86 e Capstone. Nenhum acesso ao processo do jogo. Esta entrega conclui um marco estático; o objetivo de ESP/aimbot externo funcional permanece em desenvolvimento, sem validação em execução.

**SHA-256 preservado:** `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. Steam build 25981220, patch 126, conforme identificação anterior. Todos os endereços abaixo são **RVAs**, exceto onde explicitamente indicado; base preferencial `0x140000000`. Endereços em disco não são endereços observados de um processo.

## As três perguntas

| Pergunta | Resposta sustentada | Confiança e limite |
|---|---|---|
| O que a chave identifica? | Nos dois caminhos de inserção conhecidos, os quatro bytes são o serial em `Character::Actor+0x0c`, atribuído pela construção de sua base `AnimationCore::Skeleton`. Dois construtores usam o mesmo contador atômico de 32 bits. | Alta para origem e escopo desses caminhos. Unicidade global durante toda a execução não está demonstrada: faltam exclusão de resets/acessos calculados, tratamento do wrap e prova de associação exclusiva. |
| Quais categorias entram no registro? | Os payloads comprovados são componentes da família nativa `ActorComponent`; a chave pertence ao ator associado. Isso não classifica jogador, NPC, aliado, inimigo ou objeto decorativo. | Alta para os produtores examinados; classificação independente de gameplay **aberta**. Não foi provado que todo objeto dessa família entre no registro. |
| Quando uma referência deixa de ser válida? | Existem fronteiras diferentes: remoção do nó, troca/liberação do ator, expiração do wrapper e destruição do componente. Um caminho de limpeza expira o wrapper **antes** de chamar o destrutor nativo que pode remover o nó. | Alta para a ordem local desse caminho; ordem global, exclusão mútua, reentrância e thread concreta **abertas**. |

Não seria sustentado declarar as três perguntas completamente encerradas. A origem da chave foi resolvida nos construtores conhecidos; as duas outras receberam limites mais precisos e novos caminhos concretos.

## 1. Integridade e reprodução da V3

`audit-v4/v3-reproduction.json` registra:

- **18/18** arquivos correspondentes ao manifesto original da V3.
- Hash do manifesto V3: `0e052f7c53346d61def4167eba4e8fc1915e04dd0b5b515c19b312b84b123e80`.
- Hash da amostra correspondente ao valor fixado acima.
- **8.018 instruções únicas**, equivalentes a **8.096 registros com repetições entre CFGs**, conferidas em bytes, comprimento e alvos aplicáveis com dois decodificadores.
- Oito snapshots de dados da V3 reproduzidos; entradas V2 e anteriores do baseline preservadas.

Essas verificações reproduzem o conteúdo dos artefatos, não validam automaticamente todas as interpretações semânticas da V3. Nenhum identificador V2/V3 foi renomeado ou reutilizado. Novas instruções recebem `V4-I-<RVA hexadecimal>`, blocos recebem `V4-Dnn` e alegações selecionadas recebem `V4-Knn`.

## 2. Origem da chave e tratamento de duplicatas

### 2.1 Geração dos quatro bytes

**V4-K01**, evidência `V4-D01` e instruções `V4-I-115EB42`, `V4-I-115EB4A`, `V4-I-115E502`, `V4-I-115E50A`:

```asm
; Construtor 0x115eb00, trechos contíguos selecionados
0x115eb3d  mov eax,1
0x115eb42  lock xadd [0x1479602f0],eax
0x115eb4a  mov [rcx+0x0c],eax

; Outro construtor 0x115e4c0
0x115e4fd  mov eax,1
0x115e502  lock xadd [0x1479602f0],eax
0x115e50a  mov [rcx+0x0c],eax
```

O operando de memória é DWORD. `XADD` devolve em EAX o valor anterior e soma um no armazenamento. O arquivo contém `01 00 00 00` no RVA `0x79602f0`; isso é o valor inicial **em disco**, sem prova de que inicializadores nunca o alterem. O DWORD vizinho não faz parte de um contador de 64 bits.

**V4-K02:** os construtores de `Character::Actor` em `0x16d0e70` e `0x16d1190` chamam respectivamente esses construtores de `Skeleton` em `0x16d0e9a` e `0x16d11b2`. Ambos os caminhos recebem serial novo desse mecanismo; o segundo não foi chamado de construtor de cópia por mera semelhança.

O construtor genérico de `Skeleton` também tem callers fora da criação de `Character::Actor`, inclusive o caminho de `SkeletonComponent` em `0xad6760`. Portanto o domínio do contador é mais amplo que a população de atores desta raiz. Isso não significa que esses outros objetos sejam payloads do registro de `GetAllActors`.

A varredura de descoberta cobriu 309.153 registros de unwind, com 18.587.982 registros decodificados e 11.007 inválidos. Encontrou essas duas referências diretas ao DWORD do contador. Referências a matrizes/constantes vizinhas não foram tratadas como resets. A busca não exclui escritas por ponteiro calculado, leafs fora dos registros de unwind, inicialização dinâmica ou código não alcançado.

### 2.2 Invariável de não colisão: o que foi e não foi provado

Os caminhos de inserção já examinados na V3 leem `A+0x0c` e associam o componente C. Na troca feita em `0x19c0100`, o caminho com ator antigo remove sua chave antes de associar e inserir a nova. A fábrica `0x19bfe20` aloca `0x810` bytes, chama o construtor de ator em `0x19bfe53` e a associação em `0x19bfe75`. Há assim um produtor concreto de novo serial seguido de associação.

**V4-K03:** o helper `0x254390` conserva o payload existente quando a chave já está presente. As instruções em `0x254422`, `0x254435` e `0x254438` sustentam o ramo de duplicata e o retorno sem substituição. Os dois callsites de inserção conhecidos não usam o resultado para reparar a colisão.

A explicação compatível com o código é: seriais novos evitam colisão com outros atores no intervalo sem reset e sem wrap; remoção anterior cobre a troca local do ator do componente. Essa explicação é **condicional**, não uma invariável universal demonstrada.

Permanecem abertas:

- O contador de 32 bits sofre wrap módulo `2^32`. Não foram encontrados bits de geração separados nesses quatro bytes; zero pode aparecer após wrap. Não há medição da frequência real de construção.
- Não foi excluída uma segunda associação simultânea do mesmo ator com componentes diferentes. Compartilhar A implica compartilhar sua chave; exclusividade precisa de prova independente.
- A remoção antiga é por chave. Não foi demonstrado um teste universal `payload atual == componente que remove` que impeça um componente antigo de apagar uma associação diferente em um cenário de colisão.
- Não foi reconstruído um mecanismo de tratamento especial de wrap/reset. A ausência nesta cobertura não prova inexistência.

**Conclusão:** não há bug de duplicata provado. Há origem de serial demonstrada e obrigações precisas para provar que a política de duplicatas é suficiente. A chave não é demonstradamente um ID de rede, jogador ou classe de gameplay.

## 3. Produtores, Parent e classificação

O produtor `0x19bfe20` liga a construção de `Character::Actor` ao componente recebido como argumento. O wrapper `0x29bb2f0`, identificado pelo nome de método `LoadSkeletonAndGraph`, verifica seu nativo e chama esse produtor. Isso comprova uma rota pública da camada de binding para a criação/associação, não a categoria de gameplay da instância.

`IComponent.Parent`, já sustentado por `V3-D02`, é declarado `IObject` e lido do componente em `+0x40`. Não foi encontrada nesta entrega uma cadeia independente que una a construção desse Parent, um controlador específico e uma categoria de jogador/NPC. Nem `Character::Actor`, nem skeleton, nem `IsInWorld` substituem essa ligação.

O construtor genérico de skeleton e a raiz distinta `0x8143e90` continuam separados da raiz `0x8b7cd90`. O uso do mesmo helper de mapa e do mesmo contador não unifica os containers. Nenhum novo payload de categoria C++ distinta foi demonstrado na raiz de `GetAllActors`.

**Estado:** família C++ conhecida, taxonomia de gameplay aberta. Até que produtores/consumidores com significado independente sejam ligados ao componente e ao Parent, não há filtro de alvos sustentado para ESP/aimbot.

## 4. Referências: remoção, expiração e destruição

### 4.1 Não existe uma única fronteira de validade

| Referência | Fronteira demonstrada | O que não decorre dela |
|---|---|---|
| Nó do registro | `erase` libera o nó de 32 bytes | Não prova destruição do payload nem do ator. |
| `C+0x378` → ator A | Associação substitui/libera a referência anterior; destrutor libera sua referência | Não prova exclusividade de A nem que nenhum outro holder o retenha. |
| Wrapper W → componente nativo | Limpeza da cadeia de wrappers zera `W+0x18` | Python P pode continuar existente; endereço de W não prova nativo válido. |
| Controle H → nativo N | Invalidação zera `H+8` e `N+0x18` | Não substitui sincronização nem valida um ponteiro lido antes. |
| Parent / `IsInWorld` | Propriedade e bit testados no caminho conhecido | Não prova que Parent seja alvo de gameplay nem que a instância ainda seja a mesma. |

### 4.2 Novo caminho com expiração anterior ao destrutor

**V4-K04:** a função de limpeza em `0x4fa950` foi seguida através de **cinco regiões de unwind**. No trecho relevante:

1. Salva o próximo item em `0x4faa14` e limpa ligações do item em `0x4faa1d`/`0x4faa21`.
2. Chama a invalidação `0x10ea20` em **`0x4faa28`**.
3. Carrega a vtable e chama seu primeiro slot com EDX=0 em **`0x4faa35`**.

Quando o item tem o destrutor de `ActorComponent`, o caminho de remoção da raiz está dentro desse destrutor, depois da etapa de invalidação acima. Isso impede resumir o sistema como “sempre remove do registro e depois expira o wrapper”. O ordenamento local comprovado neste caminho é o inverso para essas duas operações.

O caller `0x52a530` chama a rotina de limiar `0x4fa8c0` e a limpeza `0x4fa950`. Há controles de lote/tempo, mas o nome semântico dessa rotina, a thread concreta e sua disciplina de sincronização não foram deduzidos desses padrões.

### 4.3 O wrapper pode sobreviver expirado

**V4-K05:** a limpeza de associação `0x2d82b80` chama o slot `+0x18` do wrapper. A cadeia selecionada percorre `0x29a8e60` → `0x2148390` → `0x20cc6b0` → `0x212e050` → `0x2d85f40`; caudas compartilhadas podem chegar diretamente à base. Em **`0x2d85fe7`**, `mov qword ptr [rbp+0x18],0` limpa o nativo de W após notificações.

No método `LoadSkeletonAndGraph`, as instruções `0x29bb2f4`/`0x29bb2f8` testam esse campo; o ramo expirado usa a mensagem `Calling method <%s> of an expired IObject.`. Isso corrobora a distinção entre existência do objeto Python e validade de sua associação nativa. A V3 já demonstrava a reutilização de uma associação existente; a V4 acrescenta a transição concreta para wrapper expirado.

A sequência de `0x10ea20` chama o callback de limpeza quando há associação, e só depois zera `H+8` e `N+0x18`. As notificações incluem chamadas indiretas. Reentrância e retenções durante esses callbacks continuam relevantes: não foi provado que toda observação concorrente veja um estado intermediário seguro.

O importado usado pelo helper `0x3f3950` foi resolvido como **`KERNEL32.dll!TlsGetValue`**, IAT RVA `0x4e34860`, em `selected-imports.json`. Isso prova uma consulta a TLS nesse helper, não identifica a thread executante de cada mutação. `LOCK XADD` no contador não equivale a um lock do mapa.

## 5. Fábrica, callback de metadados e caminhos pendentes

**V4-K06:** foi identificado o destino concreto do callable usado pelo resolvedor consultado na conversão nativo/Python:

- O construtor `0x1cb7100`, ligado ao módulo PyObjects por RTTI, instala o callable em `0x8e45608`. `V4-D08`/`V4-D09` e `resolver-rtti.json` preservam os COLs e TypeDescriptors do módulo e de seu callable.
- `V4-D02` preserva o ponteiro COL e a tabela em `0x55ca5f0`; o slot `+0x10` aponta para `0x1cb85b0`.
- `0x1cb85b0` recebe o nome por indireção e salta para `0x20cb120`.
- Essa rotina procura o nome na estrutura `0x8d17038`, invoca um callable pendente, remove a entrada e trata uma segunda estrutura em `0x8d17000` antes de retornar sucesso. As instruções `0x20cb175`, `0x20cb194`, `0x20cb1b9` e `0x20cb1d8` preservam esses pontos.

Isso sustenta uma etapa de **resolução/registro adiado por nome**. Não transforma o callback em evidência de um tipo Python dinâmico específico por instância. Os destinos de cada callable armazenado nas estruturas dependem do produtor da entrada; não foram todos resolvidos. A cadeia de fábrica de `ActorComponent` da V3 continua válida, sem estender sua conclusão a todo objeto retornável.

| Pendente anterior | Avanço V4 | Limitação restante |
|---|---|---|
| Callback de resolução | Adapter e rotina por nome identificados | Callables das entradas pendentes ainda não enumerados por completo |
| Limpeza do wrapper | Cadeia até `W+0x18=0` reconstruída | Reentrância, referências retidas e execução concreta |
| Cauda `0x899eb0` | Helper de remoção de ponteiro de vetor, com troca pelo último elemento | Não é nova remoção da raiz de atores |
| Getter `0x34c790` | Lê o global `0x80d5770` | Não é alias comprovado da raiz `0x8b7cd90` |
| Cauda `0x424c1b0` | Thunk seguido pelo CFG até rotina de liberação | Não classifica o payload por si só |
| Flag de skeleton `0x1163300` | Grava byte `+0x2ad=1`, limpa WORD `+0x2aa`, notifica virtualmente | Sem significado de gameplay atribuído |
| Cargas assíncronas | Captura e callbacks de associação selecionados | Capturar/encaminhar trabalho não prova qual thread o executa |
| Aliases da raiz | Todos os 21 acessos diretos descobertos e os seis callers do getter incluídos em CFGs | Propagação por ponteiros calculados, armazenamento de aliases e encerramento global continuam abertos |

`root-consumer-coverage.json` liga esses 27 pontos aos identificadores de instrução. “Coberto por CFG” não significa “todos os aliases fechados”.

## 6. Transformação e câmera: ganho concreto para a investigação externa

**V4-K07**, `V4-D04`–`V4-D07` e `spatial/SPATIAL.md`:

| Propriedade refletida | Cadeia comprovada | Efeito do getter |
|---|---|---|
| `IEntity.Transform`, tipo `Matrix4x3` | Metadado `0x4f60590` → wrapper `0x954ad0` → célula `0x4f601c0` → `0x95e880`, ajuste de this zero | Retorna `RCX+0x58` |
| `ICamera.ViewMatrix`, tipo `Matrix4x3` | Metadado `0x4f43b10` → wrapper `0x93f1a0` → célula `0x4f45130` → `0x964090`, ajuste de this zero | Retorna `RCX+0x41c` |

Não foram demonstrados nesses getters: transformação mundial, layout linha/coluna, eixo/unidade, câmera ativa, matriz de projeção, viewport, divisão por W ou world-to-screen. Não foi implementada uma fórmula de projeção usando pressupostos de outra engine.

O complemento `spatial/projection/PROJECTION.md` resolve duas pistas pelos seus produtores e consumidores:

- `GetMainCameraViewProjection` é registrado para **DecalCameraData**, callback `0x314e7f0`, implementação `0x314c250`. Constrói uma **PerspectiveCamera temporária**, com RTTI preservado, configura **2048×2048** e pode devolver identidade. Seu objeto-fonte vem da cadeia global `0x80d5980 → +0x58 → +0x58 → +0xd88`; a ligação ao getter refletido `ICamera.GetScreenSize` e a `ViewMatrix` é concreta, mas não prova equivalência com a imagem final.
- `CameraProjection` é registrado com callback `0x1abd000` e tamanho `0x40`. O callback copia 64 bytes de `[[RDX+0xb8]+0xfa0]`. Falta fechar o produtor desse armazenamento e a origem de RDX. Esse deslocamento não foi atribuído a ICamera.

Assim, o nome “MainCamera” não sustenta sozinho uma matriz utilizável no overlay. Os artefatos complementares preservam registro, callback, getters, slots e RTTI, sem substituir essa prova pela aparência do nome.

O terceiro complemento, `spatial/render-source/RENDER-SOURCE.md`, fecha um caminho do dispatcher `0x222ed0 → 0x7dac30 → 0x766370 → callback`. Nele, o RDX do callback vem do segundo argumento de `0x222ed0`. Um segundo consumidor acessa a mesma forma `[contexto+0xb8] → bloco+0xfa0`. Foram catalogadas 219 ocorrências candidatas e priorizados quatro escritores que copiam 64 bytes de um slot virtual `+0x70`, além de um inicializador por identidade. **Não está demonstrado que seus destinos sejam o mesmo bloco de `[contexto+0xb8]`.** Nem a coincidência do deslocamento nem a do slot virtual fecha esse alias ou identifica o tipo dinâmico.

Nomes literais qualificados procurados, como `IEntity.WorldPosition` e `ICamera.ProjectInner`, não apareceram em ASCII/UTF-16LE. A ausência literal limita essa estratégia de busca; não prova ausência funcional da operação.

## 7. Pesquisa pública e fontes

Foi usada pesquisa delegada com modelos Luna e gpt-6.1-sol de esforço baixo, além da conferência local. [O estudo autoral Globality](https://globality.live/case-bloodstrike) descreve um projeto privado e não fornece fonte nem identificação de amostra que permita equipará-lo ao hash desta investigação. Seus nomes servem para formular buscas locais; nenhum offset da página foi transferido.

Resultados de Unreal que usam o nome `AnimationCore` foram descartados como analogia de layout. A coincidência do nome não demonstra parentesco de implementação com Messiah. Referências públicas a MPK de outros jogos também não provam compatibilidade com estes pacotes. A busca não localizou uma implementação pública de `GetAllActors` atribuível a esta amostra; isso não demonstra inexistência em toda a internet.

`audit-v4/public-research.md` é o registro da pesquisa delegada, incluindo pistas descartadas, não um catálogo de fatos binários comprovados. Prevalecem os bytes e cadeias locais reproduzidos.

### Reconhecimento local dos pacotes

A pesquisa de código encontrou um [parser MPKINFO V1 em Rust](https://raw.githubusercontent.com/fangfang1984/netease-messiah-tools/main/mpk/src/lib.rs). Ele não foi executado e não aceita a forma encontrada localmente. Os primeiros DWORDs dos índices Engine e Resources são **4**, e não 1. O índice Patch tem outro cabeçalho; não foi forçado no mesmo parser.

`probe_mpk_v4.py` testou uma hipótese de header de oito bytes, registros de 24 bytes `<QQII` e trailer de 16 bytes. Os **56** registros de Engine e **201.388** de Resources cabem exatamente nesse particionamento. Usando o bit baixo do último campo como indicador de diretório e os demais como índice do sidecar, todos os intervalos candidatos de arquivo cabem nos respectivos MPKs. Amostras contêm assinaturas coerentes como `ZZZ4`, `.MESSIAH`, XML e dados de fonte. São evidências fortes de consistência do layout candidato, não prova do significado de cada campo, da função de hash dos identificadores nem da semântica dos arquivos. Hashes dos dois índices e exemplos constam em `mpk-candidate-probe.json`.

Essa rota permite procurar produtores de gameplay nos recursos sem presumir que exista Python legível. Não foi extraído nem executado código dos pacotes nesta etapa.

O inventário complementar `assets/ASSETS.md` amostrou **197.336 cabeçalhos**, de até 32 bytes: 49 de Engine e 197.287 de Resources. Não encontrou as três assinaturas literais testadas no início dos payloads (Lua, shebang e um padrão de magic CPython). Isso não exclui scripts em outros formatos ou dentro de compressão/encapsulamento. Os textos pequenos inspecionados fornecem fontes/localização de editor e inventários; não forneceram uma classificação independente jogador/NPC. Os payloads `META` examinados exibem vocabulário de serialização PhysX, sem vínculo demonstrado com produtores de gameplay. A classificação permanece aberta após essa busca adicional.

`verify_assets_v4.py` reproduz independentemente essa amostragem a partir dos índices com hash fixado. O grupo de cinco prefixos textuais de Resources no inventário delegado inclui quatro JSON-like e um XML-like; o verificador preserva essa distinção em `assets/header-reproduction.json`. Houve 34 leituras completas pequenas na exploração (29 META e cinco outras entradas), separadas da amostragem de cabeçalhos. O comando de inventário original era inline; foi preservada essa limitação, sem afirmar que existia um script original salvo.

## 8. Comparação V2 × V3 × V4

| Tema | V2 | V3 | Nova conclusão V4 |
|---|---|---|---|
| Chave | Campo usado nas operações | Origem do valor ainda aberta; duplicata sem substituição demonstrada | Dois construtores atribuem serial por contador atômico compartilhado de 32 bits; unicidade é condicional |
| Payload e categorias | Hipóteses sobre atores | Componente, ator associado e Parent separados; família C++ sustentada | Produtor concreto de novo ator e rota `LoadSkeletonAndGraph` ligados; categorias de gameplay continuam abertas |
| Lifetime | Caminhos parciais | Remoção, associação e limpeza H/A/W/P documentadas | Expiração concreta de W e caminho que invalida antes do destrutor reconstruídos |
| Conversão | Inferências iniciais de wrappers | Fábrica e reutilização sustentadas | Callback de registro adiado por nome ganha destino concreto; tipo dinâmico por instância continua não observado |
| Máscara `0x10` | Semântica em investigação | Correspondência refletida a `IEntity.IsInWorld` | Preservada; não virou filtro de jogador, inimigo ou validade de lifetime |
| Espaço e câmera | Sem cadeia suficiente | Fora das conclusões centrais | Dois getters ligados a metadados; projeção e seleção de câmera ainda não demonstradas |
| Integridade | Base selecionada | Dupla decodificação e manifesto | V3 reproduzida integralmente; nova seleção com 67 CFGs e 8.628 instruções únicas |

**Confirmadas nesta etapa:** geração da chave nos construtores selecionados; serial compartilhado com skeletons; comportamento de duplicata; expiração do nativo de W; ordem invalidação → destrutor em um caminho concreto; getters de Transform e ViewMatrix.

**Rejeitadas como conclusões sustentadas:** interpretar a chave como ID de jogador/rede; interpretar `IsInWorld` como classe de gameplay; tratar o contador como 64 bits; supor remoção sempre anterior à expiração; equiparar existência de P a validade de N; chamar ViewMatrix de projeção completa. A rejeição é da inferência, não prova de que conceitos adicionais nunca existam.

**Abertas:** categorias de gameplay, associação exclusiva A→C, reset/wrap/colisão, destruição global da raiz, aliases calculados, sincronização, tipos e fábricas observados em instâncias, câmera/projeção e cadeia externa completa.

## 9. Validação dinâmica ainda necessária

Não foi identificada build de laboratório ou trace de eventos na pasta da investigação. Isso não afirma ausência em outros locais. Esta entrega contém **zero eventos de execução**; não mistura fixtures ou simulação com observação real.

O arquivo `audit-v4/event-schema.csv` contém apenas o cabeçalho para futura coleta, incluindo:

```text
sequencia | thread | operacao | chave | componente | Parent
metadado_nativo | tipo_RTTI | fabrica | W | P | IsInWorld
geracao_componente | geracao_ator | geracao_Parent | geracao_W | geracao_P
```

Geração de vida deve ser atribuída a partir de criação/destruição observadas, por identidade e endereço, nunca deduzida apenas do contador ou do endereço. “Mesmo endereço” depois de destruição não estabelece “mesma instância”. Cobertura incompleta do início da vida exige geração desconhecida, sem inventar número inicial.

Eventos discriminantes: criação de ator/componente/Parent, associação, inserção e duplicata, entrada/saída do mundo, remoção, início/fim de invalidação, destruição e recriação com reuso de endereço. Precisam decidir exclusividade, política real de colisão, thread, seleção de fábrica e comportamento de referências mantidas após expiração. Para espaço/câmera, ainda são necessárias observações que distingam transformação local/mundial e câmera de renderização/mira.

## 10. Reprodução e limites da entrega

Scripts em `StaticAnalysis`:

1. `reproduce_v3_for_v4.py`: verifica manifesto, baseline, amostra e evidências V3 sem regravá-las.
2. `discover_v4.py`: busca linear nos registros de unwind; produz descoberta com limites explícitos.
3. `audit_v4.py --sample <BloodStrike.exe>`: extrai os CFGs e blocos selecionados, verifica bytes/comprimentos/alvos em dois decodificadores e confirma o baseline V3 ao terminar.

Os dois primeiros scripts preservam o caminho local fixado da amostra; o terceiro recebe caminho por argumento. Dependem do parser e dependências locais já utilizados pela V2/V3. Não carregam o executável como módulo. A descoberta contém possíveis falsos positivos de decodificação linear, submetidos a CFG quando sustentam conclusão.

Resultado da nova seleção central: **67 CFGs, 8.802 registros de instrução, 8.628 instruções únicas, oito entradas atravessando regiões de unwind, nove blocos de dados, sete alegações selecionadas e zero divergências de bytes/comprimento/alvos**. Os complementos espaciais têm suas próprias seleções e não estão somados a essa contagem. Caudas fora do limite espacial constam no resumo; os destinos relevantes foram incluídos como seeds separados. Isso não torna indireções arbitrárias exaustivas.

`verify_v4.py --sample <BloodStrike.exe>` confere novamente os bytes/endereço de arquivo dos registros JSON reconhecidos, os comprimentos de instrução, o baseline V3 e os IDs citados neste relatório; produz `delivery-verification.json` e um manifesto V4 separado. O manifesto não inclui seu próprio hash. Essa verificação não transforma inferências semânticas em fatos de execução.

O resultado entrega uma base estática mais precisa para o trabalho externo. **Não há cheat funcional entregue ou teste de ESP/aimbot em execução nesta auditoria.** O próximo avanço autônomo é ligar câmera/projeção e produtores de gameplay a essas identidades, sem preencher as lacunas com offsets de outra amostra.
