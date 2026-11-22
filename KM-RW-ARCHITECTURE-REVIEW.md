# Revisão de arquitetura e segurança — `km_rw` (diffs 0001-0004)

Revisão final antes de qualquer aplicação. **Nada foi alterado, aplicado, compilado
ou executado.** Os quatro diffs e os originais estão congelados; os hashes estão
na §0.

Método: leitura dos quatro diffs, dos headers do WDK 10.0.22621 e da export table
do `ntoskrnl` 19045. Onde a conclusão depende de comportamento não documentado,
está marcado como tal.

---

## 0. Artefatos congelados

| Item | SHA-256 |
|---|---|
| `km_rw.c` (original) | `651FC5106E1B7D3FB351CADAE4321C0343A6E224D93281C3BA0911DC727460A2` |
| `km_rw.sys` (original) | `83F53EA9B6F2B00F1D210D507022BFD35D6EDF9FF6481A95FD16E1DCDF438A5B` |
| `proposals/0001-…diff` | `FCF23E63C8B24E6703774A098EE75C631A310FA7143B1E6E2331E4D0AC5E6876` |
| `proposals/0002-…diff` | `B73A4FD92141152D76163EA1F6257A2D5D0CEA1A64EAF085DDD9118024003174` |
| `proposals/0003-…diff` | `32093804F1D8EB3028A9F6D9EDA1FF778B13CD4DDDF6C424B2CCFE19E933E0CB` |
| `proposals/0004-…diff` | `019F730CB74E860E35629BF779944CC61C8C8B366DA5321F350938C786925A3A` |

Nada aqui altera esses arquivos; a revisão é somente leitura.

---

## 1. Separação de responsabilidades

### 1.1 Inventário: infraestrutura × funcionalidade específica

| Diff | Infraestrutura genérica (reutilizável) | Específico de acesso à memória |
|---|---|---|
| **0001** | ciclo de vida seção/view/thread, `KmValidateRange` (faixa e overflow), protocolo de latch, caminhos de erro | `KmRead`/`KmWrite`/`KmImagePath`, `MmCopyVirtualMemory`, `PsGetProcessPeb` + offsets `0x20`/`0x60`, semântica de PID/endereço |
| **0002** | transporte (abrir/mapear a seção), ABI ctypes, chunking, validação de faixa no cliente | `CMD_READ`/`CMD_WRITE`/`CMD_IMAGE_PATH`, `read`/`write`/`image_path` |
| **0003** | device, symlink, dispatch de IOCTL, validação de tamanho, unload, create/close | `KmReadProcess`, `KmWriteProcess`, `KmImagePathProcess`, os três IOCTLs de dados |
| **0004** | `CreateFile`/`DeviceIoControl`/`CloseHandle`, marshalling, tratamento de erro | `read`/`write`/`image_path` |

A proporção é reveladora: **em 0003, ~60% do arquivo é infraestrutura e ~40% é a
funcionalidade de memória.** O núcleo (device + dispatch + validação + ciclo de
vida) não depende de nada específico e é o que deveria ser revisado e aceito
primeiro. A camada de dados é a parte que carrega todo o risco e todas as APIs não
documentadas.

### 1.2 O núcleo reutilizável

Estas partes não sabem o que é um processo e podem ser mantidas sem discussão:

- `DriverEntry` (device, symlink, `MajorFunction`, `DriverUnload`);
- `KmDeviceControl` como *esqueleto*: ler `IoControlCode`, `InputBufferLength`,
  `OutputBufferLength`, despachar, preencher `IoStatus`, completar o IRP;
- `KmValidateRange` (faixa + overflow) — é aritmética pura;
- `KmUnload`, `KmCreateClose`;
- o transporte do cliente (`_ioctl`, buffer único, `Information`).

### 1.3 O que não deve ser ampliado

Os três IOCTLs de dados (`0x800`-`0x802` em 0003) e os três comandos de 0001/0002
implementam **leitura e escrita arbitrária de memória de outro processo**. Isso não
é um detalhe de implementação: é a capacidade principal do driver e a razão pela
qual o anti-cheat o procura. Ampliar essa superfície (mais comandos, mais
endereços, write) não é uma decisão de engenharia isolada.

**Recomendação de arquitetura:** o núcleo (consultas inofensivas) é a v1; a camada
de dados fica fora da v1 e, se voltar, exige decisão separada e um modelo de
ameaça próprio (§7.4). Não proponho código novo de leitura/escrita nesta revisão.

---

## 2. Protocolo IOCTL (0003/0004)

