# Proposta de correções — `km_rw` (diff revisável, não aplicado)

Continuação de `KM-RW-DIAGNOSTIC.md` e `KM-RW-DRIVERENTRY-REVIEW.md`.
Esta é uma **proposta**. Nada foi aplicado, compilado, carregado ou instalado.

| | |
|---|---|
| Base do diff do driver | `km_rw.c` SHA-256 `651FC5106E1B7D3FB351CADAE4321C0343A6E224D93281C3BA0911DC727460A2` |
| Base do diff do cliente | `ExternalCore/km_memory.py` (commit `26160d5`) |
| Artefatos | `proposals/0001..0004-*.diff` (detalhes na §6) |
| Verificação feita | `git apply --check` (4/4), `ast.parse` (2/2), asserts de ABI executados, símbolos conferidos nos headers do WDK |

**Nada foi commitado.** Os arquivos em `proposals/` e este documento estão no
working tree, aguardando tua revisão.

---

## 0. Resumo das decisões

| Achado | Correção proposta | Patch |
|---|---|---|
| B2 — `Size` sem limite (overflow real de até 12 MB) | validação derivada da estrutura + chunking no cliente | 0001, 0002 |
| B3 — corrida `Status`/`Command` (comando perdido) | `InterlockedExchange` no latch + contador `Completion` monotônico | 0001, 0002 |
| B4 — vazamento da view se a thread falhar | tabela de propriedade por caminho, liberação única | 0001 |
| B1/B5 — VA user de outro processo em global | mapear em **VA de sistema** (`MmMapViewInSystemSpace`) | 0001 |
| PreviousMode incompatível com buffer de kernel (bug latente do `image_path`) | `UserMode` → `KernelMode` | 0001 |
| Arquitetura frágil (seção compartilhada, thread de polling) | device + IOCTL `METHOD_BUFFERED`, sem estado global | 0003, 0004 |

Dois entregáveis independentes:

- **0001 + 0002** — correção incremental do desenho atual (seção compartilhada).
  Aplicável hoje, muda pouco, resolve B1-B5.
- **0003 + 0004** — arquitetura convencional (device + IOCTL), arquivos novos.
  Não substitui nada; convive com o driver antigo até a decisão de migrar.

---

## 1. Limites dos buffers (B2)

### 1.1 De onde vêm os números (não são clamps arbitrários)

| Limite | Valor | Derivação |
|---|---|---|
| `KM_DATA_CAPACITY` | `0x3FFC00` | `MaximumSize` da seção (`0x400000`) − `KM_DATA_OFFSET` (`0x400`). É o intervalo `[view+0x400, view+0x400000)` — a única região que o comando pode usar. O cabeçalho (`sizeof(KM_SHARED) = 0x28`) cabe folgado nos primeiros `0x400`, então não há sobreposição. |
| `KM_MAX_PATH_CHARS` | `0x8000` | `UNICODE_STRING.Length` é `USHORT` = contagem de **bytes**; o máximo de caracteres é `0xFFFF/2 = 0x7FFF`. `0x8000` é o teto exclusivo. A alocação `(chars+1)*2` fica ≤ `0x10000` bytes, sem overflow. |
| `KM_MAX_USER_ADDRESS` | `0x7FFFFFFF0000` | `MmUserProbeAddress` no x64. Endereços a partir daí são kernel; `ProbeForWrite` rejeita `Address + Length > MmUserProbeAddress`. Usar exatamente esse valor como limite superior exclusivo alinha a validação do driver com a do probe. |
| `KM_MAX_XFER` (só no 0003) | `0x100000` | **Limite de política**, não estrutural: `METHOD_BUFFERED` faz o I/O manager alocar `max(in,out)` em pool não paginado por IRP. 1 MB mantém a alocação previsível; o cliente divide transferências maiores. Está documentado no código como escolha nossa. |

Intervalo válido resultante para um read/write:

```
size    ∈ [1, 0x3FFC00]
address ∈ (0, 0x7FFFFFFF0000)
address + size ≤ 0x7FFFFFFF0000
```

### 1.2 Overflow em cálculos

O teste ingênuo `address + size > MAX` estoura em 64 bits (`address = 0xFFFF...`,
`size = 0x3FFC00`). A forma usada não pode estourar, porque `address` já foi
limitado antes:

```c
if (address > KM_MAX_USER_ADDRESS)            /* kernel address */
    return STATUS_INVALID_PARAMETER;
if (size - 1 > KM_MAX_USER_ADDRESS - address) /* cannot overflow */
    return STATUS_INVALID_PARAMETER;
```

`size >= 1` é garantido na linha anterior, então `size - 1` não subtrai abaixo de
zero; `KM_MAX_USER_ADDRESS - address` não é negativo. Nenhuma soma é feita.

