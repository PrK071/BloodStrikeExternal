# Blood Strike — auditoria estática V2

Data: 21/10/2026, America/Sao_Paulo. Amostra: Steam build **25981220**, patch **126**.

A auditoria fortaleceu as ligações entre tabelas virtuais, inicializadores C++, o registro de `GetAllActors` e o módulo de scripts `MCharacter`. O callback constrói uma lista Python a partir de um registro usado pelo ciclo de vida de `ActorComponent`. Isso não demonstra enumeração exclusiva de jogadores.

O escopo foi análise dos arquivos em disco. Não houve execução do jogo, consulta ou alteração de seu processo, injeção ou interferência em mecanismos de proteção. Nenhum offset de jogador, câmera ou bones foi inventado.

**Identificação e integridade**

| Propriedade | Valor observado |
| --- | --- |
| Executável | `E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe` |
| SHA-256 | `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747` |
| Tamanho | 141.431.288 bytes |
| Máquina / imagem | AMD64 / PE32+ |
| Timestamp COFF | `0x6acbbfba` = `2026-10-11 16:56:26 UTC` |
| Base preferencial | `0x140000000` |
| SizeOfImage / entry point | `0x94e9000` / RVA `0x424c4a4` |
| Build / patch | Manifesto Steam `25981220` / `pkgversion` `126` |

O hash é idêntico ao da primeira análise e permaneceu igual ao fim desta auditoria. O timestamp é uma declaração do cabeçalho, não uma data autenticada de compilação. VAs indicadas são preferenciais, sem consulta de base real/ASLR.

Os hashes dos JSONs anteriores e dos scripts de origem estão em `audit-v2/summary.json`. O relatório anterior foi preservado. A versão original do verificador, antes da correção descrita abaixo, foi preservada em `audit-v2/baseline-verify_evidence.py`, SHA-256 `e0e84e2557a5b22463354a6f80bd07b6c0bc43122ab12aea3e99272a87b4e28f`.

**Método independente e resultado da conferência**

Foi criado um terceiro parser PE em `audit_v2.py`, baseado em leitura de estruturas brutas. Ele não importa `pefile`, Capstone nem os parsers anteriores. O segundo desassemblador é **iced-x86 1.21.0**, distinto do Capstone usado antes. A independência aqui é de implementação do parser e do decoder; não significa revisão por outra pessoa.

| Conferência executada | Resultado |
| --- | --- |
| Registros antigos de instrução | 38.445 conferidos; 38.445 intervalos únicos |
| Bytes, offsets e comprimentos no segundo decoder | Zero divergências |
| Referências RIP-relative antigas | 370 destinos confirmados |
| Slots de vftable anteriores | 132 ponteiros confirmados, todos com relocação DIR64 |
| Ponteiros COL das 12 tabelas do núcleo | Confirmados e com relocação DIR64 |
| TypeDescriptors catalogados | 32.609 nomes e cabeçalhos relidos sem divergências |
| Hierarquias centrais | 12 COLs/descritores conferidos, sem divergência com o inventário |
| Diretório de unwind | 309.153 registros reconhecidos pelo parser independente |

Resultado: **PASS_STRUCTURAL**, em `audit-v2/summary.json`. Não foi encontrado falso positivo estrutural entre os alvos conferidos. Isso não transforma cada nome ou hipótese semântica em uma descoberta confirmada. Contagem exata de métodos, tipos sem RTTI e layouts completos continuam fora desse resultado.

A investigação complementar encontrou 1.291 registros de referência nas formas pesquisadas e exportou 55 unidades de código selecionadas. Desses registros, 1.239 acessam o contexto compartilhado de conversão em `0x8e455b8`; isso não equivale a 1.239 tipos de atores ou novas funções identificadas semanticamente. A busca cobre formas selecionadas de LEA/MOV/MOVSXD RIP-relative, CALL/JMP relativos e ponteiros absolutos alinhados. Não cobre todas as referências indiretas, construções de endereços nem todas as leaf functions sem unwind.

**Mapeamento RVA ↔ arquivo**