### 2.1 ABI: definição e estabilidade

| Elemento | Estado atual | Estabilidade |
|---|---|---|
| `\Device\KmRw` + `\DosDevices\KmRw` | fixo no código | estável, mas enumerável |
| `KM_REQUEST` (0x18) | `Pid/Address/Size` | **sem versão nem tamanho** — ver R3 |
| IOCTL `0x800/0x801/0x802` | `CTL_CODE(FILE_DEVICE_UNKNOWN, …)` | estável; mudar os bits de acesso muda o valor |
| `Information` | bytes escritos | correto nos três casos |
| Modelo de erro | NTSTATUS → `GetLastError` | estável |
| Alinhamento | todos `ULONG64`; `SystemBuffer` de pool (`MEMORY_ALLOCATION_ALIGNMENT` = 16 no x64) | ok na prática |

**R3 (média) — ABI sem versão.** Não há como o driver detectar um cliente de outra
geração. Um cliente futuro que acrescente campos ao `KM_REQUEST` continua sendo
aceito (o driver lê só 0x18) — o que "funciona" por acidente e falha silencioso no
dia em que o campo mudar de posição ou significado. A ABI precisa de
`AbiVersion` + `StructSize` explícitos (§8).

### 2.2 Validação de tamanhos — matriz de entradas

| Entrada | Comportamento atual | Status |
|---|---|---|
| `inLen = 0` | rejeitado | `STATUS_BUFFER_TOO_SMALL` |
| `inLen = 0x17` | rejeitado | `STATUS_BUFFER_TOO_SMALL` |
| `inLen ≥ 0x18`, `size = 0` | rejeitado | `STATUS_INVALID_BUFFER_SIZE` |
| `size > 0x100000` | rejeitado | `STATUS_INVALID_BUFFER_SIZE` |
| `address` em kernel space | rejeitado | `STATUS_INVALID_PARAMETER` |
| `address + size - 1` passa do limite | rejeitado (sem overflow) | `STATUS_INVALID_PARAMETER` |
| `size > outLen` (read) | rejeitado | `STATUS_BUFFER_TOO_SMALL` |
| payload curto (write) | rejeitado, subtração protegida | `STATUS_BUFFER_TOO_SMALL` |
| pid 0 / > 32 bits | rejeitado | `STATUS_INVALID_PARAMETER` |
| IOCTL desconhecido | rejeitado | `STATUS_INVALID_DEVICE_REQUEST` |
| **`inLen`/`outLen` = 4 GB** | **aceito** | **R1** |

**R1 (média, requer admin) — `inLen`/`outLen` sem teto.** `KM_MAX_XFER` limita
`size`, mas não `InputBufferLength`/`OutputBufferLength` (0003:236-237). Em
`METHOD_BUFFERED` o I/O manager aloca `max(in, out)` em **pool não paginado, com
quota cobrada ao processo chamador** antes de chamar o driver. Como a quota padrão
é ilimitada fora de um job object, um cliente pode pedir centenas de MB por IRP e
exaurir o pool não paginado do sistema (pedidos de 4 GB normalmente falham antes,
com `STATUS_INSUFFICIENT_RESOURCES`). Não é escalada de privilégio (o device exige
admin), é DoS/robustez. Correção: rejeitar
`inLen > sizeof(KM_REQUEST) + KM_MAX_XFER` e `outLen > KM_MAX_XFER` **antes** de
tocar no buffer.

**R2 (baixa) — cast do `SystemBuffer`.** 0003:258-260, 282-284, 312 fazem
`((PKM_REQUEST)buffer)->Campo`. Funciona porque a pool garante alinhamento ≥ 16,
mas o correto é `RtlCopyMemory` para um `KM_REQUEST` local: elimina a dependência
de alinhamento e qualquer dúvida de aliasing. Hoje o padrão "copiar para locais
antes de escrever na saída" já existe — falta só a cópia do cabeçalho.

### 2.3 Controle de acesso

**R4 (média) — ACL implícita.** 0003:374 usa `IoCreateDevice` com
`SecurityDescriptor = NULL`. O descritor resultante é o **padrão do token do
criador** (SYSTEM no `DriverEntry`), que na prática inclui SYSTEM e
Administradores. É o comportamento padrão do object manager, não uma política
declarada. `FILE_DEVICE_SECURE_OPEN` garante que o descritor seja aplicado a
**todo** open por nome — isso está correto e é o ponto mais importante — mas a
política em si continua implícita.