O outro cálculo sensível é `(chars + 1) * sizeof(WCHAR)` no `KmImagePath`: com
`chars ≤ 0x7FFF` o produto máximo é `0x10000`, muito abaixo de `ULONG_MAX`.

### 1.3 Consistência entre pedido e capacidade

| Situação | Antes | Proposta |
|---|---|---|
| `Size > 0x3FFC00` | passava direto para `MmCopyVirtualMemory`, escrevendo fora da view | `STATUS_INVALID_BUFFER_SIZE`, nada é copiado |
| `Size == 0` | `MmCopyVirtualMemory(..., 0, ...)` → sucesso com 0 bytes | `STATUS_INVALID_BUFFER_SIZE` (explícito; `image_path` não usa `Size`) |
| `Address` em kernel space | `MmCopyVirtualMemory` devolvia erro depois de attach | rejeitado antes de qualquer lookup |
| `Size` no IOCTL maior que o buffer de saída | — | `STATUS_BUFFER_TOO_SMALL` (0003) |
| `Size` de payload maior que o buffer de entrada | — | `STATUS_BUFFER_TOO_SMALL`, com subtração protegida pelo `inLen >= sizeof` anterior (0003) |

**Efeito colateral:** o cliente não pode mais fazer um read único de 16 MB. Por
isso o patch 0002 passou a dividir em blocos de `DATA_CAPACITY` de forma
transparente (`read`/`write` montam o resultado). A semântica de "leitura
atômica" já não existia acima de 4 MB — antes ela simplesmente derrubava a
máquina.

---

## 2. Gerenciamento de recursos (B4)

### 2.1 Tabela de propriedade por caminho

Recursos: **(S)** handle da seção, **(O)** referência ao objeto seção, **(V)** view
de sistema, **(T)** handle da thread, **(G)** globais `g_shared`/`g_data`.

| Caminho | S | O | V | T | G | Correto? |
|---|---|---|---|---|---|---|
| `ZwCreateSection` falha | — | — | — | — | — | sim (nada criado) |
| `ObReferenceObjectByHandle` falha | fecha | — | — | — | — | sim |
| `MmMapViewInSystemSpace` falha | fechada | deref | — | — | — | sim |
| view menor que `KM_SHARED_SIZE` | fechada | deref | **unmap** | — | — | sim (novo) |
| `PsCreateSystemThread` falha | fechada | deref | **unmap** | — | **limpas** | sim (novo; antes vazava 4 MB) |
| sucesso | fechada | deref | mantida | fecha | publicadas | sim (view vive enquanto o driver viver) |

Ordem no caminho de falha da thread: limpar as globais **antes** de desmapear,
para que nenhum caminho (nem uma thread futura) leia a view depois de liberada.

### 2.2 Dupla liberação

Não existe caminho que libere duas vezes:

- o `return` do view curto acontece antes da criação da thread;
- o caminho da thread só é alcançado se o view curto passou;
- `section` e `sectionObject` são liberados em blocos disjuntos
  (`sectionObject` só é referenciado dentro do `if (NT_SUCCESS(st))`).

O handle da thread só existe em caso de sucesso, e é fechado uma vez.

**Efeito colateral:** não há `DriverUnload` no 0001 (driver mapeado não tem
descarga). A view e a thread vivem até o reboot — intencional e documentado. O
0003 tem `DriverUnload` completo.

---

## 3. Concorrência (B3)

### 3.1 Inventário de acessos (versão atual)

| Campo | Quem escreve | Quem lê |
|---|---|---|
| `Command` | cliente (valor), kernel (`0`) | kernel |
| `Status` | **cliente (`BUSY`) e kernel (`DONE`/`ERROR`)** | cliente |
| `ErrorCode` | kernel | cliente |
| `Pid`/`Address`/`Size` | cliente | kernel |

O problema estrutural: **dois escritores no mesmo campo de estado** (`Status`),
sem operação atômica em nenhum dos lados, e o kernel limpa `Command` *depois* de
publicar o resultado.

### 3.2 As três falhas concretas

**(a) Comando perdido.** É a falha real do desenho atual:

```
t0  cliente : Status=BUSY; Command=cmd        (km_memory.py:136-137)
t1  kernel  : lê Command, processa
t2  kernel  : ErrorCode=..; Status=DONE        (km_rw.c:227-228)
t3  cliente : vê DONE, publica o PRÓXIMO comando (Status=BUSY, Command=cmd2)
t4  kernel  : Command=0                        (km_rw.c:229)  <-- apaga cmd2
t5  cliente : espera Status != BUSY por 5 s -> MemoryReadError(0x102)
```
Não corrompe memória, mas produz timeout e uma requisição que nunca executa.
Também explica timeouts intermitentes que não são falha do alvo.

**(b) Leitura/limpeza não atômica.** `if (Command != 0) { cmd = Command; ... }`
são duas leituras e uma escrita separadas. Se o cliente republicar entre elas, o
`cmd` executado e o `Command` apagado podem não ser o mesmo valor (lost update).

