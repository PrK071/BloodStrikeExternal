# Blood Strike — Auditoria estática V3

Data: **21/10/2026**, America/Sao_Paulo. Base: [Auditoria V2](AUDITORIA-V2.md), Steam build **25981220**, patch **126**.

A V3 sustenta três conclusões novas: o filtro `0x10` corresponde à representação refletida de **`IEntity.IsInWorld`**; o ponteiro intermediário é **`IComponent.Parent`**, declarado como `IObject`; e existe uma fábrica registrada como **`ActorComponent`** que constrói o wrapper C++ **`Messiah::PyActorComponent`**. Foram também demonstrados outros caminhos de inserção, remoção e destruição, além da reutilização e limpeza da associação nativo/Python.

Isso esclarece o caminho de conversão típico, mas não fecha o conjunto de tipos dinâmicos do registro. Não foi demonstrada uma segunda categoria inserida na mesma raiz, nem a exclusividade de jogadores, inimigos ou objetos de gameplay.

## Escopo, integridade e identificação das evidências

Análise dos arquivos em disco, sem executar o jogo, abrir ou modificar seu processo ou interferir no anticheat. Os interpretadores e decoders usados são ferramentas de análise; o PE foi lido como dados. Nenhum endereço foi apresentado como base real sob ASLR, e nenhum campo de jogador, câmera ou bones foi derivado por suposição.

| Item | Resultado |
| --- | --- |
| Amostra | `E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe` |
| SHA-256 original, reconferido no início e no fim | `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747` |
| Base preferencial | `0x140000000` |
| Integridade da V2 | Manifesto anterior conferido; arquivos anteriores preservados |
| Resultado da conferência selecionada | `PASS_SELECTED_EVIDENCE` |

Todos os endereços abaixo são **RVAs**; deslocamentos `+campo` são relativos ao objeto explicitado. A conversão para offset de arquivo e VA preferencial está em [address-map.json](audit-v3/address-map.json). As referências à raiz global em extensão virtual não representam conteúdo observado em memória.

Os IDs **A01–A05, G01–G10, C01–C05, M01–M04 e D01–D02** permanecem nos arquivos originais, sem renumeração. [baseline-lock.json](audit-v3/baseline-lock.json) fixa os hashes de entrada, inclusive os resultados anteriores. [v2-claim-state.json](audit-v3/v2-claim-state.json) liga cada ID da V2 aos achados novos, sem reescrever sua classificação histórica.

Na V3, `V3-I-<RVA hexadecimal>` identifica uma instrução em [disassembly.txt](audit-v3/disassembly.txt), com bytes, RVA, VA preferencial e offset também em [reachable-code.json](audit-v3/reachable-code.json). `V3-D01` a `V3-D08` identificam blocos brutos de dados e ponteiros em [data-evidence.json](audit-v3/data-evidence.json). Os IDs de conclusão e suas limitações estão em [claims.json](audit-v3/claims.json).

**Confiança alta** significa ligação direta por instruções, fluxo ou metadados relidos. **Parcial** delimita uma conclusão positiva cuja extensão continua aberta. Uma conclusão descartada abaixo rejeita a inferência descrita, sem afirmar que todos os cenários opostos tenham sido provados.

## 1. Ciclo de vida e tipos do registro

### Mutações ligadas à raiz correta

Foram separados os callers de um helper genérico daqueles que efetivamente recebem a raiz de `GetAllActors`. A varredura encontrou **21 referências diretas à raiz**, dentro dos registros de unwind, e **seis chamadas diretas ao getter**. O próprio getter, leaf sem unwind, foi incluído separadamente no CFG selecionado. São contagens de formas cobertas, não prova de inexistência de aliases.