Recomendação: `IoCreateDeviceSecure` com SDDL explícito
(`D:P(A;;GA;;;SY)(A;;GA;;;BA)`). `wdmsec.h` declara e `wdmsec.lib` existe no kit
22621 (verificado), então não é dependência nova.

**R5 (baixa) — `IRP_MJ_CREATE` não valida `DesiredAccess`.** `KmCreateClose`
(0003:220) aceita qualquer abertura. Não dependa do I/O manager para aplicar os
bits de acesso do `CTL_CODE`: verifique o `DesiredAccess` no create (exigir
`FILE_READ_DATA` para as consultas) e/ou abra o cliente com o acesso mínimo.

**Ponto de arquitetura:** a ACL (SYSTEM/Admins) não protege contra o modelo de
ameaça real de um driver assim — qualquer processo elevado pode abrir o device. A
ACL serve para *não criar* superfície nova para usuário comum; ela não torna a
capacidade de R/W inofensiva.

### 2.4 Sincronização, cancelamento e ciclo de vida dos buffers

- **Buffers:** `Irp->AssociatedIrp.SystemBuffer` pertence ao I/O manager e vive até
  a conclusão do IRP. O driver não o retém, não o libera e não o usa depois de
  `IoCompleteRequest` — correto em 0003. `Information ≤ OutputBufferLength` em
  todos os caminhos (o write deixa `Information = 0`, que é a escolha certa).
- **Pendência:** nenhum caminho chama `IoMarkIrpPending`; o dispatch completa
  sempre de forma síncrona. Consequência: **não é necessário** rotina de cancelamento
  — um IRP só é cancelável enquanto está na fila, e ele nunca fica.
- **Cancelamento do lado do usuário:** matar a thread durante `DeviceIoControl`
  não interrompe `MmCopyVirtualMemory`; o IRP é concluído e o I/O manager libera o
  buffer. Não há use-after-free, mas a operação não é interrompível (até 1 MB de
  cópia com attach).
- **Unload:** `KmUnload` (0003:339) apaga o link antes do device, na ordem certa.
  **Suposição não verificada:** que o I/O manager recuse o unload enquanto houver
  handle aberto. Isso precisa ser provado no teste (`sc stop` com handle aberto
  deve falhar com `STATUS_DEVICE_BUSY`). Se não falhar, `KmUnload` corre com IRP em
  voo e vira use-after-free.
- **Reentrância:** 0003 não tem estado global; duas chamadas concorrentes de
  handles diferentes (impossível com `Exclusive = TRUE`) ou do mesmo handle são
  independentes. O I/O manager serializa por file object? **Não** — IOCTLs
  concorrentes no mesmo handle podem rodar em paralelo em threads diferentes. Como
  não há estado compartilhado, isso é seguro hoje; deixa de ser no dia em que
  existir contador/estado no device extension (usar `InterlockedXxx`).

---

## 3. Concorrência e recursos (0001/0002)

### 3.1 O que as garantias realmente cobrem

As afirmações anteriores ("exatamente uma execução", "nenhum comando perdido",
"`Completion` monotônico") são **verdadeiras sob três premissas que não estão
declaradas nem impostas**:

1. **um único cliente**;
2. **x86/x64 (TSO)**;
3. **nenhum timeout seguido de retry**.

### 3.2 Contra-exemplos

**R7 (alta) — múltiplos clientes.** O cabeçalho é único e não há identidade de
cliente. Se A publica `Command=1` e B publica `Command=2` antes do latch, o kernel
executa **os parâmetros de um comando com o código do outro** (os campos
`Pid/Address/Size` são sobrescritos por B). Além disso `g_data` é um buffer único:
duas leituras simultâneas se sobrescrevem. O protocolo é correto **apenas** com um
escritor. Nada no código impede o segundo. O `Exclusive = TRUE` do device (0003)
resolve isso por construção; a seção nomeada (0001) não tem equivalente.

**R8 (alta, rara) — timeout + retry devolve dado errado.** Sequência:

```
t0  cliente: seq = Completion (= N); publica cmd1
t1  kernel : trava cmd1, começa a cópia (lenta)
t2  cliente: 5 s estouram -> exceção; chamador tenta de novo
t3  cliente: seq = N (ainda); publica cmd2
t4  kernel : termina cmd1, ErrorCode(st1), Completion -> N+1
t5  cliente: vê N+1, conclui que cmd2 terminou, lê ErrorCode de cmd1
             e g_data possivelmente no meio da cópia de cmd2
```