**(c) Estado parcialmente atualizado.** O lado do *resultado* está ordenado
corretamente (`ErrorCode` antes de `Status`, stores ordenados no x86), então isto
**não** era um bug ativo. Já o lado do *pedido* (três campos de 64 bits antes de
`Command`) não tinha barreira nem `volatile` — funcionava por sorte de TSO/x86.

**Comando duplicado:** não acontecia (o kernel limpa `Command`), mas a limpeza
não era atômica com a leitura, então "exatamente uma vez" não era garantido por
construção.

### 3.3 Protocolo proposto

Um único campo de estado pertence ao kernel e é **monotônico**:

```c
cliente : Pid/Address/Size; seq = Completion; Command = cmd
kernel  : cmd = InterlockedExchange(&Command, 0)   /* latch + clear atômico */
          ... processa ...
          ErrorCode = st
          InterlockedIncrement(&Completion)         /* publica o resultado */
cliente : espera Completion != seq; lê ErrorCode
```

Propriedades:

| Propriedade | Por quê |
|---|---|
| exatamente uma execução por comando | `InterlockedExchange` lê e zera em uma operação; um valor já consumido não pode ser consumido de novo |
| nenhum comando perdido | o kernel não escreve `Command`; um pedido publicado durante o processamento fica pendente e é pego na volta seguinte |
| sem estado "busy" compartilhado | o cliente não escreve estado; não há janela entre "publicar resultado" e "limpar latch" |
| ordem dos campos | `InterlockedExchange`/`InterlockedIncrement` são barreiras completas; os campos lidos/escritos em volta estão ordenados |
| falha segura no wrap | `Completion` é `LONG` e volta a zero após 2³² comandos (≈49 dias a 1 kHz); se `seq` coincidir, o cliente dá timeout em vez de aceitar dado velho |

Por que **não** spinlock/mutex: o estado é compartilhado com user mode, que não
pode adquirir um `KSPIN_LOCK` nem um mutex de kernel. `InterlockedXxx` sobre
memória compartilhada é o mecanismo correto para um handshake entre modos.
Um `KEVENT` também não serve: o cliente user-mode não pode esperar em um objeto
de kernel sem um handle, e isso exigiria um device — que é justamente o 0003.

**Efeito colateral:** o layout de `KM_SHARED` **não muda** (0x28 bytes,
`Completion` no offset de `Status`), mas a **semântica muda**. Driver e cliente
têm de ser atualizados juntos; versões cruzadas resultam em timeout, não em
corrupção (o cliente antigo escreveria `Status=BUSY` em `Completion`, que o
kernel sobrescreveria com o incremento — o cliente antigo veria `!= BUSY` e
prosseguiria; por isso a recomendação é trocar os dois no mesmo deploy).

---

## 4. Arquitetura de memória

### 4.1 Por que um VA de user space não pode ser estado global

Um VA abaixo de `0x7FFFFFFF0000` pertence a **um** processo: a tradução depende
do CR3 ativo. Guardar esse VA em uma global significa que o ponteiro só é válido
enquanto (a) o processo dono estiver ativo **e** (b) o acesso acontecer naquele
espaço de endereçamento.

O driver viola (b) na linha 208 original: `RtlZeroMemory(view, …)` roda no
contexto de quem chamou `DriverEntry`, que pode ser o processo do loader, não o
PID 4. É a causa dos `0x1E` documentada no `KM-RW-DRIVERENTRY-REVIEW.md` §6.

### 4.2 Correção mínima: VA de sistema

`MmMapViewInSystemSpace` mapeia a seção na metade de sistema, que é **compartilhada
por todos os espaços de endereçamento**. O VA passa a ser válido em qualquer
contexto, então:

- `RtlZeroMemory` no init é seguro;
- a thread de polling é segura;
- qualquer acesso futuro (DPC, unload, callback) também é — o que resolve B5, não
  só B1.

Custo: `MmMapViewInSystemSpace` exige o **objeto seção**, não o handle; daí
`ObReferenceObjectByHandle` + `ObDereferenceObject` depois do mapeamento (a view
mantém a própria referência). A view é pageable: só pode ser tocada em
`IRQL < DISPATCH_LEVEL` — verdadeiro no init e na thread (PASSIVE).

### 4.3 `PreviousMode`: por que tem de mudar para `KernelMode`

Isto **não** é cosmético e é o ponto mais delicado do patch.

`MmCopyVirtualMemory` recebe `PreviousMode` para decidir se **valida (probe) o
buffer do lado do chamador**:

- `PreviousMode == UserMode` → chama `ProbeForRead`/`ProbeForWrite` no buffer do
  processo atual;
- `ProbeForWrite` rejeita qualquer faixa acima de `MmUserProbeAddress`
  (`0x7FFFFFFF0000`), que é exatamente onde ficam os buffers de kernel.

