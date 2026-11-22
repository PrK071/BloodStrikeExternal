# Revisão estática — `DriverEntry` e gerenciamento de memória do `km_rw.sys`

Fase 3 da investigação. **Somente leitura**: nenhum código foi alterado, nada foi
compilado, nada foi carregado, nenhum mapper/BYOVD foi usado. O backup
`C:\Users\luiz\km_cheat_backup\20261122_172616\` e os hashes anteriores foram
preservados.

## 0. Artefatos e evidências

| Arquivo | SHA-256 | Observação |
|---|---|---|
| `km_rw.sys` | `83F53EA9B6F2B00F1D210D507022BFD35D6EDF9FF6481A95FD16E1DCDF438A5B` | PE `TimeDateStamp = 0x6B01CF3F` → **21/11/2026 14:05:03** |
| `km_rw.c` | `651FC5106E1B7D3FB351CADAE4321C0343A6E224D93281C3BA0911DC727460A2` | 220 linhas |
| `km_rw.obj` | `4E2402FA9686164263186CD523A390DDF59396DF9FC0EA8190493CD3B49CDFB6` | |
| `build.bat` | `E66BA20AF321841126F0D587EA51CBF17F3F60E7EDB928F50FA5C01A46C86430` | |

> **Fato importante para a interpretação de tudo abaixo:** o `.sys` analisado foi
> linkado às **14:05:03**, e o **último** BSOD registrado foi no boot de
> **14:02:03**. O binário em mãos é, portanto, **posterior aos 5 crashes e nunca foi
> executado**. Ele corresponde ao código-fonte atual (que já contém o "fix" do
> PID 4, comentado nas linhas 183-186). Os crashes vieram de builds anteriores;
> a análise vale como *prova por construção* do mecanismo, não como laudo do
> binário que crashou.

Fontes externas consultadas (leitura): `ntoskrnl.exe` export table (build 19045),
kdmapper (`include/intel_driver.hpp`, `kdmapper.cpp`, `portable_executable.cpp`),
KDU (`Hamakaze/shellcode.cpp`, `Hamakaze/sup.cpp`), Event Log `System`.

---

## 1. Resumo executivo

**Pergunta central: `RtlZeroMemory(view, KM_SHARED_SIZE)` pode ultrapassar a região
mapeada?**

- **Em tamanho: não.** A seção é criada com exatamente `0x400000` bytes, a view é o
  mapeamento da seção inteira (offset 0, `ViewSize` de entrada `0x400000`), então
  `[view, view+0x400000)` está dentro da região. Não há overflow de limites.
- **Em espaço de endereçamento: sim, e é isso que derruba a máquina.** `view` é um
  endereço **user-mode** que só existe no espaço de endereçamento do **processo
  System (PID 4)**. `DriverEntry` não roda nesse processo quando o loader é o
  kdmapper: o kdmapper substitui `ntoskrnl!NtAddAtom` por um `jmp` e chama o entry
  **na própria thread do processo do kdmapper** (`CallKernelFunction` →
  `ntdll!NtAddAtom` → syscall). Nesse contexto (CR3 = kdmapper), a metade user do
  espaço de endereçamento é a do kdmapper, **não** a do PID 4 → o primeiro acesso a
  `view` é uma violação de acesso em Ring 0 → `0x1E` / `0xC0000005`.

Ou seja: o problema não é o `Size`, é o **contexto de execução do acesso**. A frase
"o tamanho mapeado é 4 MB" é verdadeira e irrelevante: o tamanho acessível *naquele
contexto* é **zero**.

Isso fecha a classe dos 5 BSODs de 21/11 (detalhe na §6): 3 falhas de **leitura**
(param0 = 0) na base da view e 2 de **escrita** (param0 = 1) na base da view. As duas
únicas instruções do driver que tocam exatamente a base da view são
`g_shared->Command` (leitura, thread de trabalho) e `RtlZeroMemory(view, …)`
(escrita, entry).

Achados independentes que também importam:

- **Bug confirmado (crítico):** o driver **não limita `Size`** (linhas 133/136). O
  cliente Python aceita até **16 MB** (`MAX_READ`) e o buffer de dados tem
  **0x3FFC00** bytes → até **12.583.936 bytes** além da view. Isso é um overflow
  real, diferente do `RtlZeroMemory`.
- **Bug confirmado (médio):** corrida de protocolo entre `Status` e `Command`
  (linhas 150-152 × cliente 136-137) → comando perdido / timeout.
- **Vazamento:** se `PsCreateSystemThread` falhar (linha 213), a view de 4 MB fica
  mapeada no PID 4 para sempre.
- **Falsos positivos a descartar:** ausência de `.reloc`; `PsProcessType` como
  import de dado; "falta de checagem de `view != NULL`".

---

## 2. A view — origem, tamanho e validade

### 2.1 Cadeia de chamadas

| Passo | Linha | O que acontece |
|---|---|---|
| 1 | 174-175 | `size.QuadPart = KM_SHARED_SIZE` (`0x400000`) |
| 2 | 178-179 | `ZwCreateSection(&section, SECTION_ALL_ACCESS, &oa, &size, PAGE_READWRITE, SEC_COMMIT, NULL)` — seção **pagefile-backed**, 4 MB, sem arquivo |
| 3 | 187 | `view = NULL`, `viewSize = KM_SHARED_SIZE` |
| 4 | 192-198 | abre handle do **PID 4** (`PsLookupProcessByProcessId(4)` + `ObOpenObjectByPointer(..., 0x38, *PsProcessType, KernelMode, &systemHandle)`) |
| 5 | 200-201 | `ZwMapViewOfSection(section, systemHandle, &view, 0, 0x400000, NULL, &viewSize, ViewShare, 0, PAGE_READWRITE)` → **a API que produz `view`** |
| 6 | 202-204 | fecha `systemHandle` e `section` |
| 7 | 208 | `RtlZeroMemory(view, KM_SHARED_SIZE)` |

`view` é, portanto, um **out-parameter do memory manager**, não um buffer alocado
pelo driver. O driver não controla o endereço; o MM escolhe um VA livre **no
processo alvo** (PID 4) e escreve em `view`.

### 2.2 Tamanho solicitado × tamanho acessível

- `MaximumSize` da seção = `0x400000` (linha 175). É o tamanho da seção, e
  `SEC_COMMIT` compromete essa quantia.
- `SectionOffset` = `0`; `ViewSize` de entrada = `0x400000` = seção inteira.
  Como o offset é 0 e o tamanho pedido é igual ao tamanho total, o MM mapeia a
  seção completa e devolve `viewSize = 0x400000`.
- `CommitSize` = `0x400000` ≤ `MaximumSize`: válido.
- **A API pode devolver `viewSize` menor que o pedido** em outros cenários (view
  parcial, offset ≠ 0). Aqui não pode, porque o pedido é "tudo, do começo". Mas o
  código **não relê `viewSize`** depois da chamada (linha 208 usa a constante).
  Classificação: **falso positivo como overflow**, porém é uma prática frágil —
  se alguém mudar `SectionOffset`/`CommitSize` no futuro, o zeroing passa a
  depender de uma suposição não verificada.

### 2.3 Alinhamento e limites da API

| Requisito de `ZwMapViewOfSection` | Valor no driver | OK? |
|---|---|---|
| `SectionOffset` múltiplo de 64 KB | `0` | sim |
| `ViewSize` múltiplo de `PAGE_SIZE` | `0x400000` | sim |
| `CommitSize` ≤ tamanho da seção | `0x400000` ≤ `0x400000` | sim |
| `MaximumSize` da seção múltiplo de `PAGE_SIZE` | `0x400000` | sim |
| `AllocationType` válido para seção não-imagem | `ViewShare` (=1) | sim (permitido; `ViewUnmap` também seria) |

Nenhum problema de alinhamento.

> Nota lateral (não é bug): o cliente Python chama a constante de `VIEW_SHARE = 2`
> (`ExternalCore/km_memory.py:37`), mas `2` é **`ViewUnmap`**. O valor funciona; o
> nome está errado. Vale corrigir o comentário/nome quando o arquivo for tocado.

### 2.4 O que realmente quebra

`MmMapViewOfSection` insere a view no **espaço de endereçamento do processo alvo**.
Endereços abaixo de `0x7FFFFFFFFFFF` são **por processo**. Um endereço em
`0x1_xxxx_xxxxx` (como os vistos nos crashes) pertence à metade user do PID 4 e
**não existe** quando o CR3 ativo é outro.

`RtlZeroMemory` (linha 208) é executado no contexto do loader. Logo:

```
contexto do DriverEntry (kdmapper)  →  CR3 = processo do kdmapper
view                                →  VA no espaço do PID 4
resultado                           →  #PF em endereço user não mapeado,
                                       em Ring 0, sem __try/__except
                                    →  0x1E KMODE_EXCEPTION_NOT_HANDLED