O cliente devolve **dados de outra requisição sem erro**. É a pior classe de falha
(silenciosa), mesmo sendo improvável (exige cópia > 5 s). O contador incremental
identifica "algo completou", não **o quê**.

**R15 (baixa, documentação) — "monotônico" está errado.** `Completion` é `LONG`:
`InterlockedIncrement` passa de `0x7FFFFFFF` para `0x80000000` (negativo). A
igualdade continua válida e o wrap total é fail-safe (o cliente dá timeout em vez
de aceitar dado velho), mas o termo correto é **contador com wrap**, não
monotônico.

**R16 (baixa) — sem barreira de release no cliente.** O cliente escreve
`Pid/Address/Size` e depois `Command` com stores simples. Funciona por TSO
(store-store ordenado no x86). Em ARM64 ou sob um modelo de memória mais fraco,
não. Uma `InterlockedExchange` no `Command` do lado do cliente resolveria — mas
Python não expõe isso de forma portátil sem `ctypes` em `kernel32!InterlockedExchange`.

**R11 (média) — sem shutdown.** A thread de 0001 nunca termina e a view nunca é
desmapeada. Em driver mapeado isso é "por design"; em qualquer cenário com
descarga, é use-after-free. 0003 resolve com `DriverUnload`.

**R12 (média) — nome previsível.** `\BaseNamedObjects\KmRwShared` é fixo,
enumerável e pode ser **pré-criado** por outro processo (o `ZwCreateSection` falha
com `STATUS_OBJECT_NAME_COLLISION` → DoS de inicialização). Não é bug de memória;
é superfície de descoberta e de bloqueio.

### 3.3 Correção mínima do protocolo (se o caminho da seção for mantido)

Usar o campo `Reserved` (0x0C, hoje padding) como **`RequestId`** e transformar
`Completion` em **eco**, não contador:

```c
/* layout inalterado: 0x28 */
0x00 Command      (cliente -> kernel)
0x04 CompletionId (kernel -> cliente: ecoa o RequestId executado)
0x08 ErrorCode
0x0C RequestId    (cliente -> kernel, único por requisição)
0x10 Pid / Address / Size

cliente: rid = next_id(); RequestId = rid; Command = cmd
         espera CompletionId == rid        /* não "!= seq" */
kernel : cmd = InterlockedExchange(&Command, 0)
         rid = RequestId                    /* local, no latch */
         ... processa ...
         ErrorCode = st
         InterlockedExchange(&CompletionId, rid)
```

Isso elimina R8 (a conclusão carrega a identidade da requisição), mantém o layout
e não muda o tamanho da struct. R7 continua sem solução no modelo de seção —
apenas com a invariante "um cliente" **documentada e verificada** (ex.: o driver
recusa o segundo `NtOpenSection`? não é possível com seção nomeada; a alternativa
é o device).

---

## 4. APIs: documentado × não documentado

### 4.1 Inventário

| API | Onde está declarada no WDK 22621 | Classificação |
|---|---|---|
| `ZwCreateSection` | `wdm.h` | documentada |
| `ObReferenceObjectByHandle` | `wdm.h` | documentada |
| `MmMapViewInSystemSpace` / `Unmap` | `ntddk.h` (10929/10941) | documentada |
| `PsCreateSystemThread` | `ntifs.h` | documentada |
| `KeDelayExecutionThread` | `wdm.h` | documentada |
| `PsLookupProcessByProcessId` | `ntifs.h` (19351) | documentada |
| `ObDereferenceObject` | `wdm.h` | documentada |
| `InterlockedExchange` / `Increment` | `wdm.h` (intrinsics) | documentada |
| `IoCreateDevice` / `SymbolicLink` / `DeleteDevice` | `wdm.h` | documentada |
| `IoCreateDeviceSecure` | `wdmsec.h` (+ `wdmsec.lib`) | documentada |
| `IoCompleteRequest` / `IofCompleteRequest` | `wdm.h` | documentada |
| `ProbeForRead` / `ProbeForWrite` | `wdm.h` | documentada |
| **`MmCopyVirtualMemory`** | **nenhum header** | **não documentada / não suportada** |
| **`PsGetProcessPeb`** | **nenhum header** | **não documentada / não suportada** |
| `PsProcessType` (removido no 0001) | nenhum header (dado exportado) | não documentada |

Verificação: busca em **todos** os `*.h` de `Include\10.0.22621.0` retorna zero
declarações de `MmCopyVirtualMemory` e `PsGetProcessPeb`. Ambos existem na export
table do `ntoskrnl` 19045 (`MmCopyVirtualMemory` rva `0x5F6DB0`,
`PsGetProcessPeb` rva `0x313990`), e é só isso que o linker usa.