Consequências:

1. com `g_data` em VA de sistema, `UserMode` faria o probe falhar **sempre**;
2. isso já era um bug latente: `KmImagePath` passa `&params`, `&name` e `tmp`
   (stack e pool, endereços de kernel) com `UserMode` — ou seja, `image_path`
   não podia funcionar. Nenhum teste do repositório exercitou esse caminho
   (`find_module` vem de `win32_memory`), por isso passou despercebido.

O lado do **alvo** continua sendo endereço user de outro processo; quem valida é
a própria `MmCopyVirtualMemory` (attach + tratamento de exceção, devolvendo
`STATUS_PARTIAL_COPY`/erro), e não um probe do chamador.

**Risco assumido:** com `KernelMode` não há probe do lado do chamador. Os buffers
do chamador passam a ser sempre de kernel (view de sistema, stack, pool), o que
é verdade por construção nos dois arquivos. É o item **nº 1** a validar na VM,
porque o comportamento interno da API não é documentado linha a linha.

### 4.4 Arquitetura convencional (patch 0003/0004)

| Aspecto | Seção compartilhada (atual/0001) | Device + IOCTL (0003) |
|---|---|---|
| Dono do buffer | driver (seção) + cliente mapeia a mesma memória | I/O manager (system buffer por IRP) |
| Ciclo de vida | enquanto o driver viver | duração do IRP |
| Validação | manual, campo a campo | `InputBufferLength`/`OutputBufferLength` + validação manual |
| Quem pode comandar | qualquer processo que abra a seção (DACL herdada de SYSTEM) | qualquer processo que abra o device (DACL padrão: SYSTEM + Admins) |
| Concorrência | protocolo manual entre modos | um IRP por chamada; sem estado compartilhado |
| Teardown | não existe | `IRP_MJ_CLEANUP`/`CLOSE` + `DriverUnload` |
| Estado global | ponteiro + thread | nenhum |
| Carga | loader que injeta código | SCM (`sc create`/`sc start`) |
| Custo | polling de 1 ms | chamada direta |

O 0003 não usa `METHOD_NEITHER` (que exigiria `ProbeForRead`/`ProbeForWrite` e
`MmProbeAndLockPages` manuais) nem `METHOD_IN_DIRECT/OUT_DIRECT` (MDL). Buffered
é o mais simples de validar e o que dá o controle de tamanho mais direto.

Segurança: o device fica com o descritor padrão (SYSTEM + Administrators) e
`FILE_DEVICE_SECURE_OPEN` aplica esse descritor a **todo** open por nome, não só
ao primeiro. **Não** relaxei nada; se o cliente tiver de rodar sem elevação, a
mudança correta é `IoCreateDeviceSecure` com SDDL explícito — e isso precisa da
tua decisão, não é algo para um patch silencioso.

---

## 5. O diff, trecho por trecho

### 5.1 `proposals/0001-km_rw-driver-bounds-resources-protocol.diff`

Aplicar em `C:\Users\luiz\km_cheat\` (a árvore do driver, fora do repo).

#### A1 — cabeçalho do arquivo (antes 1-14 → depois 1-26)

Documenta o novo modelo de memória e o protocolo. Sem efeito em código.

#### A2 — constantes (antes 27-29 → depois 39-53)

**Problema:** os limites não existiam; `KM_SHARED_SIZE - KM_DATA_OFFSET` era
repetido inline e sem nome; `Status` era um estado de 3 valores.

```c
/* antes */
#define KM_SHARED_NAME L"\\BaseNamedObjects\\KmRwShared"
#define KM_SHARED_SIZE 0x400000
#define KM_DATA_OFFSET 0x400
...
#define KM_STATUS_BUSY  0
#define KM_STATUS_DONE  1
#define KM_STATUS_ERROR 2

/* proposto */
#define KM_DATA_CAPACITY (KM_SHARED_SIZE - KM_DATA_OFFSET)   /* 0x3FFC00 */
#define KM_MAX_PATH_CHARS 0x8000
#define KM_MAX_USER_ADDRESS 0x00007FFFFFFF0000ULL
/* KM_STATUS_* removidos: não existe mais estado "busy" */
```

**Justificativa:** §1.1. Nomear os limites é o que permite verificá-los num
único ponto em vez de repetir a conta em cada `switch`.
**Efeito colateral:** `KM_STATUS_*` deixa de existir; só era usado no worker.

#### A3 — `KM_SHARED` + `C_ASSERT` de ABI (antes 39-46 → depois 61-80)

**Problema:** o layout era um contrato implícito com o ctypes do cliente.

```c
/* antes */
typedef struct _KM_SHARED {
    volatile LONG Command;
    volatile LONG Status;
    LONG          ErrorCode;
    ULONG64       Pid;      /* offset 0x10 por padding implícito */
    ULONG64       Address;
    ULONG64       Size;
} KM_SHARED, *PKM_SHARED;