```

O driver tem `.pdata` válido, então o unwinder funciona — o que falta não é
tratamento de exceção de *hardware*, é o **contexto certo** ou um endereço que
exista em qualquer contexto (VA de sistema).

---

## 3. Auditoria do `DriverEntry` e do runtime

### 3.1 Ordem de inicialização

`seção → handle do PID 4 → view → zeroing → globais → thread`. A ordem é
logicamente correta **desde que** o zeroing aconteça no espaço do PID 4. As globais
`g_shared`/`g_data` (48-49) só são publicadas (209-210) depois do zeroing — bom
(evita a thread ver ponteiro meio-inicializado).

Nada é publicado antes de estar pronto, exceto o próprio `g_shared` — que é
publicado **antes** de a thread existir, mas isso é inofensivo porque só a thread o
consome.

### 3.2 Tratamento de falhas e caminhos de retorno

| Falha | Comportamento | Veredito |
|---|---|---|
| `ZwCreateSection` (180) | `return st` | ok |
| `PsLookupProcessByProcessId` (192) | `st != SUCCESS` → pula o `if` (199), fecha `section`, `return st` | ok (`systemHandle` continua `NULL`) |
| `ObOpenObjectByPointer` (194) | `st != SUCCESS` → pula o map, fecha `section`, `return st` | ok |
| `ZwMapViewOfSection` (200) | fecha `systemHandle`, fecha `section`, `return st` | ok |
| `PsCreateSystemThread` (213) | `return st` **sem desmapear a view** | **vazamento de 4 MB no PID 4** |
| `view == NULL` com `NT_SUCCESS` | não checado | inofensivo na prática (o MM não devolve sucesso com out-param nulo), mas frágil |

Observação: `ObOpenObjectByPointer` usa `*PsProcessType` (196). O padrão canônico
do WDK é exatamente esse, e o símbolo é export de **dado** confirmado nesta build
(ver §5, A9). Não é bug.

### 3.3 Uso após liberação / ponteiros pendurados

Não há `free` da view em nenhum caminho (o driver não tem `DriverUnload`). O risco é
o inverso: **a view pode ser destruída por fora** (o processo alvo termina, ou o
loader desfaz o mapeamento). Se isso acontecer, `g_shared`/`g_data` ficam
pendurados e a thread de trabalho acessa VA liberado → leitura/escrita em endereço
inválido. Esse é **exatamente** o modo de falha da v1 (view no processo do mapper,
que sai logo depois).

### 3.4 Concorrência

O protocolo é: cliente escreve `Pid/Address/Size` → `Status = BUSY` → `Command = n`.
Kernel: lê `Command`, processa, escreve `ErrorCode`, `Status`, depois `Command = 0`
(150-152).

Problemas:

1. **Comando perdido:** entre o `Status = DONE` e o `Command = 0` o cliente pode
   publicar um novo comando. O kernel então apaga o novo `Command` e deixa
   `Status = BUSY` do cliente → o cliente espera 5 s e estoura timeout
   (`km_memory.py:140`). **Não corrompe memória**, mas é um bug real.
2. **Sem barreiras de memória:** `Command`/`Status` são `volatile LONG`, mas
   `Pid/Address/Size` não. Em x64 (TSO) a ordem de *loads* é preservada e o loop
   chama `KeDelayExecutionThread` a cada iteração, o que força recarga; na prática
   funciona. Formalmente, o modelo não garante nada — só `volatile`/`Interlocked`
   garantiriam.
3. **Sem validação de consistência:** o kernel não confere que `Address+Size` está
   na metade user do processo alvo (deixa o `MmCopyVirtualMemory` decidir) nem que
   `Size` cabe no buffer (§4, #5).

### 3.5 Estrutura compartilhada

`KM_SHARED` (39-46): `Command 0x00`, `Status 0x04`, `ErrorCode 0x08`, padding,
`Pid 0x10`, `Address 0x18`, `Size 0x20` → **0x28 bytes**. O cliente
(`km_memory.py:56-62`) tem layout idêntico (ctypes alinha `c_uint64` em 0x10).
Sem divergência de ABI. `g_data = view + 0x400` (210) e o cabeçalho cabe folgado.

---

## 4. Rastreamento de memória

| # | Operação (linha) | Origem do endereço | Tamanho | Validação | Risco |
|---|---|---|---|---|---|
| 1 | `ZwCreateSection` (178) — `MaximumSize` | constante `KM_SHARED_SIZE` | 4 MB | nenhuma (constante) | nenhum |
| 2 | `ZwMapViewOfSection` (200) — `view`/`viewSize` | memory manager, **no PID 4** | 4 MB in/out | nenhuma pós-chamada | `viewSize` não reconferido |
| 3 | `RtlZeroMemory(view, KM_SHARED_SIZE)` (208) | out-param do MM (user VA do PID 4) | 4 MB | **nenhuma** | **AV em contexto ≠ PID 4 — confirmado**; limites ok |
| 4 | `g_shared->Command` (123) leitura | `view + 0x00` | 4 B | nenhuma | **AV se a view não estiver no espaço ativo — confirmado (v1)** |
| 5 | `KmRead` → `g_data` como destino (133) | `view + 0x400` | **`g_shared->Size` (controlado pelo cliente, ULONG64)** | **nenhuma** | **escrita além da view** (até 12 MB com o cliente atual) |
| 6 | `KmWrite` → `g_data` como origem (136) | `view + 0x400` | idem | **nenhuma** | **leitura além da view** (vazamento de memória adjacente do PID 4) |
| 7 | `KmImagePath` → `out = g_data` (139) | `view + 0x400` | ≤ `0x3FFBFE + 2` (clamp em 93-95) | clamp por `outChars` | ok, encosta no fim da view |
| 8 | `ExAllocatePoolWithTag` (97) | comprimento vindo do PEB do alvo | ≤ 64 KB + 2 | clamp `chars` | ok |
| 9 | `MmCopyVirtualMemory` (57-59, 66-68, 80-89, 102) — VA do alvo | **`g_shared->Address` / PEB do alvo** | `g_shared->Size` | `PreviousMode = UserMode` (probe interno da API) | devolve erro para VA inválido (provável `STATUS_PARTIAL_COPY`), mas **não valida contra o buffer** |
| 10 | `RtlCopyMemory(out, tmp, chars*2)` (105) | pool → view | ≤ `0x3FFBFE` | clamp | ok |
| 11 | `PsCreateSystemThread` (213) | n/a | n/a | status | vazamento de 4 MB se falhar |

Regra que resume a tabela: **o único limite que existe é o da #7/#10 (clamp
explícito)**. Os limites das #3-#6 dependem de suposições (contexto de execução e
tamanho do cliente).

---

## 5. Achados classificados

### Bugs confirmados

**B1 — `RtlZeroMemory` sobre VA de outro processo (crítico).**
`km_rw.c:208` (`DriverEntry`). `view` pertence ao espaço user do PID 4; o entry roda
no espaço do loader. Violação de acesso determinística sob kdmapper.
*Impacto:* `0x1E`/`0xC0000005` de escrita na base da view. *Evidência:* §6.

**B2 — `Size` sem limite (crítico, pós-carga).**
`km_rw.c:133` e `km_rw.c:136` (`KmWorker`/`KmRead`/`KmWrite`). `g_shared->Size` vai
direto para `MmCopyVirtualMemory` com destino/origem em `view + 0x400`, capacidade
`0x3FFC00`. O cliente permite `MAX_READ = 16 MB`
(`ExternalCore/memory.py:8`), ou seja **12.583.936 bytes além da view**.
*Impacto:* escrita/leitura OOB no espaço user do PID 4 → corrupção de mapeamentos
vizinhos, vazamento de memória (leitura), ou AV conforme o layout.
*Não* é a causa dos crashes de *load*, porque depende de um comando já em execução.

**B3 — Corrida `Status`/`Command` (médio).**
`km_rw.c:150-152` × `ExternalCore/km_memory.py:136-137`. Comando perdido e
`Status` preso em `BUSY` → timeout de 5 s. Sem corrupção.

**B4 — Vazamento da view no erro de thread (baixo).**
`km_rw.c:213-216`: retorna erro sem `ZwUnmapViewOfSection`; 4 MB ficam mapeados no
PID 4 e o driver fica "carregado" sem worker.

### Riscos plausíveis

**B5 — Arquitetura: VAs de user space em globais (alto).**
`km_rw.c:48-49, 209-210`. Todo acesso a `g_shared`/`g_data` só é válido em thread
cujo espaço de endereçamento seja o do PID 4. Hoje só a thread de trabalho
(`PsCreateSystemThread` → System) cumpre isso; o entry não. Qualquer uso futuro
(DPC, timer, unload, callback) reintroduz o B1. Além disso, se a view for desfeita
por fora, os globais viram ponteiros pendurados (use-after-unmap).

**B6 — Ausência de barreiras de memória (baixo).**
`km_rw.c:40-45, 122-152`. Funciona em x64/TSO; não é garantido pelo modelo.

**B7 — DACL da seção (funcional, não é BSOD).**
`km_rw.c:178-179`: seção criada por SYSTEM sem `SecurityDescriptor` explícito. Um
cliente **não elevado** pode receber `ACCESS_DENIED` em `NtOpenSection`
(`km_memory.py:106`). Não testado.

### Falsos positivos

**A8 — "Sem `.reloc`, logo a imagem está quebrada".**
Não. `FileHeader.Characteristics = 0x0022` (**`RELOCS_STRIPPED` não está setado**),
`DllCharacteristics = 0x1E0` (`HIGH_ENTROPY_VA|DYNAMIC_BASE|FORCE_INTEGRITY|NX_COMPAT`),
`BaseRelocationDirectory = RVA 0 / size 0` e **0 blocos de reloc**. O código é
RIP-relative, `.pdata` usa RVAs e a IAT é preenchida pelo loader — não há nenhuma
referência absoluta para corrigir, então o linker não emite a seção. O kdmapper
**tolera** isso explicitamente (`portable_executable.cpp:26-27`: `if (!reloc_va)
return {};`) e o KDU também (`shellcode.cpp`: só relocaliza `if (off && rsz)`).
Consequência real, e única: carga **convencional** em base diferente da preferida
falha limpa (não corrompe). Relação com os BSODs: **nenhuma**.

**A9 — `PsProcessType` como import de dado não resolvido.**
Todos os 15 imports existem no `ntoskrnl.exe` desta build (19045), verificado na
export table:
`RtlInitUnicodeString, KeDelayExecutionThread, ExAllocatePoolWithTag,
ExFreePoolWithTag, PsCreateSystemThread, IoGetCurrentProcess,
ObfDereferenceObject, ZwClose, ZwCreateSection, ZwMapViewOfSection,
PsLookupProcessByProcessId, ObOpenObjectByPointer, MmCopyVirtualMemory,
PsGetProcessPeb` (14 funções) + **`PsProcessType`, RVA `0xCFC410`, seção
`ALMOSTRO` (dados, não executável)**. O kdmapper resolve pelo export table
(`intel_driver.cpp:739-741`: `AddressOfNames`/`AddressOfFunctions`), que devolve o
endereço do símbolo para função **e** para dado; o KDU faz o mesmo via
`LdrGetProcedureAddress` (`Hamakaze/sup.cpp:1402-1456`). `*PsProcessType` é o uso
canônico. Não há evidência de falha de resolução — e a hipótese não é necessária
para explicar nenhum dos 5 crashes.

**A10 — "Falta checar `view != NULL`".**
O MM não devolve `STATUS_SUCCESS` com `view == NULL` em `ViewShare`/`ViewUnmap`.
Vale como robustez, não como causa.

**A11 — `IoGetCurrentProcess` "importado sem uso".**
É o macro por trás de `PsGetCurrentProcess()` (`km_rw.c:58, 66, 81, 88, 102`).
Não é import órfão.

### Informação insuficiente

**C12 —** se `ZwMapViewOfSection` em PID 4 **sucede** nesta build (nenhum teste
executado). Os crashes de escrita na base da view sugerem que sim, mas isso depende
de dump para ser provado.
**C13 —** o `0x1A` de 19/11 (`0x3F`) é de **outro dia** e de outro estágio do
projeto (possivelmente o driver IOCTL ou um teste anterior). Sem dump, não é
atribuível.
**C14 —** DACL da seção para cliente não elevado (B7).

---

## 6. Ligação com os 5 BSODs de 21/11

### 6.1 Semântica dos parâmetros (correção da análise anterior)

Para `0x1E` (`KMODE_EXCEPTION_NOT_HANDLED`):

| Parâmetro | Significado |
|---|---|
| 1 | código da exceção |
| 2 | **endereço onde a exceção ocorreu (a instrução)** |
| 3 | `ExceptionInformation[0]` — para AV: **0 = leitura, 1 = escrita, 8 = execução** |
| 4 | `ExceptionInformation[1]` — **endereço virtual acessado** |

A versão anterior deste diagnóstico tratou o parâmetro 2 como "endereço acessado".
**Está errado**: o endereço acessado é o **parâmetro 4**. A conclusão anterior
("não dá para saber se é user ou kernel") muda de forma decisiva com essa correção:

### 6.2 Os cinco eventos

| Hora | Param 2 (instrução) | Param 3 | Param 4 (endereço acessado) | Natureza | 64 KB alinhado? |
|---|---|---|---|---|---|
| 13:41:00 | `0xFFFFB10C27BDA1E0` | **0** | `0x000001F6F5FC0000` | **leitura** de VA user | **sim** |
| 13:52:04 | `0xFFFF9F8A30FD91E0` | **0** | `0x0000016DE55A0000` | **leitura** de VA user | **sim** |
| 13:53:51 | `0xFFFFC70CF8DD31E0` | **0** | `0x0000021E77730000` | **leitura** de VA user | **sim** |
| 13:56:47 | `0xFFFFD80FE3FE9950` | **1** | `0x0000017AF38E0000` | **escrita** de VA user | **sim** |
| 14:02:03 | `0xFFFF8E86F23DC950` | **1** | `0x000001CA71FA0000` | **escrita** de VA user | **sim** |

Os 5 endereços acessados são **todos user-mode**, na faixa **1,4–2,1 TB**, e todos
**múltiplos de 64 KB** — a granularidade com que o memory manager escolhe a base de
uma *view* de seção. Não parecem endereços de módulo do jogo (que variam por
`/DYNAMICBASE` mas também seriam 64 KB-alinhados), e o jogo provavelmente nem estava
em execução durante o load. A leitura mais simples e consistente: **a base da view
mapeada da seção `KmRwShared`, diferente a cada boot/tentativa.**

### 6.3 Crash → versão do driver

O driver só toca **exatamente a base da view** (`view + 0`) em dois lugares:

- `g_shared->Command` — **leitura** (`km_rw.c:123`, thread de trabalho);
- `RtlZeroMemory(view, …)` — **escrita** (`km_rw.c:208`, entry).

Isso casa com a divisão 3 leituras / 2 escritas:

- **3 leituras (13:41, 13:52, 13:53) = v1** (`ZwCurrentProcess`). A view caía no
  espaço do **processo do kdmapper**; o `DriverEntry` (que roda nesse processo)
  conseguia zerar; o kdmapper saía; a view era destruída; a **thread de sistema** lia
  `g_shared->Command` num VA que não existe no espaço do System → leitura de VA user
  não mapeado. É exatamente o modo de falha que o `KERNEL-POSTMORTEM.md` descreve
  como "BSOD garantido".
- **2 escritas (13:56, 14:02) = v2** (mapeamento no PID 4 — o comentário nas linhas
  183-186). Agora a view está no espaço do PID 4, mas o **zeroing continua rodando no
  espaço do kdmapper** → escrita em VA user não mapeado, na base da view.

> Grau de confiança: **alto** no mecanismo (provado por construção: kdmapper executa
> o entry na thread do chamador; as duas únicas referências a `view+0` produzem
> exatamente esses dois padrões de fault). **Médio** na atribuição crash→build: sem
> dump não há stack; o `KERNEL-POSTMORTEM.md` conta "4 após o fix", o log mostra 5
> no total — a contagem do post-mortem está imprecisa.

### 6.4 O `0x1A` (MEMORY_MANAGEMENT)

`19/11 13:06`, parâmetros `(0x3F, 0xEA1DB, 0x27F7AE28, 0x1AABD40A)`. É **dois dias
antes** dos 5 `0x1E` e de outro estágio do projeto. `MEMORY_MANAGEMENT` indica
corrupção de estruturas de memória (PTE/pool), compatível com escrita em VA
inválida, mas **sem dump não há como atribuir** nem descartar. Fica como
**informação insuficiente** — não usar como evidência de nada.

---

## 7. Por que a mesma linha funciona num loader e não no outro

Isso é relevante para qualquer teste futuro, e explica por que "o fix do PID 4" não
resolveu:

| Loader | Como o entry é invocado | Processo/CR3 ativo | `RtlZeroMemory(view)` |
|---|---|---|---|
| **kdmapper** | `CallKernelFunction` substitui `ntoskrnl!NtAddAtom` por `jmp` e chama `ntdll!NtAddAtom` (`include/intel_driver.hpp:89-126`; uso em `kdmapper.cpp:247`) | **processo do kdmapper** (thread do chamador, `PreviousMode = UserMode`) | **fault** |
| **KDU** | `PsCreateSystemThread(..., (PKSTART_ROUTINE)(exbuffer + AddressOfEntryPoint), NULL)` (`Hamakaze/shellcode.cpp:556-561`) | **System (PID 4)** | **não faulta** |

Ou seja: sob KDU o `DriverEntry` já roda no espaço do System, que é o mesmo espaço
em que a view foi mapeada — o B1 fica latente, não ativo. Sob kdmapper ele é
determinístico. Isso **não** valida o desenho: ele só funciona por coincidência de
o loader usar uma system thread, e volta a quebrar no primeiro acesso fora dela.

(Registrando, sem recomendar: o caminho KDU é BYOVD e está fora do escopo
autorizado nesta fase.)

---

## 8. O que ainda não está provado

1. Que o mapa no PID 4 **sucede** no 19045 (C12).
2. A instrução exata de cada crash (exige dump; os dumps foram apagados).
3. Se o fault de escrita é da linha 208 ou de uma escrita da thread de trabalho
   (a thread escreve `Status`/`Command` em +4/+0; mas ela lê +0 antes, então um
   fault de escrita em +0 só faz sentido no entry).
4. O `0x1A` de 19/11 (C13).
5. Comportamento do `MmCopyVirtualMemory` com `Size` absurdo (erro limpo ×
   bugcheck) — depende da implementação e precisa de VM.
6. DACL da seção para cliente não elevado (C14).

---

## 9. Próximas etapas seguras

Nada aqui foi aplicado. Cada item tem justificativa técnica; a ordem é de menor para
maior risco.

**Antes de qualquer VM (só análise, sem executar):**
1. Fechar a decisão sobre B2 (limite de `Size`): é o único bug que continua ativo
   *depois* de um load bem-sucedido, e o cliente atual já o alcança (16 MB > 4 MB).
2. Decidir o modelo de memória (B5). As opções reais são:
   - **(a)** não zerar e não guardar VA de user space: manter a view no PID 4 e
     garantir que **só** a thread de sistema a toque — remove a linha 208
     (o `SEC_COMMIT` já entrega páginas zeradas, então o zeroing é redundante);
   - **(b)** mapear a seção em **VA de sistema** (`MmMapViewInSystemSpace` /
     `MmGetSystemAddressForMdlSafe`), que existe em qualquer contexto — é a correção
     de raiz do B1/B5, e a única que não depende de qual thread toca o buffer.
   A opção (b) é a tecnicamente correta; a (a) é a mínima. Nenhuma foi aplicada.

**Na VM (quando autorizado, em ambiente descartável):**
3. Carga **convencional** (`sc start`) do mesmo `.sys` com test-signing **dentro da
   VM**: se não houver `0x1E`, confirma que o problema é o contexto do acesso, não o
   PE/imports/compilação.
4. Só depois: reproduzir o cenário de mapeamento e comparar o fault com a tabela §6.2.

---

## 10. Preservação

- Código e binário **não foram alterados**; nenhum rebuild.
- Backup `C:\Users\luiz\km_cheat_backup\20261122_172616\` intacto.
- Hashes no topo deste documento são os mesmos já registrados em
  `KM-RW-DIAGNOSTIC.md`.