### 4.2 Por que "está nos exports" não é argumento de segurança

A fase anterior concluiu "15/15 imports existem, logo não há problema". Isso
responde **se o driver carrega**, não **se a interface é suportada**. A distinção
importa por três motivos concretos:

1. **Sem declaração, não há verificação de protótipo.** O `km_rw.c` declara
   `MmCopyVirtualMemory` à mão. Se a assinatura real divergir em um parâmetro, o
   compilador não avisa e o erro é um bug de pilha em Ring 0.
2. **Sem contrato, não há garantia de comportamento.** Toda a decisão do 0001 de
   trocar `PreviousMode` para `KernelMode` depende de *como* a função faz o probe
   internamente — comportamento que não está documentado. Foi a escolha certa, mas
   é uma inferência, não uma garantia (§8.1 da proposta anterior).
3. **Export não é estável.** Um export interno pode desaparecer ou mudar de
   semântica entre builds; uma API do WDK tem compromisso de compatibilidade.

### 4.3 Dependências não documentadas que restam

- `MmCopyVirtualMemory` — o núcleo da operação de dados.
- `PsGetProcessPeb` + offsets **`0x20`** (ProcessParameters) e **`0x60`**
  (ImagePathName) — layout interno do PEB/RTL_USER_PROCESS_PARAMETERS por
  arquitetura. Não muda só com a build do jogo; muda com a build do **Windows**.
- `IMAGE_FILE_MACHINE`/ABI do alvo — o driver é x64-only por construção.

Consequência para a arquitetura: **toda a parte de infraestrutura usa APIs
documentadas; toda a parte de memória depende de internos.** Isso reforça a
separação da §1 e é o argumento técnico para a v1 não incluir a camada de dados.

---

## 5. Avaliação diff por diff

### 5.1 `0001` — endurecimento da seção

**O que resolve bem:** B1/B5 (VA de sistema válido em qualquer contexto), B4
(tabela de propriedade, sem vazamento), B2 (limites derivados), o bug latente do
`image_path`, e remove `PsProcessType`/`ObOpenObjectByPointer`.

**O que fica devendo:** R7 (multi-cliente), R8 (timeout/retry), R10 (`g_data`
único), R11 (sem shutdown), R12 (nome previsível), R15/R16 (precisão e barreira),
R13 (`MmCopyVirtualMemory`/`PsGetProcessPeb`).

**Veredito:** correto para o que se propõe (**um** cliente, um escritor), com uma
invariante que precisa estar escrita no código e no cliente. Não é a arquitetura
recomendada — é o remendo do desenho antigo.

### 5.2 `0002` — cliente

**Bom:** protocolo sem estado compartilhado de "busy", validação antes de tocar no
kernel, chunking transparente, asserts de ABI.

**Problemas:** R8 (herdado), R9 (asserts somem com `python -O`), R16 (sem barreira),
e o `if err:` tratar qualquer NTSTATUS não-zero como erro (avisos positivos, como
`STATUS_PARTIAL_COPY` = `0x8000001A`, são `NT_SUCCESS` verdadeiro).

**Veredito:** consistente com 0001; precisa do `RequestId` para fechar R8.

### 5.3 `0003` — driver IOCTL

**Bom:** separação clara, sem estado global, dispatch síncrono sem pendência,
`Information` correto, validação de faixa à prova de overflow, ciclo de vida com
`DriverUnload`, `C_ASSERT` de ABI, cliente valida `len(data) == chunk`.

**Problemas:** R1 (teto de `inLen`/`outLen`), R2 (cast do SystemBuffer), R3 (sem
versão), R4 (ACL implícita), R5 (`DesiredAccess`), R13/R14 (APIs e offsets não
documentados), R6 (a capacidade de R/W é o produto, não um detalhe).

**Veredito:** a **melhor base** dos quatro. É o único que resolve R7 por
construção e o único com ciclo de vida real. Com R1-R5 corrigidos e a camada de
dados removida, é a arquitetura recomendada.

### 5.4 `0004` — cliente IOCTL

**Bom:** transporte mínimo, buffer único (natural em `METHOD_BUFFERED`), valida
leitura curta, interface pública igual à dos outros leitores.

**Problemas:** herdaria R6 (expõe `read`/`write`/`image_path`), e `_ioctl` não
distingue erro de transporte de erro de comando (ambos viram `MemoryReadError` com
`GetLastError`, o que é aceitável, mas perde o NTSTATUS original).