/* proposto */
typedef struct _KM_SHARED {
    volatile LONG Command;      /* 0x00 */
    volatile LONG Completion;   /* 0x04: kernel only */
    LONG          ErrorCode;    /* 0x08 */
    LONG          Reserved;     /* 0x0C: padding explícito */
    ULONG64       Pid;          /* 0x10 */
    ULONG64       Address;      /* 0x18 */
    ULONG64       Size;         /* 0x20 */
} KM_SHARED, *PKM_SHARED;

C_ASSERT(sizeof(KM_SHARED) == 0x28);
C_ASSERT(FIELD_OFFSET(KM_SHARED, Completion) == 0x04);
/* ... Command, ErrorCode, Pid, Address, Size ... */
```

**Justificativa:** `Completion` no mesmo offset de `Status` mantém o layout;
`Reserved` torna o padding explícito (nada de "confiar no alinhamento");
os `C_ASSERT` transformam um erro de ABI em erro de compilação. `C_ASSERT` +
`FIELD_OFFSET` é padrão do próprio WDK (93 ocorrências nos headers 22621).
**Efeito colateral:** quebra de fonte para qualquer outro consumidor que use
`Status` (não há outro).

#### A4 — globais voláteis (antes 48-49 → depois 82-83)

```c
/* antes  */ static PKM_SHARED g_shared = NULL;  static PUCHAR g_data = NULL;
/* depois */ static PKM_SHARED volatile g_shared = NULL;
             static PUCHAR     volatile g_data   = NULL;
```

**Justificativa:** o compilador não pode cachear o ponteiro entre iterações do
loop nem entre a thread e o init.

#### A5 — validação (novo, depois 86-121)

```c
static NTSTATUS
KmValidateRange(ULONG64 pid, ULONG64 address, ULONG64 size)
{
    if (pid == 0 || pid > 0xFFFFFFFFULL)
        return STATUS_INVALID_PARAMETER;
    if (size == 0 || size > KM_DATA_CAPACITY)
        return STATUS_INVALID_BUFFER_SIZE;
    if (address > KM_MAX_USER_ADDRESS)
        return STATUS_INVALID_PARAMETER;
    if (size - 1 > KM_MAX_USER_ADDRESS - address)
        return STATUS_INVALID_PARAMETER;
    return STATUS_SUCCESS;
}

static NTSTATUS
KmValidatePid(ULONG64 pid) { /* mesma checagem de pid */ }
```

**Justificativa:** §1. Um único ponto, chamado antes de qualquer lookup ou
cópia, com a ordem que evita overflow. `KmValidatePid` existe porque
`image_path` não usa `Size`/`Address`.
**Efeito colateral:** PIDs > `0xFFFFFFFF` e `Size == 0` passam a falhar (antes
havia truncamento silencioso para `HANDLE` e um no-op, respectivamente).

#### A6 — `PreviousMode` (antes 57-59, 66-68, 80-89, 102-103 → depois 140-146, 149-155, 163-167, 174-178, 185-189)

```c
/* antes  */ (SIZE_T)size, UserMode, &bytes);
/* depois */ (SIZE_T)size, KernelMode, &bytes);
```

**Justificativa:** §4.3. Obrigatório com VA de sistema e com os buffers de
kernel do `KmImagePath`.
**Efeito colateral:** remove o probe do lado do chamador. É o risco nº 1 (§8).

#### A7 — mapeamento em VA de sistema (antes 183-206 → depois 315-331)

```c
/* antes */
PEPROCESS systemProcess = NULL;
HANDLE systemHandle = NULL;
st = PsLookupProcessByProcessId((HANDLE)4, &systemProcess);
if (NT_SUCCESS(st)) {
    st = ObOpenObjectByPointer(systemProcess, OBJ_KERNEL_HANDLE, NULL,
                               0x38, *PsProcessType, KernelMode, &systemHandle);
    ObDereferenceObject(systemProcess);
}
if (NT_SUCCESS(st)) {
    st = ZwMapViewOfSection(section, systemHandle, &view, 0, KM_SHARED_SIZE,
                            NULL, &viewSize, ViewShare, 0, PAGE_READWRITE);
    ZwClose(systemHandle);
}
ZwClose(section);
if (!NT_SUCCESS(st))
    return st;

/* proposto */
st = ObReferenceObjectByHandle(section, SECTION_ALL_ACCESS, NULL,
                               KernelMode, &sectionObject, NULL);
ZwClose(section);
section = NULL;

if (NT_SUCCESS(st)) {
    st = MmMapViewInSystemSpace(sectionObject, &view, &viewSize);
    ObDereferenceObject(sectionObject);          /* a view mantém a referência */
    sectionObject = NULL;
}
if (!NT_SUCCESS(st))
    return st;