| Caminho | Evidência nova ou aprofundada | Conclusão sustentada |
| --- | --- | --- |
| Substituição/associação do ator, `0x19c0100` | `0x19c0203` → `0x19c020a` remove a chave anterior; `0x19c0409` → `0x19c0410` insere o componente | A associação pode desfazer a entrada anterior antes de criar outra; a inserção já observada em G06 integra um ciclo maior |
| Callback virtual do componente, `0x19d4b00` | Slot principal `+0x70`, `V3-D06`; `0x19d4c66` testa o byte do ator `+0x2ad`; `0x19d4c75` guarda o componente; `0x19d4c84` obtém a chave; `0x19d4caa` insere | Segundo callsite de inserção diretamente ligado à mesma raiz |
| Callback virtual, `0x19d4eb0` | Slot principal `+0x78`, `V3-D06`; `0x19d50a1` obtém a chave e `0x19d50b4` chama a remoção com a mesma raiz | Terceiro callsite de remoção, associado ao caminho de desligamento do componente |
| Destruição de `ActorComponent`, `0x19bfb60` | Reinstala suas tabelas; testa `ator+0x2ad` em `0x19bfb9f`; remove em `0x19bfbbb`; libera referências nativas e salta à base em `0x19bfdf1` | A remoção precede a liberação das referências nesse caminho e depende do estado do ator |
| Destrutor com opção de desalocação, `0x1a1e560` | Chama `0x19bfb60` em `0x1a1e56f`, depois examina flags de destruição e pode desalocar | A rotina anterior está ligada ao caminho de destruição virtual, não é apenas um helper de consulta |

**V3-L01 e V3-L05**: confiança alta para esses callsites; cobertura global do ciclo de vida continua parcial. As demais referências diretas foram examinadas como consultas, buscas por chave e iteração. Por exemplo, `0x19c55e0` procura chaves provenientes de objetos nativos e copia os componentes encontrados para um vetor; `0x19f3dc0` percorre o registro e outros containers ao montar uma coleção de componentes. Isso não adiciona um novo tipo de payload à raiz.

O byte **`Character::Actor`/base de animação `+0x2ad`** não deve ser confundido com o bit **`Parent+0x130 & 0x10`**. O slot virtual do ator `+0x28` passa pelo thunk `0x16d17d0` e pelo helper `0x1163300`, que grava `1` em `0x1163304`. O caminho do slot `+0x30`, `0x16d17e0` → `0x1163340`, grava `0` em `0x11633d2`. Esses fatos ajudam a explicar a guarda da inserção/remoção; não recuperam o nome fonte exato do estado nem o transformam em um indicador de jogador.

### O container não destrói o payload nesses helpers

O helper `0x254390` tem comportamento de inserção com unicidade de chave:

- Ao encontrar chave existente, grava o nó de retorno e o indicador `0` em `0x254435`/`0x254438`; esse ramo retorna sem substituir `[nó+0x18]`.
- Ao criar um nó, copia quatro bytes da chave em `0x254497` e o ponteiro recebido em `0x25449e`. A inserção propriamente dita não incrementa uma referência do payload.
- O caminho de erro referencia `unordered_map/set too long` em `0x254630`. Isso fortalece a interpretação de container hash dessa família, sem recuperar a especialização fonte ou o sinal da chave.

O helper `0xad0640` atualiza buckets e ligações, decrementa o número de elementos e libera **o nó de `0x20` bytes** em `0xad070f`. Ele não desreferencia `[nó+0x18]` para destruir o componente. Portanto, **“remover a entrada destrói o componente” está rejeitado para esse helper**. A interpretação sustentada é de um índice que guarda ponteiros sem reter/liberar o payload nessas operações; a política de ownership de todo o sistema permanece aberta. **V3-L02, confiança alta no escopo local.**

### Hierarquias e categorias: o que mudou

O caminho de destruição percorre `ActorComponent` → `SkeletonComponent` → `ISkeletonComponent` → `IComponent` → `IObject`, coerente com RTTI, instalação das tabelas e chamadas das bases. O ramo `ITickable` permanece distinto. `Character::Actor` continua pertencendo ao ramo de animação, separado do componente que é guardado no nó.