**Veredito:** adequado como transporte; na v1 recomendada, expõe só as consultas.

### 5.5 Problemas consolidados

| # | Onde | Problema | Severidade | Natureza |
|---|---|---|---|---|
| R1 | 0003:236-237 | `inLen`/`outLen` sem teto → alocação não paginada controlada pelo cliente | média (admin) | robustez/DoS |
| R2 | 0003:258-260 | cast de `SystemBuffer` para `PKM_REQUEST` | baixa | robustez |
| R3 | 0003:70-75 | ABI sem `AbiVersion`/`StructSize` | média | compatibilidade |
| R4 | 0003:374 | ACL implícita (default SD) | média | política |
| R5 | 0003:220 | create não valida `DesiredAccess` | baixa | defesa em profundidade |
| R6 | 0003/0004 | R/W arbitrário de outro processo é a capacidade do driver | **alta (decisão)** | arquitetura |
| R7 | 0001/0002 | protocolo só é correto com 1 cliente | alta | correção |
| R8 | 0002:170-176 | timeout+retry pode aceitar conclusão antiga | alta (rara) | correção |
| R9 | 0002:78-83 | asserts de ABI somem com `-O` | baixa | robustez |
| R10 | 0001 | `g_data` único, sem identidade de cliente | alta | correção |
| R11 | 0001 | thread sem shutdown; view sem unload | média | ciclo de vida |
| R12 | 0001 | nome de seção previsível | média | descoberta/DoS |
| R13 | 0001/0003 | `MmCopyVirtualMemory` não documentada | média | suporte |
| R14 | 0003 | `PsGetProcessPeb` + offsets `0x20`/`0x60` | média | suporte |
| R15 | doc 0001 | "monotônico" impreciso | baixa | documentação |
| R16 | 0001/0002 | stores sem release (x86-only) | baixa | portabilidade |

---

## 6. Riscos restantes (mesmo depois de aplicar tudo)

1. **O risco dominante não é um bug — é a capacidade.** Um driver que lê/escreve a
   memória de qualquer processo é, por definição, um primitivo de acesso arbitrário.
   Nenhuma validação de tamanho muda isso. R6 permanece até a camada de dados sair
   da v1.
2. **Detecção.** Nome de device/symlink/seção fixos são enumeráveis
   (`NtQueryDirectoryObject`, `\BaseNamedObjects`). Não é o escopo desta revisão
   tratar evasão — e não deve ser: a arquitetura recomendada não depende disso.
3. **Dependência de internos do Windows.** `MmCopyVirtualMemory`/`PsGetProcessPeb`
   podem mudar sem aviso. Um driver assim tem vida útil ligada à build do SO.
4. **`PreviousMode` (0001)** continua sendo o item nº 1 de validação em VM — é uma
   inferência sobre comportamento interno.

---

## 7. Arquitetura recomendada

### 7.1 Camadas

```
┌──────────────────────────────────────────────────────────┐
│ user mode                                                │
│   cliente: abre \\.\KmRwCtl, faz 3 consultas             │
└──────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│ km_core  (v1 — documentado, sem memória de processo)     │
│   device + SDDL explícito + ABI versionada               │
│   IOCTL_GET_VERSION / GET_STATE / GET_CAPABILITIES       │
│   sem estado global, sem buffers variáveis               │
└──────────────────────────────────────────────────────────┘
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
  (fora da v1) camada de dados — exigiria modelo de ameaça
  próprio, IOCTLs em faixa separada, e nova revisão
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

### 7.2 O que entra na v1

- `km_core` inteiro: device, dispatch, ABI, validação, unload.
- Cliente com as três consultas.
- Nenhum comando que receba PID, endereço ou tamanho variável.

### 7.3 Política de segurança da v1

- SDDL explícito `D:P(A;;GA;;;SY)(A;;GA;;;BA)`; `FILE_DEVICE_SECURE_OPEN`;
  `Exclusive = TRUE`.
- `DesiredAccess` verificado no `IRP_MJ_CREATE`.
- Toda ABI com `AbiVersion` + `StructSize`; mismatch → `STATUS_REVISION_MISMATCH`.
- Tamanhos exatos (`inLen == sizeof`, `outLen >= sizeof`), sem buffers variáveis.
- `Information = sizeof(resposta)`; nunca maior que `OutputBufferLength`.
- Zero estado global; contadores, se houver, na device extension com `Interlocked`.
- `DriverUnload` simétrico ao `DriverEntry`.

### 7.4 O que fica fora (e por quê)

A camada de dados não entra na v1. Se algum dia entrar, estes são pré-requisitos
mínimos — **não implementados aqui**:

- vínculo a **um** PID no `IRP_MJ_CREATE` (não por requisição), recusando troca
  depois — elimina o "qualquer processo";
- somente leitura, ou escrita restrita a faixas declaradas;
- allow-list de faixas por módulo (base+tamanho), não endereço livre;
- limite de taxa e contador de auditoria;
- revisão de ameaça própria (o que acontece se o cliente for comprometido).

---

## 8. Proposta de interface mínima e segura (v1)

Ilustrativa — não é um diff, não foi compilada. Nenhuma operação de memória.

### 8.1 Device

```
\Device\KmRwCtl          \DosDevices\KmRwCtl