```

**Justificativa:** §4.1/§4.2. Elimina `PsProcessType` e
`ObOpenObjectByPointer` — os dois símbolos que a fase anterior suspeitava — e
torna o VA válido em qualquer contexto.
**Efeito colateral:** dois imports novos (`MmMapViewInSystemSpace`,
`Unmap`), dois removidos (`ObOpenObjectByPointer`, `PsProcessType`); IRQL ≤
APC_LEVEL (o init é PASSIVE); a view é pageable.

#### A8 — recursos e caminhos de falha (antes 207-219 → depois 332-361)

```c
/* antes */
if (!NT_SUCCESS(st))
    return st;               /* <- vazava a view de 4 MB */

/* proposto */
if (view == NULL)                              /* nada mapeado, nada a liberar */
    return STATUS_INVALID_VIEW_SIZE;

if (viewSize < KM_SHARED_SIZE) {               /* não confia no pedido */
    MmUnmapViewInSystemSpace(view);
    return STATUS_INVALID_VIEW_SIZE;
}
...
if (!NT_SUCCESS(st)) {
    g_shared = NULL;
    g_data   = NULL;
    MmUnmapViewInSystemSpace(view);           /* libera exatamente uma vez */
    return st;
}
```

**Justificativa:** §2. O `viewSize` de saída agora é conferido — é a resposta
literal à pergunta "o tamanho solicitado é o tamanho acessível?" — e o `view`
nulo deixa de ser uma suposição.
**Efeito colateral:** nenhum caminho novo de sucesso; só falhas deixam de vazar.

#### A9 — worker (antes 114-156 → depois 202-274)

```c
/* antes */
if (g_shared && g_shared->Command != 0) {
    LONG cmd = g_shared->Command;             /* 2 leituras + 1 escrita */
    ...
    g_shared->ErrorCode = (LONG)st;
    g_shared->Status = NT_SUCCESS(st) ? KM_STATUS_DONE : KM_STATUS_ERROR;
    g_shared->Command = 0;                    /* apaga comando novo */
}

/* proposto */
LONG cmd = InterlockedExchange(&shared->Command, 0);
if (cmd != 0) {
    ULONG64 pid = shared->Pid, address = shared->Address, size = shared->Size;
    ...
    shared->ErrorCode = (LONG)st;
    InterlockedIncrement(&shared->Completion);
}
```

**Justificativa:** §3.3. Os campos são copiados para locais **antes** de
qualquer processamento, então o `switch` nunca relê estado compartilhado.
**Efeito colateral:** o worker lê os campos mesmo quando o comando é inválido
(inofensivo: são apenas leituras). Um comando publicado durante o processamento
fica pendente (comportamento novo e correto).

#### A10 — clamp do `image_path` (depois 179-183)

```c
ULONG chars = name.Length / sizeof(WCHAR);
if (chars >= KM_MAX_PATH_CHARS)      /* Length é USHORT */
    chars = KM_MAX_PATH_CHARS - 1;
if (chars >= outChars)
    chars = outChars - 1;
```

**Justificativa:** o limite estrutural (`USHORT`) passa a estar explícito, e não
só o limite do destino; os dois clamps são necessários.
**Efeito colateral:** nenhum (o destino é muito maior que `0x8000` chars).

---

### 5.2 `proposals/0002-km_memory-client-protocol-chunking.diff`

Aplicar na raiz do repo (`Documents\BloodStrikeExternal`).

#### C1 — constantes (antes 22-38 → depois 28-45)

`DATA_CAPACITY`, `MAX_USER_ADDRESS`, `STATUS_INVALID_BUFFER_SIZE` (valor
correto: `0xC0000206`; `0xC0000023` é `STATUS_BUFFER_TOO_SMALL`). Constantes
`STATUS_*` removidas. `VIEW_SHARE = 2` renomeado para `VIEW_UNMAP = 2` — o valor
2 **é** `ViewUnmap`; o nome antigo estava errado (o driver usa `ViewShare = 1`).

#### C2 — `KM_SHARED` + asserts (antes 56-62 → depois 65-84)

`Status` → `Completion`, `Reserved` explícito, e asserts de `sizeof`/offset
espelhando os `C_ASSERT`. Um desvio de layout agora falha no import do módulo,
em user mode, em vez de corromper um pedido.

#### C3 — protocolo (antes 128-145 → depois 164-195)

**Problema:** §3.2(a).

```python
# antes
sh.Status = STATUS_BUSY
sh.Command = command
while self._shared.contents.Status == STATUS_BUSY: ...

# proposto
seq = self._shared.contents.Completion          # lê antes de publicar
self._shared.contents.Command = command
while self._shared.contents.Completion == seq: ...
err = self._shared.contents.ErrorCode
if err:
    raise ...