O inventário de hierarquias relido encontra somente **`Messiah::ActorComponent`** no conjunto de classes catalogadas que declaram essa base. **Não foi encontrada uma segunda categoria comprovadamente inserida na mesma raiz.** Isso reduz o suporte à hipótese de um registro heterogêneo entre os caminhos conhecidos; não prova homogeneidade universal. Classes sem RTTI, módulos externos, caminhos indiretos e subclasses fornecidas dinamicamente continuam fora dessa inferência negativa. **V3-L03: parcial.**

Um falso positivo foi eliminado: `SkeletonComponent` também chama `0xad0640`, mas passa **outra raiz**, `0x8143e90`, em `0xad6144`. Outro caller do mesmo helper de inserção, `0x225740`, usa um container embutido no argumento em `+0xf90`. Compartilhar o corpo de um helper não identifica o container nem o tipo de seu payload. **V3-L04: inferência descartada, confiança alta.**

**Limite de destruição:** a alocação e instalação da raiz estão demonstradas, assim como as remoções locais. Não foi reconstruído um caminho completo de destruição global desse container, sua ordem no encerramento nem todas as invalidações de aliases. A V3 não declara o ciclo de vida global encerrado.

## 2. Conversão nativo/Python: fábrica, tipos e identidade

### Fábrica efetivamente sustentada pelos metadados

O nome de registro deixou de ser a única pista. A ligação positiva é:

1. `0x29a9030` prepara um callable com tabela em `0x580bcd8` (`0x29a90b5`), usa a string **`ActorComponent`** (`0x29a90cb`) e registra o delegado no contexto de conversão (`0x29a90f9` → `0x2d82a00`).
2. O COL dessa tabela identifica o callable de **`RegisterObjectClass__ActorComponent`**. Seu slot `+0x10` aponta para `0x29abcd0`, que chama `0x29aec10` e extrai o wrapper em `+0x20` do objeto Python produzido. **V3-D04.**
3. `0x29aec10` solicita o tipo pelo helper `0x29c1b40`, usa seu alocador indireto, constrói a cadeia de wrappers e instala a tabela `0x580b050` em `0x29aec9c`.
4. O COL dessa tabela identifica **`Messiah::PyActorComponent`**, com as bases C++ **`PySkeletonComponent` → `PyISkeletonComponent` → `PyIComponent` → `PyIObject`**, além dos subobjetos de referência/Asyncore. A hierarquia foi relida dos descritores. **V3-D05; hierarchies.json.**

**V3-B01: confirmada, confiança alta.** Existe essa fábrica e ela constrói esse wrapper C++. A conclusão é condicional à seleção do delegado; não equivale a observar que todas as entradas vivas sempre usam essa fábrica.

O descritor nativo em `0x7998b00` também contém `ActorComponent` e o endereço do slot `0x8c34bc0`. `0xab720` inicializa esse slot e o construtor do componente o encaminha à base em `0x19bf52d`/`0x19bf534`. Isso conecta o nome nativo à construção, sem equiparar o descritor de reflexão ao `TypeDescriptor` RTTI. **V3-D03.**

### Seleção e fallback não são um teste RTTI universal

No conversor `0x2d82d90`, o código consulta a associação existente e, se necessário, lê os metadados em **`[nativo+8]`**. Os acessos observados são:

| Campo relativo ao metadado | Fluxo demonstrado |
| --- | --- |
| `+0xc0` | Cache de resolução consultado antes de selecionar a fábrica |
| `+0xb8` | Relação usada para procurar uma resolução ancestral; helper recursivo `0x2d84e90` |
| `+0xc8` | Referência ao objeto que contém o delegado de construção |
| Delegado `+0x38`, slot virtual `+0x10` | Invocação indireta da fábrica em `0x2d82e44` |

O registro em `0x2d82a00` escreve `+0xc8` em `0x2d82aa4` e torna `+0xc0` autorreferente em `0x2d82aab`. Já o fallback consulta um callback indireto antes de gravar a resolução ancestral; quando esse callback retorna verdadeiro, o store local é pulado. Portanto, o resultado não pode ser reduzido a “sempre instancia o wrapper da classe C++ mais derivada”. Uma classe sem fábrica própria pode usar a resolução ancestral, e o callback amplia as possibilidades não resolvidas estaticamente. **V3-B02: confirmada para o mecanismo, com limites explícitos.**