Para um RVA com bytes armazenados: `file_offset = PointerToRawData + RVA - VirtualAddress`, respeitando `SizeOfRawData`. `VA_preferencial = ImageBase + RVA`. O parser trata a extensão virtual sem bytes separadamente. Essa distinção segue o [formato PE documentado pela Microsoft](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).

| Seção | RVA inicial | Offset inicial no arquivo | Tamanho bruto | Tamanho virtual |
| --- | --- | --- | --- | --- |
| `.text` | `0x1000` | `0x600` | `0x4e32c00` | `0x4e32aef` |
| `.rdata` | `0x4e34000` | `0x4e33200` | `0x2801400` | `0x2801216` |
| `.data` | `0x7636000` | `0x7634600` | `0xa99400` | `0x189ee24` |
| `.pdata` | `0x8ed5000` | `0x80cda00` | `0x389c00` | `0x389b8c` |

| Objeto | RVA | Offset no arquivo |
| --- | --- | --- |
| Callback `GetAllActors` | `0x3259770` | `0x3258d70` |
| Rotina que instala o registro | `0x32362d0` | `0x32358d0` |
| Getter da raiz | `0x19d45e0` | `0x19d3be0` |
| Vftable `Character::Actor` | `0x5565060` | `0x5564260` |
| Vftable principal `ActorComponent` | `0x559b8f8` | `0x559aaf8` |
| Vftable secundária `ActorComponent` | `0x559b9f0` | `0x559abf0` |
| Vftable principal `SkeletonComponent` | `0x4fa22a0` | `0x4fa14a0` |
| Vftable secundária `SkeletonComponent` | `0x4fa2390` | `0x4fa1590` |
| Vftable `ICamera` | `0x4e57558` | `0x4e56758` |
| Armazenamento da raiz | `0x8b7cd90` | **Sem bytes no arquivo** |
| Endereço externo anteriormente citado | `0x8a8e810` | **Sem bytes no arquivo** |

O último par pertence à extensão virtual de `.data`. Nenhum offset de arquivo foi fabricado para esses endereços. O mapa completo desta rodada está em `audit-v2/address-map.json`.

**`GetAllActors`: registro, scripts e convenção de chamada**

O vínculo nome/callback permanece confirmado. Os bytes `48 8d 15 d3 00 02 00` no RVA `0x3239696`, offset de arquivo `0x3238c96`, resolvem para o callback `0x3259770`; em `0x323969d`, `48 89 50 08` escreve esse endereço no campo `+8` do registro. O nome é escrito em `+0`, flags `4` em `+0x10` e um ponteiro em `+0x18`, após solicitação de 32 bytes.

Novas evidências ligam o registro a **`MCharacter`**:

- `0x32362e2` carrega a definição de módulo no RVA `0x7a94790`; a chamada seguinte recebe essa definição e a versão de API `0x3f5`.
- O campo interpretado como `m_name`, no RVA `0x7a947b8`, aponta para a string `MCharacter` no RVA `0x5bb7038`.
- `0x323630e` referencia a mesma string na configuração do módulo.
- A rotina chamadora `0x3244db0` chama essa inicialização e também usa `MCharacter` em `0x3244dce`.