```

**Justificativa:** o cliente nunca escreve estado no kernel; o contador
monotônico elimina a janela de comando perdido.
**Efeito colateral:** incompatível com o driver antigo (ver §3.3). Um comando
que estoure o timeout deixa `Completion` avançar depois; a próxima chamada usa um
`seq` novo, então não há dessincronização.

#### C4 — `read`/`write` com blocos (antes 149-161 → depois 197-216)

```python
while len(out) < size:
    chunk = min(DATA_CAPACITY, size - len(out))
    self._run(CMD_READ, address + len(out), None, chunk)
    out += ctypes.string_at(self._data, chunk)
```

**Justificativa:** preserva a interface pública para leituras > 4 MB, agora
respeitando o limite do driver. O `_run` também valida faixa/tamanho e levanta
erro claro antes de tocar no kernel.
**Efeito colateral:** uma transferência grande deixa de ser atômica (nunca foi,
na prática). Leituras acima de `MAX_READ` (16 MB, `memory.py`) continuam
rejeitadas por `check_range`.

---

### 5.3 `proposals/0003-km_rw-ioctl-conventional-driver.diff` (arquivo novo)

Aplicar em `C:\Users\luiz\km_cheat\`. Cria `km_rw/km_rw_ioctl.c` (400 linhas).

Pontos que importam na revisão:

- `C_ASSERT(sizeof(KM_REQUEST) == 0x18)` — ABI do IOCTL;
- `IoCreateDevice(..., FILE_DEVICE_UNKNOWN, FILE_DEVICE_SECURE_OPEN, TRUE, ...)`;
- `KmUnload`: apaga o symbolic link **antes** do device;
- `KmDeviceControl` copia o cabeçalho para locais antes de escrever no buffer
  (com `METHOD_BUFFERED` a saída sobrescreve a entrada);
- `IoStatus.Information`: `0` no write (um valor > `OutputBufferLength` faria o
  I/O manager copiar além do buffer do usuário), `copied` no read,
  `chars*2` no image path — todos ≤ `OutputBufferLength` por construção;
- duas cópias de validação (`KmValidateRange`/`KmValidatePid`) com o limite de
  1 MB e a mesma comparação à prova de overflow.

Não incluí `IoCreateDeviceSecure`/SDDL: mudaria a política de acesso, e isso é
decisão tua, não de um patch de correção.

### 5.4 `proposals/0004-km_memory-ioctl-conventional-client.diff` (arquivo novo)

Aplicar na raiz do repo. Cria `ExternalCore/km_memory_ioctl.py` (144 linhas),
mesma interface pública (`read`/`write`/`image_path`/context manager).
`_ioctl` usa um único buffer para entrada e saída (permitido e natural em
`METHOD_BUFFERED`), e `read` valida que o retorno tem exatamente `chunk` bytes.

---

## 6. Artefatos e verificação

| Patch | Base | Arquivos | SHA-256 |
|---|---|---|---|
| `0001-km_rw-driver-bounds-resources-protocol.diff` | `C:\Users\luiz\km_cheat\` | `km_rw/km_rw.c` | `FCF23E63C8B24E6703774A098EE75C631A310FA7143B1E6E2331E4D0AC5E6876` |
| `0002-km_memory-client-protocol-chunking.diff` | repo | `ExternalCore/km_memory.py` | `B73A4FD92141152D76163EA1F6257A2D5D0CEA1A64EAF085DDD9118024003174` |
| `0003-km_rw-ioctl-conventional-driver.diff` | `C:\Users\luiz\km_cheat\` | `km_rw/km_rw_ioctl.c` (novo) | `32093804F1D8EB3028A9F6D9EDA1FF778B13CD4DDDF6C424B2CCFE19E933E0CB` |
| `0004-km_memory-ioctl-conventional-client.diff` | repo | `ExternalCore/km_memory_ioctl.py` (novo) | `019F730CB74E860E35629BF779944CC61C8C8B366DA5321F350938C786925A3A` |

Totais: `0001` +207/−66 em `km_rw.c`; `0002` +61/−19 em `km_memory.py`;
`0003` +400; `0004` +144 (812 inserções, 85 remoções no total).

> Existe uma cópia de `km_memory.py` em `C:\Users\luiz\km_cheat\ExternalCore\`
> com **conteúdo idêntico** mas finais de linha **LF** (a do repo é CRLF). O patch
> `0002` foi gerado para a cópia do repo. Sobre a cópia LF ele só aplica com
> `git apply --ignore-whitespace` (testado). O caminho canônico é o repo.

### Verificações já executadas (estáticas, sem compilar o driver)

1. `git apply --check` nos 4 patches, em três cenários: clone do repo, árvore
   fora de repo (driver) e árvore fora de repo (cliente). **4/4 ok.**
2. `git apply` real em clone descartável e comparação byte a byte com o
   resultado pretendido: **idêntico**, exceto conversão CRLF→LF do
   `core.autocrlf` do repo.
3. `ast.parse` nos dois clientes: **ok**.
4. Asserts de ABI do ctypes executados de forma isolada:
   `sizeof 0x28`, `Completion 0x04`, `ErrorCode 0x08`, `Pid 0x10`,
   `Address 0x18`, `Size 0x20` — **ok**.
5. Símbolos usados existem nos headers 22621: `MmMapViewInSystemSpace`,
   `MmUnmapViewInSystemSpace` (exportados pelo ntoskrnl 19045),
   `STATUS_INVALID_VIEW_SIZE`, `STATUS_INVALID_BUFFER_SIZE` (`0xC0000206`),
   `FILE_DEVICE_SECURE_OPEN` (`wdm.h`), `C_ASSERT`+`FIELD_OFFSET`
   (93 usos nos próprios headers).

### Testes estáticos a rodar depois de aplicar (ainda sem compilar)

```powershell
# 1. Nenhum acesso direto a VA de user space sobrou
Select-String km_rw\km_rw.c -Pattern "ZwMapViewOfSection|ObOpenObjectByPointer|PsProcessType"
# esperado: nenhum resultado