UNICODE_STRING sddl;
RtlInitUnicodeString(&sddl, L"D:P(A;;GA;;;SY)(A;;GA;;;BA)");
IoCreateDeviceSecure(DriverObject, 0, &deviceName, FILE_DEVICE_UNKNOWN,
                     FILE_DEVICE_SECURE_OPEN, TRUE, &sddl,
                     &KM_DEVICE_CLASS_GUID /* GUID privado */, &device);
```

### 8.2 ABI

```c
#define KM_ABI_VERSION 1u

typedef struct _KM_QUERY {              /* 0x10, entrada de todas as consultas */
    ULONG32 AbiVersion;
    ULONG32 StructSize;                 /* sizeof(KM_QUERY) */
    ULONG32 Command;                    /* eco do IOCTL, defesa em profundidade */
    ULONG32 Reserved;                   /* 0 */
} KM_QUERY;

typedef struct _KM_VERSION {            /* 0x10 */
    ULONG32 AbiVersion;
    ULONG32 StructSize;
    ULONG32 DriverVersion;              /* 0x00010000 = 1.0 */
    ULONG32 BuildNumber;
} KM_VERSION;

typedef struct _KM_STATE {              /* 0x10 */
    ULONG32 State;                      /* 0 = init, 1 = ready, 2 = degraded */
    ULONG32 UptimeSeconds;
    ULONG64 RequestsServed;
} KM_STATE;

typedef struct _KM_CAPS {               /* 0x10 */
    ULONG32 StructSize;
    ULONG32 CapabilityMask;             /* bit0 query, bit1 state, bit2 caps */
    ULONG32 MaxRequest;                 /* 0 na v1 (sem canal de dados) */
    ULONG32 Reserved;
} KM_CAPS;
```

| IOCTL | Código | Entrada | Saída |
|---|---|---|---|
| `IOCTL_KM_GET_VERSION` | `CTL_CODE(0x22, 0x800, METHOD_BUFFERED, FILE_READ_DATA)` | `KM_QUERY` | `KM_VERSION` |
| `IOCTL_KM_GET_STATE` | `… 0x801 …` | `KM_QUERY` | `KM_STATE` |
| `IOCTL_KM_GET_CAPS` | `… 0x802 …` | `KM_QUERY` | `KM_CAPS` |

### 8.3 Regras de validação (todas antes de qualquer acesso)

1. `inLen == sizeof(KM_QUERY)` — igualdade, não `>=` (ABI fixa).
2. `outLen >= sizeof(resposta)`; `Information = sizeof(resposta)`.
3. `q->AbiVersion != KM_ABI_VERSION` → `STATUS_REVISION_MISMATCH`.
4. `q->StructSize != sizeof(KM_QUERY)` → `STATUS_INVALID_PARAMETER`.
5. `q->Command != IoControlCode` → `STATUS_INVALID_PARAMETER`.
6. IOCTL desconhecido → `STATUS_INVALID_DEVICE_REQUEST`.
7. Nenhum buffer de tamanho variável; nenhum ponteiro do usuário.

### 8.4 Ciclo de vida

- `DriverEntry`: criar device + link; falha → desfaz o que criou.
- `KmUnload`: `IoDeleteSymbolicLink` → `IoDeleteDevice`.
- Create/cleanup/close: sem estado; create valida `DesiredAccess`.
- Nenhum IRP fica pendente; nenhuma rotina de cancelamento necessária.

### 8.5 Por que isto é seguro

> Estes são argumentos de **desenho**, não resultados de execução. Nenhuma
> destas propriedades foi verificada em kernel real; a verificação está em
> `KM-CORE-VM-TEST-MATRIX.md` (T1–T12).

- A superfície inteira são três consultas de tamanho fixo, sem ponteiros.
- Não há como transformar um pedido numa leitura/escrita de outro processo.
- ABI versionada: qualquer extensão futura é detectável e recusável.
- ACL explícita; nenhuma dependência de descritor padrão.
- Encaixa na matriz de testes de IOCTL da §9 sem casos especiais.

---

## 9. Testes estáticos necessários

### 9.1 No código (antes de compilar)

```powershell
# 1. A camada v1 não pode importar APIs não documentadas
Select-String km_core.c -Pattern "MmCopyVirtualMemory|PsGetProcessPeb|PsProcessType"
# esperado: nenhum resultado