### Duas camadas de associação e reutilização

Convenção desta seção: **N** = objeto nativo; **H** = controle/handle; **A** = registro de associação; **W** = wrapper C++; **P** = objeto Python. São rótulos analíticos, não nomes fonte recuperados.

```text
N+0x18 -> H
H+0x08 -> N                 H+0x10 -> A
A+0x00 -> H    A+0x08 -> W   A+0x10 -> P
W+0x08 -> P                 P+0x20 -> W
```

`0x2d82d98`/`0x2d82da4` recuperam `H` e `A`. Havendo associação, `0x2d82dab` desvia para o retorno em `0x2d82ef9`, sem chamar a fábrica novamente. No caminho de criação, `0x10e8a0` recupera ou cria `H`; o conversor aloca `A` com `0x20` bytes, instala os backlinks e guarda `W` e `P`. A fábrica instala os pares `W+8`/`P+0x20` em `0x29aecd4`/`0x29aecd8`.

O helper do controle usa `lock cmpxchg` para tentar incrementar sua contagem existente; se ela não estiver viva, pode limpar a referência antiga e criar outro controle de `0x30` bytes. Isso demonstra **reutilização durante a vida da associação**, não unicidade eterna de endereço ou identidade Python após destruição e recriação. **V3-B03: confirmada.**

Os números `+0x10` e `+0x18` nesta seção são deslocamentos de ponteiros/contagens em objetos diferentes. Não têm relação semântica demonstrada com a máscara `0x10` do filtro.

### Referências, limpeza e limites dos tipos dinâmicos

Há contagens separadas: incremento de `W+0x10` em `0x2d82ec3`; incremento condicionado da referência de `P` em `0x2d829d0`; decrementos de objetos Python, com chamada de desalocação quando apropriado; e liberação do controle via `0x10e1f0`. A rotina `0x2d82b80` limpa a associação: decrementa referências, zera `H+0x10` em `0x2d82cee`, libera o controle e desaloca `A`.

A inicialização registra essa rotina pelo helper `0x10ea90`, no slot global `0x80cfff0`. A busca ampliada também localizou chamadas indiretas por esse slot em `0x10e3fd`, `0x10ea3b` e `0x10eaa4`, que não seriam encontradas procurando somente CALL relativo. Em particular, `0x10ea20` segue `N+0x18` → `H+0x10`, chama a limpeza se houver associação e depois zera `H+8` e `N+0x18` em `0x10ea4d`/`0x10ea51`. Há, portanto, um caminho concreto de invalidação dos vínculos; isso ainda não resolve todos os callers, ordens de destruição ou substituições possíveis do callback. **V3-B04: parcial para ownership e sincronização globais.**

Não foi atribuído automaticamente o nome **GIL** aos helpers de estado `0x2adc1c0`/`0x2adc290`. Os incrementos locais observados não estabelecem a política completa de threads, coleta ou acesso concorrente ao registro.

O helper de tipo retorna o armazenamento **`0x7a07d30`**, e a fábrica invoca alocação e possível inicialização por ponteiros desse tipo. Porém, o slot compatível com **`tp_name`**, em **`0x7a07d48`**, está **zerado no arquivo**. Assim, `Messiah::PyActorComponent` é um nome C++ sustentado pelo RTTI; `ActorComponent` é um nome de registro sustentado pelo código; o nome Python qualificado final não foi observado. Não foram demonstrados `type(P)` de cada entrada, substituições do delegado em execução ou a ausência de tipos derivados. **V3-B05: parcial.**

## 3. Máscara `0x10`: significado demonstrável

### Correspondência direta com `IEntity.IsInWorld`

O bloco em `0x4f64210` contém estes pares de dados e funções, preservados integralmente em **V3-D01**:

| Slot RVA | Conteúdo |
| --- | --- |
| `0x4f64210` | String de classe `IEntity` |
| `0x4f64220` | Tipo `bool` |
| `0x4f64230` | Nome `IsInWorld` |
| `0x4f64240` | Nome qualificado `IEntity.IsInWorld` |
| `0x4f642d0` / `0x4f642d8` | Accessors `0x952640` / `0x952660` |
| `0x4f642f0` / `0x4f642f8` | Accessors adaptados `0x952710` / `0x952740` |

Os ponteiros de função possuem relocação DIR64 e os destinos foram conferidos. O getter lê o byte **`[objeto+0x130]`**, desloca quatro bits e aplica `& 1`. O setter limpa `0x10`, desloca o valor recebido quatro bits e faz OR no mesmo byte. Os accessors adaptados repetem a operação com conversão de argumentos. A correspondência depende desse vínculo entre dados e fluxo, não apenas da proximidade de uma string.

**V3-F01: confirmada, confiança alta.** O bit usado pelo callback tem a representação da propriedade refletida `IsInWorld`. Isso avança G10: a finalidade nominal do bit deixou de ser totalmente desconhecida.

### De qual objeto é o bit

**V3-D02** contém `IComponent.Parent`, declara o tipo **`IObject`** e aponta para o getter `0x58b3e0`. Esse getter retorna **`[componente+0x40]`**. O setter passa pelo helper `0x141d50`, que consulta e pode gravar o mesmo campo.

No callback, `0x32597c0` recupera o componente do nó; `0x32597c4` lê `Parent`; `0x32597c8` verifica o ponteiro; `0x32597cd` testa `Parent+0x130 & 0x10`. **V3-F02: confirmada.**

A descrição precisa passa a ser: **o callback converte componentes cujo Parent não é nulo e passa no teste usado por `IEntity.IsInWorld`**. O descritor declara `IObject`, e o callback não executa uma checagem RTTI demonstrada antes do acesso. Portanto, não se generaliza “todo Parent de todo componente é IEntity”; o caminho pressupõe uma representação compatível nos objetos que alcançam esse acesso.

### Leituras, gravações e explicações alternativas

| Evidência | Resultado |
| --- | --- |
| Construtor de `IEntity`, `0x88cafb` | Inicializa o dword em `+0x130` com `0x1285`; seu bit `0x10` começa limpo |
| `0x89680f` | Liga `0x10` por OR |
| `0x896f97` | Desliga `0x10` por AND com `0xef` |
| `0x89f0b2` / `0x89f0be` | Testa o estado antes de chamar a rotina que liga o bit |
| `0x89f262` / `0x89f26e` | Testa o estado antes de chamar a rotina que desliga o bit |
| Setters de reflexão | Também podem alterar a representação do bit |

Esses usos são coerentes com transições de estado de mundo. **V3-F03** confirma as operações e as guardas; nomes fonte exatos das rotinas continuam desconhecidos. Como há setters diretos, o valor isolado não demonstra que todos os efeitos de uma transição, como inserção em subsistemas específicos, tenham ocorrido.

Não há evidência direta para chamar esse bit de “inimigo”, “jogador”, “visível”, “renderizado”, “vivo”, “em partida” ou “ativo” no sentido de gameplay. **V3-R02** rejeita essa inferência a partir do nome `Actor` ou do bit. Isso não exclui que jogadores possam possuir componentes elegíveis.

## 4. Cobertura, controles e falsos positivos

A V3 reutiliza o parser bruto da V2, com **iced-x86** para percurso e **Capstone** para conferência adicional. Não alega uma terceira implementação independente de parser. A diferença metodológica principal é a cobertura ampliada e a ligação entre funções, descritores e callsites.

| Checagem | Resultado |
| --- | --- |
| Registros de unwind varridos para descoberta | **309.153** |
| Registros de decodificação na descoberta linear | **18.587.982** |
| Decodificações inválidas nessa descoberta | **11.007**, registradas e excluídas como evidência positiva |
| Entradas selecionadas para CFG | **75** |
| Instruções alcançáveis únicas selecionadas | **8.018** |
| Divergências de bytes/comprimentos no segundo decoder | **0** |
| CFGs que atravessam mais de um registro de unwind | **8** |
| Candidatos por deslocamento `+0x130` | **10.398** acessos; não são 10.398 usos de `IsInWorld` |
| Hash da amostra e imutabilidade dos artefatos anteriores | Reconferidos ao final |