# 2. Nenhum PreviousMode UserMode sobrou
Select-String km_rw\km_rw.c -Pattern "UserMode"
# esperado: só "KeDelayExecutionThread(KernelMode" ... nenhum "UserMode"

# 3. Nenhum estado "busy" compartilhado
Select-String km_rw\km_rw.c -Pattern "KM_STATUS|->Status"
# esperado: nenhum resultado

# 4. Todo uso de tamanho passa por um limite nomeado
Select-String km_rw\km_rw.c -Pattern "KM_DATA_CAPACITY|KM_MAX_PATH_CHARS|KM_MAX_USER_ADDRESS"

# 5. O cliente importa e os asserts de ABI passam (não abre driver nenhum)
python -c "from ExternalCore import km_memory, km_memory_ioctl; print(km_memory.KM_SHARED.Completion.offset)"

# 6. Depois de compilar (fase seguinte): provas no binário
#    dumpbin /imports km_rw.sys   -> sem PsProcessType/ObOpenObjectByPointer,
#                                    com MmMapViewInSystemSpace
#    dumpbin /headers km_rw.sys   -> segue sem .reloc (esperado)
```

Checklist manual no 0003 (revisão de `METHOD_BUFFERED`):

- [ ] todo caminho que grava em `SystemBuffer` respeita
      `size ≤ OutputBufferLength`;
- [ ] `IoStatus.Information` ≤ `OutputBufferLength` em todos os `case`;
- [ ] nenhum `case` usa `buffer` depois de uma cópia de saída;
- [ ] `ZwCreateSection`/`ObReferenceObjectByHandle`/`MmMapViewInSystemSpace`
      liberados exatamente uma vez por caminho.

---

## 7. Ordem de aplicação e rollback

```powershell
# driver (0001, 0003)
cd C:\Users\luiz\km_cheat
git apply --check  C:\Users\luiz\Documents\BloodStrikeExternal\proposals\0001-*.diff
git apply          C:\Users\luiz\Documents\BloodStrikeExternal\proposals\0001-*.diff

# cliente (0002, 0004)
cd C:\Users\luiz\Documents\BloodStrikeExternal
git apply --check  proposals\0002-*.diff
git apply          proposals\0002-*.diff
```

Rollback: `km_rw.c` está no backup
`C:\Users\luiz\km_cheat_backup\20261122_172616\km_rw\km_rw.c`
(SHA `651FC510…`); o cliente sai com `git checkout -- ExternalCore/km_memory.py`.
Os arquivos 0003/0004 são novos: basta apagar.

**Não aplicar 0001 e 0003 juntos no mesmo build**: 0003 é um driver alternativo
(device + IOCTL), não um delta do 0001.

---

## 8. O que continua não provado

1. **`MmCopyVirtualMemory` com `PreviousMode = KernelMode` e buffer de sistema**
   — é o item nº 1 da VM. Se falhar, a alternativa é `KeStackAttachProcess` +
   `__try/__except` em volta de `RtlCopyMemory` no processo alvo.
2. **`MmMapViewInSystemSpace` nesta build** (19045) — exportado, mas não
   exercitado. Se falhar, o fallback é manter o mapa no PID 4 **sem** o
   `RtlZeroMemory` (páginas `SEC_COMMIT` já vêm zeradas) e só acessar da thread
   de sistema — isto é, o desenho do 0001 sem a parte do init.
3. **DACL da seção/device para cliente não elevado** (B7) — não medido.
4. **Compilação** — nada foi compilado; os patches foram validados como texto e
   por inspeção, não por compilador.

## 9. O que não foi feito

- Nenhum arquivo original alterado; nenhum commit.
- Nada compilado, nada executado, nada instalado.
- Nenhum uso de KDU, kdmapper, BYOVD ou mapeamento manual.
- Nenhuma alteração de privilégio, política de segurança ou configuração do
  Windows.
- Nenhum teste na máquina principal.