# 2. ABI travada
Select-String km_core.c -Pattern "C_ASSERT"
# esperado: sizeof == 0x10 para KM_QUERY/VERSION/STATE/CAPS

# 3. Todo caminho preenche Information com sizeof(resposta)
Select-String km_core.c -Pattern "IoStatus.Information"

# 4. Nenhum estado global mutável
Select-String km_core.c -Pattern "^static .*="
# esperado: só constantes/ponteiros imutáveis; contadores na device extension

# 5. Códigos de IOCTL estáveis (golden table)
python tools\ctl_codes.py --expect 0x0022E000,0x0022E004,0x0022E008
```

### 9.2 No binário (depois de compilar — fora desta fase)

```powershell
dumpbin /imports km_rw.sys     # só ntoskrnl; nenhuma API não documentada
dumpbin /headers km_rw.sys     # Subsystem Native; DACL não aparece aqui
dumpbin /exports km_rw.sys     # nenhuma exportação
```

- **Code Analysis (PREfast)** `/analyze` no build; zero warnings de C6001/C6014.
- **Driver Verifier** na VM: Standard, IRQL, Pool, Handle, `Special Pool`.
  Qualquer `IRQL_NOT_LESS_OR_EQUAL` ou pool corruption reprova.
- **ACL:** `sc sdshow KmRwCtl` e `!object \Device\KmRwCtl` devem mostrar
  `D:P(A;;GA;;;SY)(A;;GA;;;BA)`.
- **Ciclo de vida:** `sc stop` com handle aberto deve falhar com
  `STATUS_DEVICE_BUSY`; `!irp` não deve mostrar IRPs pendentes no unload.
- **Fuzz de IOCTL (VM):** matriz `inLen ∈ {0, 0xF, 0x10, 0x11, 0x1000, 0x10000}` ×
  `outLen ∈ {0, 0xF, 0x10, 0x1000}` × `AbiVersion ∈ {0,1,2}` × códigos válidos e
  inválidos. Critério: sempre um NTSTATUS, nunca crash; `Information` nunca >
  `outLen`.
- **Reentrância:** N threads no mesmo handle fazendo `GET_STATE`; contador
  consistente e sem crash.

### 9.3 Específicos de 0001/0002 (se forem mantidos)

- Um teste que **prove** a invariante "um cliente": segundo `NtOpenSection` +
  mapeamento não pode coexistir com um pedido em voo (hoje não há mecanismo; o
  teste deve falhar e expor R7).
- Teste de timeout: injetar atraso > 5 s no kernel e verificar que o retry **não**
  aceita a conclusão antiga (hoje falha — R8).

---

## 10. Conclusão e recomendação

1. **Arquitetura:** adotar o esqueleto do `0003`, **sem** a camada de dados na v1.
   É o único desenho com isolamento por requisição (resolve R7), ciclo de vida
   real (R11) e sem estado global.
2. **Antes de qualquer build do 0003:** R1 (teto de `inLen`/`outLen`), R3 (versão
   na ABI), R4 (SDDL explícito), R5 (`DesiredAccess`), R2 (cópia do cabeçalho).
3. **`0001`/`0002`:** continuam sendo o remendo correto do desenho antigo; se o
   caminho de seção for aposentado, não vale investir neles. Se for mantido,
   `RequestId`/`CompletionId` e a invariante de cliente único são obrigatórios.
4. **A camada de R/W não deve entrar na v1.** É a decisão de arquitetura desta
   revisão: ela concentra 100% das APIs não documentadas, 100% dos riscos de
   memória e é a capacidade que define o perfil de detecção do driver.
5. **Nada foi alterado.** Os quatro diffs seguem exatamente como estavam; os
   hashes da §0 foram reverificados na leitura. Aguardo aprovação para qualquer
   alteração — inclusive para transformar a §8 em um `0005`.