Também foram conferidos entre decoders **282 destinos RIP-relative** e **1.606 destinos de branches**, sem divergências. Há **121 transferências indiretas** inventariadas. As contagens e os resultados estão em [summary.json](audit-v3/summary.json). Os nomes das operações sozinhos não constituem prova semântica.

Exemplos concretos de cobertura entre unwind: `0x141d50` alcança **nove** registros; `0x10e1f0`, **quatro**; os conversores `0x2d829a0` e `0x2d82d90`, **três** cada. O percurso não para apenas porque mudou o registro. Chamadas diretas relevantes são analisadas como entradas separadas, sem fingir execução de suas instruções pelo CFG chamador.

Caudas fora do limite de percurso são listadas em `unfollowed_targets`. Algumas foram cobertas por outra entrada, como `0x19bfb60` → `0xad6090`, `0xa030d0` → `0x1416d0` e `0x16d17d0` → `0x1163300`. Outras, como `0x899eb0` e certos helpers genéricos, continuam fora do fechamento semântico desta rodada. Calls/jumps indiretos estão inventariados em [indirect-transfers.json](audit-v3/indirect-transfers.json); parte dos slots da fábrica foi resolvida pelos dados, mas não se presume resolução de todos os destinos.

O resultado **`PASS_SELECTED_EVIDENCE`** confirma a conferência selecionada. A varredura linear inclui regiões que não podem ser aceitas como fluxo alcançável apenas por estarem no diretório de unwind; a origem de todas as decodificações inválidas não foi determinada. Essa varredura não valida a imagem inteira nem toda leaf function. **V3-R01.**

Foram controlados estes falsos positivos semânticos:

- **Mesmo helper, outra raiz:** `SkeletonComponent` e o container em `argumento+0xf90` não demonstram heterogeneidade de `GetAllActors`.
- **Mesmo deslocamento, outra estrutura:** `SkeletonComponent+0x130` é usado como endereço de um container em `0xad60e6`; não é o byte de flags de `IEntity`. A busca também captura acessos à pilha e campos de tipos alheios.
- **Nome C++ versus tipo Python:** o RTTI de `PyActorComponent` não revela sozinho `tp_name` ou o tipo efetivamente presente em todas as listas.
- **Cache versus identidade universal:** a reutilização de uma associação existente não exclui recriação depois da invalidação.
- **Remoção de nó versus destruição do objeto:** o helper de erase não destrói seu payload.

## 5. Hipóteses e comparação V2 × V3

| Questão | V2 | V3 | Estado e confiança |
| --- | --- | --- | --- |
| Inserções na raiz de `GetAllActors` | Um caminho comprovado | Dois callsites ligados diretamente à raiz; remoção anterior na substituição | Confirmado no escopo, alta — V3-L01 |
| Remoção e destruição | Ciclo incompleto | Três callsites de erase; caminho de destruição virtual e bases; nó liberado sem destruir payload | Localmente confirmado; encerramento global aberto — V3-L02/L05 |
| Natureza dos elementos, G07 | `ActorComponent` em um caminho | Callbacks, destruição e consumidores reforçam a mesma família; sem segunda categoria comprovada | Continua parcial — V3-L03 |
| Heterogeneidade pelo reuso de helpers | Não resolvida | Callers de outras raízes foram separados | Inferência pelo helper rejeitada; heterogeneidade global aberta — V3-L04 |
| Fábrica de wrappers | Conversor genérico e fábrica indireta | Nome `ActorComponent` → callable → fábrica → `Messiah::PyActorComponent` | Ligação condicional confirmada, alta — V3-B01 |
| Tipagem dinâmica | Metadados e associação incompletos | Cache, relação ancestral e callback de resolução rastreados | Mecanismo confirmado; tipo de cada entrada aberto — V3-B02/B05 |
| Identidade Python | Reutilização genericamente observada | Duas camadas de associação, caminho sem nova fábrica e limpeza dos backlinks | Reutilização confirmada; ownership/concorrência parciais — V3-B03/B04 |
| Ponteiro intermediário `+0x40` | Objeto relacionado sem nome sustentado | Getter e descritor `IComponent.Parent`, declarado `IObject` | Confirmado, alta — V3-F02 |
| Máscara `0x10`, G10 | Teste comprovado; significado desconhecido | Accessors de `IEntity.IsInWorld`, leituras, OR/AND e estado inicial | Representação nomeada confirmada, alta — V3-F01/F03 |
| `0x10` como jogador/inimigo/visibilidade | Sem evidência | Sem verificação de identidade de gameplay; propriedade refletida é outra | Inferência rejeitada — V3-R02; exclusividade G08 segue aberta |
| Identidade fonte do container, G09 | Hipótese de hash/map | Branch de duplicata e erro `unordered_map/set too long` reforçam a família | Especialização exata e sinal da chave continuam abertos |
| Unwind como função fonte inteira, A03 | Inferência já descartada | 8 CFGs selecionados cruzam registros; limites e indireções explícitos | Descarte mantido — V3-R01 |