Os dados são compatíveis com `PyModuleDef`, apoiados pela [documentação oficial da API de módulos](https://docs.python.org/3.14/c-api/module.html#c.PyModuleDef). O módulo e o registro são evidência desta build; nomes fonte exatos das rotinas anônimas não foram recuperados. `CharacterImp`, encontrado em outros nomes de bindings, não foi confundido com o nome deste módulo.

A flag `4` seleciona o dispatcher em `0x2abfd80`, carregado em `0x2abf926`. Em seu caminho válido:

| RVA | Bytes | Operação observada |
| --- | --- | --- |
| `0x2abfe72` | `48 8b 4b 18` | Carrega o argumento self em RCX |
| `0x2abfe76` | `33 d2` | Zera EDX, fornecendo segundo argumento NULL |
| `0x2abfe78` | `41 ff d0` | Chama indiretamente o callback carregado em R8 |

Esse fluxo é coerente com `METH_NOARGS`. A [API C do Python](https://raw.githubusercontent.com/python/cpython/v3.14.0/Include/methodobject.h) mantém dois parâmetros C para esse tipo de callback; sem argumentos Python não significa um protótipo C sem parâmetros. A passagem por RCX/RDX e retorno por RAX é compatível com a [ABI Windows x64](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170). O corpo observado do callback não utiliza os argumentos de entrada para selecionar time, jogador ou alvo.

Na cobertura pesquisada, há uma referência LEA ao endereço do callback, no registro acima; nenhum CALL relativo direto a ele foi encontrado. A invocação pelo dispatcher é indireta. Isso explica por que procurar somente CALLs diretos não reconstrói essa ligação.

**`GetAllActors`: comportamento e tipos até onde há evidência**

O corpo começa em `0x3259770`, termina no intervalo de unwind `0x3259887` e tem 87 instruções alcançáveis no CFG produzido. O fluxo observado é:

1. Solicita uma lista de tamanho zero pelo helper `0x2a83270`; verifica falha.
2. Obtém a raiz pelo getter `0x19d45e0`, que lê o slot global `0x8b7cd90`.
3. Percorre nós encadeados usando a sentinela encontrada em `[raiz+8]` e o próximo nó em `[nó+0]`.
4. Lê o valor do nó em `+0x18`. Lê outro ponteiro em `[valor+0x40]`; exige ponteiro não nulo e máscara `0x10` no byte `+0x130` desse objeto relacionado.
5. Converte o valor original do nó pela camada genérica de associação nativo/scripts, através de `0x2d829a0`/`0x2d82d90`.
6. Acrescenta o objeto convertido à lista pelo helper `0x2a83570`, com operações de referência e caminhos de falha/limpeza.
7. Retorna a lista ou NULL nos caminhos observados, levando em conta o estado de erro.

A lista deixou de ser apenas uma suposição genérica de “objeto de retorno”: o helper de criação usa o tipo no RVA `0x7a193e0`, cujo nome é `list`, e inicializa tamanho/armazenamento. Seus caminhos de erro e os do append referenciam `PythonCore3\Python-3.14.0\Objects\listobject.c`. As operações correspondem às de criação e append do [código público de listas do CPython](https://raw.githubusercontent.com/python/cpython/v3.14.0/Objects/listobject.c). A associação entre registros de método e o dispatcher também concorda com o [código público de métodos nativos](https://raw.githubusercontent.com/python/cpython/v3.14.0/Objects/methodobject.c).

**Ligação nova com `ActorComponent`**

Há um caminho concreto que constrói `Character::Actor` e o associa ao componente:

- A inicialização de `ActorComponent` chama `0x19bfe20` em `0x19bf936`.
- Esse helper chama o inicializador de `Character::Actor`, `0x16d0e70`, em `0x19bfe53`, e encaminha a referência junto ao ponteiro do componente para `0x19c0100`, em `0x19bfe75`.
- Nessa rotina, `0x19c01dc` identifica o armazenamento `+0x378` do componente e `0x19c0266` grava a referência nativa nesse armazenamento. Esse acesso relacional é comprovado; não é posição, jogador local ou bone.
- Antes da inserção no registro, `0x19c03f0` guarda o ponteiro do componente; `0x19c03f7` obtém um valor de 32 bits de `Character::Actor`; `0x19c0409` carrega a mesma raiz global e `0x19c0410` chama `0x254390` com chave e valor.
- O helper de inserção lê quatro bytes da chave, consulta buckets e escreve a chave em `[nó+0x10]` (`0x254497`) e o valor recebido em `[nó+0x18]` (`0x25449e`). Esse último campo é o lido pelo callback.

Isso demonstra pelo menos um caminho de inserção de **ponteiros de `ActorComponent`**, associados a um valor de 32 bits do ator nativo. Não demonstra que essa chave seja um identificador de jogador da rede, nem que todas as outras inserções e subclasses tenham sido auditadas. A caracterização completa dos tipos dinâmicos retornados fica **PARCIAL**.

A raiz é alocada com solicitação de `0x40` bytes em `0x19b9360`. O inicializador `0x1a52d0` cria uma sentinela que aponta para si e configura armazenamento de buckets. O código é compatível com um container hash com nós encadeados. O nome fonte exato `std::unordered_map<uint32_t, ActorComponent*>`, inclusive o sinal da chave, continua **HIPÓTESE**.

O significado do bit `0x10` não foi identificado. Não foi rotulado como “inimigo”, “ativo”, “visível” ou “jogador”. Também não foi publicado um layout completo do objeto relacionado em `+0x40`.

**Hierarquias C++ e vptrs**

As quatro classes foram verificadas por três caminhos: hierarquia RTTI, inicialização da base seguida pela derivada e instalação das vftables. Nos componentes, thunks de ajuste oferecem confirmação adicional. A interpretação dos metadados está alinhada à [implementação pública da ABI Microsoft no LLVM](https://raw.githubusercontent.com/llvm/llvm-project/main/clang/lib/CodeGen/MicrosoftCXXABI.cpp), enquanto os valores concretos foram lidos desta amostra.

| Classe | Relação sustentada | Inicialização e instalação observadas |
| --- | --- | --- |
| `Character::Actor` | Deriva de `AnimationCore::Skeleton`, que deriva de `Messiah::IRefObject` | Chama a base em `0x16d0e9a`; a base instala sua tabela em `0x115eb3a`; a derivada instala `0x5565060` em `0x16d0ea6` |
| `Messiah::ActorComponent` | Deriva de `SkeletonComponent` | Chama a base em `0x19bf534`; instala vptrs `+0` e `+0x68` em `0x19bf540`/`0x19bf54a` |
| `Messiah::SkeletonComponent` | Deriva de `ISkeletonComponent`; esta tem bases `IComponent` e `ITickable` | Chama a base em `0xad5c24`; instala vptrs em `0xad5c30`/`0xad5c3a`; a base já instala seus pares em `0xa03077`/`0xa03081` |
| `Messiah::ICamera` | Deriva de `IEntity`, com ancestrais `IObject` e o ramo de componentes de objeto | Chama a base em `0x275738`; base instala sua tabela em `0x88ca47`; a derivada substitui o vptr em `0x275744` |

Os COLs secundários dos dois componentes registram deslocamento 104 decimal (`0x68`), coerente com o deslocamento de `ITickable`. As chamadas pelos subobjetos ajustam `this`:

| Thunk RVA | Bytes | Efeito |
| --- | --- | --- |
| `0x1a1e2fc` | `48 83 e9 68 e9 5b 02 00 00` | Subtrai `0x68` de RCX e salta para `0x1a1e560` |
| `0xb1070c` | `48 83 e9 68 e9 eb 12 00 00` | Subtrai `0x68` de RCX e salta para `0xb11a00` |

`+0x68` não foi generalizado para `Character::Actor` ou `ICamera`. A enumeração RTTI não demonstra por si só tamanhos completos, visibilidade pública/privada de todas as bases, nomes de métodos virtuais nem a configuração de toda instância em execução.

**Divergências e correções metodológicas**

**1. Mistura de notação no relatório anterior.** O comentário do bloco asm dizia que os endereços eram RVAs, mas a coluna esquerda era RVA e operandos absolutos de CALL eram VAs preferenciais. Exemplo: o destino exibido como `0x14424c168` corresponde ao RVA `0x424c168`. Os bytes e o alvo estavam corretos; a descrição da notação era ambígua. Nesta rodada, JSONs guardam explicitamente RVA, VA preferencial e offset de arquivo.

**2. Unwind não delimita necessariamente uma função fonte inteira.** Em `0x2a8327c`, o ramo válido salta para `0x2a83297`, fora do primeiro registro usado para desassemblagem. O percurso completo desse helper alcança quatro registros de unwind. O helper de associação `0x2d82d90` alcança três. Portanto, `truncated=false` no dump de uma unidade anterior não deve ser interpretado como cobertura de todos os ramos da função fonte. `reachable-code.json` registra agora instruções alcançáveis, arestas e alvos não seguidos. A [documentação de unwind x64](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170) descreve esses registros como informação de recuperação de execução, não como substituto de símbolos fonte.

**3. Sucesso prematuro no verificador.** O script antigo gravava `verification.json` com `PASS` antes da restrição de hash e dos nove blocos curados. Uma falha posterior podia deixar sucesso obsoleto em disco. O script `verify_evidence.py` foi corrigido: publica `PASS` após todas as verificações, ou grava `FAIL` ao capturar um erro. Isso não invalida o resultado antigo desta amostra, cujos bytes foram novamente conferidos; corrige o comportamento em falhas futuras.

**4. Endereço externo não validado.** O getter desta build lê `0x8b7cd90`, não `0x8a8e810`. A busca coberta não encontrou referências a este último, mas ausência nessa busca limitada não prova que ele nunca seja usado por outro código. Não há uma segunda build para atribuir-lhe origem. Sua identificação como a raiz lida por este getter está descartada.

**Arquitetura Messiah: binário versus referências públicas**

| Camada | Evidência nesta build | Limite |
| --- | --- | --- |
| Animação nativa | `AnimationCore::Skeleton` → `Character::Actor`, construtores e RTTI | Não equivale a uma entidade de jogador |
| Componentes Messiah | `ActorComponent` → `SkeletonComponent` → `ISkeletonComponent`; referência ao ator nativo e registro | Ownership total, subclasses e ciclo de vida completo ainda não reconstruídos |
| Objetos/entidades | `ICamera` → `IEntity`; ramo `TObjectComponent<IEntity>`/`ObjectComponentBase` no RTTI | Não fornece matriz de câmera validada nem coordenadas do campo |
| Scripts nativos | Inicialização de `MCharacter`, `PyMethodDef`, dispatcher NOARGS e lista Python | Nome fonte de cada helper anônimo não é garantido |
| Bridge Asyncore | Tipos `Asyncore::pybase_object_impl<...>`, `Messiah::PythonAsyncoreModule` e conversor genérico com associação de wrappers | Não demonstra scheduling, política de threads, rede ou integração completa do GIL |
| Procedência CPython | Caminhos `Python-3.14.0` em instruções dos helpers e operações compatíveis com a API C | Não prova identidade byte a byte com a tag pública ou ausência de customizações |

O conversor genérico consulta associação existente, metadados e uma fábrica indireta antes de recuperar/associar o objeto de scripts. O contexto global `0x8e455b8` é compartilhado por muitos caminhos; não foi identificado como um tipo Python exclusivo de ator.

A referência pública usada é documentação de formatos/ABI e código oficial do CPython/LLVM. Ela sustenta a interpretação dos padrões, **não valida RVAs desta build**. Não foram incorporadas tabelas de offsets de terceiros como prova. Os números de linha gravados nas chamadas de erro dos helpers não coincidem exatamente com os da tag pública CPython `v3.14.0`; por isso “fonte identificada como Python-3.14.0” foi separado de “runtime idêntico à release oficial”.

**Classificação das descobertas**

`CONFIRMADA`: demonstrada no escopo explicitado por bytes/fluxo/metadados conferidos. `PARCIAL`: parte da caracterização é demonstrada, com extensão ainda aberta. `HIPÓTESE`: interpretação plausível ou possível, sem prova suficiente. `DESCARTADA`: afirmação contradita ou inferência metodológica que não se sustenta. Descartar uma inferência de “lista de jogadores” não prova que jogadores nunca possam ter componentes nesse registro.

| ID | Classificação | Descoberta / interpretação |
| --- | --- | --- |
| A01 | CONFIRMADA | Consistência estrutural dos RVAs, bytes, xrefs e slots conferidos |
| A02 | PARCIAL | Reconstrução de tipos e layouts via RTTI |
| A03 | DESCARTADA | Um registro de unwind garante função fonte completa |
| A04 | DESCARTADA | Todos os endereços do asm anterior estavam apresentados como RVA |
| A05 | PARCIAL | Recuperação de vftables, quantidade e identidade exatas dos métodos |
| G01 | CONFIRMADA | Nome `GetAllActors` associado ao callback `0x3259770` |
| G02 | CONFIRMADA | Registro na inicialização de `MCharacter` |
| G03 | CONFIRMADA | Dispatcher NOARGS fornece self e NULL |
| G04 | CONFIRMADA | Construção de lista Python e retorno lista/NULL nos caminhos observados |
| G05 | CONFIRMADA | Código de alocação/inicialização da raiz em `0x8b7cd90` |
| G06 | CONFIRMADA | Caminho de inserção relaciona valor de 32 bits do ator a `ActorComponent` |
| G07 | PARCIAL | Caracterização de todos os elementos dinâmicos retornados |
| G08 | HIPÓTESE | Enumeração exclusiva de jogadores ou inimigos |
| G09 | HIPÓTESE | Identidade fonte exata do container e sinal do tipo de chave |
| G10 | CONFIRMADA | Leituras e teste da máscara `0x10`, sem semântica de gameplay |
| C01 | CONFIRMADA | Herança/inicialização de `Character::Actor` |
| C02 | CONFIRMADA | Vptrs `+0`/`+0x68` e `ITickable` nos dois componentes |
| C03 | CONFIRMADA | Herança de `ICamera` e vptr principal |
| C04 | DESCARTADA | Generalização de `+0x68` para as quatro classes |
| C05 | HIPÓTESE | `ICamera +0x454` necessariamente representa FOV |
| M01 | CONFIRMADA | Caminhos de procedência Python-3.14.0 nos helpers utilizados |
| M02 | PARCIAL | Identificação da base CPython versus versão/customizações exatas |
| M03 | CONFIRMADA | Presença dos tipos C++ Asyncore e PythonAsyncoreModule |
| M04 | HIPÓTESE | Dedução de toda a arquitetura de threads/GIL/rede a partir dos wrappers |
| D01 | DESCARTADA | O getter analisado lê `0x8a8e810` |
| D02 | DESCARTADA | Endereço da string é endereço da função |

Total: **13 CONFIRMADAS, 4 PARCIAIS, 4 HIPÓTESES e 5 DESCARTADAS**. Evidências por ID, bytes, RVA, VA preferencial e offset estão em `audit-v2/claims.json`. O relatório anterior já tinha ressalvas sobre várias hipóteses; as linhas descartadas explicitam interpretações rejeitadas, sem atribuir todas elas como afirmações prévias daquele relatório.

**Controles e reprodução**

Quatro controles passaram em `test_audit_controls.py`: fixture válida com os nove blocos curados; bytes declarados adulterados; detecção dessa adulteração pelo decoder independente; rejeição tardia de hash incompatível sem deixar `PASS` obsoleto. As falhas esperadas gravaram `FAIL`. Os controles usam artefatos temporários dentro da pasta do projeto; não alteram o executável do jogo.

A rodada final da auditoria estrutural levou **13,147 s** de parede. Esse tempo inclui o parser, o segundo decoder e os artefatos estruturais; não inclui toda a investigação manual, a curadoria executada depois ou os testes separados. Não foram medidos desempenho em partida, FPS ou custo de execução do jogo.

```powershell
# PowerShell | auditoria estática reproduzível | Windows x64
& 'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\run-audit-v2.ps1'
& 'C:\Users\luiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\test_audit_controls.py'
```

Arquivos criados: `audit_v2.py`, `curate_audit_v2.py`, `run-audit-v2.ps1`, `test_audit_controls.py`, `audit-requirements.txt`, dependência local `audit-vendor/` e este relatório. Arquivo corrigido: `verify_evidence.py`. Os arquivos anteriores de resultados foram preservados.

Os resultados desta rodada estão em `audit-v2/`: `summary.json`, `legacy-audit.json`, `address-map.json`, `hierarchies.json`, `base-initialization.json`, `references.json`, `functions.json`, `disassembly.txt`, `reachable-code.json`, `script-bridge.json`, `claims.json` e `verification-controls.json`. `audit-requirements.txt` fixa iced-x86; sua licença MIT acompanha o pacote local. Os scripts abortam a curadoria se o SHA-256 mudar.

**Questões abertas e limite da conclusão**

Continuam sem evidência suficiente: exclusividade dos tipos inseridos; todos os caminhos de remoção/inserção; significado do bit de filtro; identidade de jogador/time; ownership completo; layouts de posição, câmera e bones; inicialização completa dos delegados de reflexão; versão exata/customizações do runtime e execução efetiva de cada caminho numa partida.

A etapa estática seguinte é conferir os demais caminhos de inserção e as fábricas de wrappers, mantendo os nomes e tipos dinâmicos separados de identidades de gameplay. A presente auditoria confirma o encadeamento técnico descrito e seus acessos observados, sem transformar essas lacunas em offsets presumidos.