Foram classificadas **15 conclusões V3: 9 confirmadas, 4 parciais e 2 inferências descartadas**. São achados incrementais, não recontagem das 26 linhas da V2. Os estados históricos da V2 foram preservados; G07 continua parcial e G10 ganhou a ligação semântica descrita acima. Questões de câmera, versão exata do runtime, rede e scheduling não receberam conclusão nova nesta rodada.

## 6. O que ainda exigiria validação dinâmica controlada

Nenhuma destas validações foi executada. Elas são necessárias para converter as limitações abaixo em conclusões sobre instâncias reais:

| Lacuna | Observação necessária |
| --- | --- |
| Tipos efetivamente presentes | Correlacionar cada nó com metadado nativo, vptr/COL, fábrica selecionada, wrapper e tipo Python efetivo, inclusive objetos fora do caminho típico |
| Identidade e reutilização | Verificar se conversões repetidas da mesma instância mantêm o mesmo `P`; acompanhar invalidação e posterior recriação sem confundir reutilização de endereço com identidade |
| Ownership e encerramento | Acompanhar a ordem de erase, liberação do ator, limpeza de `H`/`A`, destruição do componente e eventual destruição da raiz; verificar aliases pendentes |
| `IsInWorld` e efeitos concretos | Correlacionar o valor refletido com chamadas de transição e estados dos subsistemas; testar a diferença entre setter direto e rotina com efeitos adicionais |
| Callbacks e concorrência | Observar os destinos efetivos dos callbacks de resolução, contexto de execução e sincronização durante enumeração e mutação |
| Semântica de gameplay | Estabelecer por evidência independente quais componentes pertencem a jogadores, NPCs ou outros objetos; a V3 não fornece essa classificação |

## Reprodução e arquivos

Na pasta original da investigação:

```powershell
# PowerShell | Auditoria V3 | análise de arquivos PE em disco
& 'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\run-audit-v3.ps1'
```

O script usa as dependências locais já existentes da V2. `audit_v3.py` verifica o SHA-256 antes de extrair, relê o manifesto anterior, percorre os alvos, confere evidências com dois decoders e só publica sucesso após as checagens finais. Uma falha publica `FAIL`, sem manter sucesso anterior. `seal_audit_v3.py` confere as ligações do relatório e cria o manifesto de entrega.

Arquivos adicionados: este relatório, `audit_v3.py`, `v3-claims-spec.json`, `run-audit-v3.ps1`, `seal_audit_v3.py` e a pasta `audit-v3/`. O código, os resultados e o relatório da V2 não foram editados. Os artefatos novos incluem os CFGs, dados brutos, inventário de indireções, catálogo de hipóteses e a comparação por ID. [artifact-sha256.json](audit-v3/artifact-sha256.json) fixa os arquivos da entrega.
