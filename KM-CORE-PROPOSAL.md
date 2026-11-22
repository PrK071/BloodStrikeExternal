# Proposta 0005 — `km_core`: driver mínimo de consulta (device/IOCTL)

Proposta independente dos diffs 0001-0004, que permanecem intactos. Nada foi
aplicado, compilado, executado ou instalado **na data desta proposta**.

> **Status posterior:** o 0005 foi aprovado e aplicado; o driver foi compilado e
> auditado estaticamente (sem carga em kernel). O desenho abaixo continua sendo
> a referência. O build efetivamente verificado está no adendo da §6.1; a
> validação de runtime continua pendente em `KM-CORE-VM-TEST-MATRIX.md`.

> **Aviso de escopo:** `km_core` não abre processos, não lê nem escreve memória de
> outro processo, não cria seção compartilhada, não cria thread de sistema e não
> usa mapper. Ele responde a três consultas de tamanho fixo. Não há o que
> "ampliar" depois sem uma decisão separada.

| Item | SHA-256 |
|---|---|
| `proposals/0005-km-core-driver.diff` | `DBB6E8B5B23EFB94DCA4DD83F5648EB0E97FA7C07DF1C993A46A526F4FD9BF28` |
| `proposals/0005-km-core-client.diff` | `5B220D9306666FA4F17B8BEAF3DF9B41D81E8AE087B8F649B64A488C24ED968D` |
| `km_core/km_core.c` (conteúdo do patch) | `99C031ADF33DA425A5DDA4541AA34EAFFB1EE13A513F3CD9211CF20650C1A18B` |
| `tools/km_core_client.py` (conteúdo do patch) | `16E0A0C4F5900B5860A7950EAF134C5ABE719C7DE4907C4CAE62FF5EFA5C15D0` |

Base para aplicar: driver em `C:\Users\luiz\km_cheat\`; cliente na raiz do repo.
Ambos são `new file` diffs — não tocam 0001-0004.

---

## 1. Arquitetura

### 1.1 Fluxo de uma requisição

```
Python (tools/km_core_client.py)
  CreateFileW(\\.\KmCore, FILE_READ_DATA)
        │
        ▼
I/O manager: aloca SystemBuffer = max(in, out)   [METHOD_BUFFERED]
        │  copia a entrada do usuário
        ▼
km_core!KmDeviceControl          (PASSIVE_LEVEL, contexto do chamador)
  1. conta a requisição            (InterlockedIncrement64)
  2. valida o código do IOCTL      (senão STATUS_INVALID_DEVICE_REQUEST)
  3. valida tamanhos + ABI         (senão STATUS_*; nada é copiado)
  4. escreve a resposta de 0x10 B
  5. Information = 0x10
        │  IoCompleteRequest
        ▼
I/O manager: copia 0x10 B de volta; DeviceIoControl devolve
```

Não existe estado de uma requisição para a próxima, nem mailbox, nem latch, nem
buffer entre clientes. O único dado mutável é o contador por device.

### 1.2 Estrutura de arquivos

```
C:\Users\luiz\km_cheat\
└─ km_core\
   └─ km_core.c                     (novo, 368 linhas)  — driver

Documents\BloodStrikeExternal\
└─ tools\
   └─ km_core_client.py             (novo, 230 linhas)  — cliente
```

Não incluí `build.bat`/`.vcxproj`: o comando de build está na §6. Se quiser, vira
um `0006` separado.

### 1.3 O que o driver não faz

Sem `PsLookupProcessByProcessId`, sem `MmCopyVirtualMemory`, sem
`MmMapViewInSystemSpace`, sem `ZwCreateSection`, sem `PsCreateSystemThread`, sem
`PsProcessType`, sem `ObOpenObjectByPointer`. A verificação da §7.1 confirma zero
ocorrências no fonte.

---

## 2. ABI v1

### 2.1 Estruturas (todas 0x10 bytes, sem ponteiro, sem campo variável)

| Struct | Offset 0x00 | 0x04 | 0x08 | 0x0C |
|---|---|---|---|---|
| `KM_QUERY` (entrada) | `AbiVersion` | `StructSize` | `Command` | `Reserved` |
| `KM_VERSION` (saída) | `AbiVersion` | `StructSize` | `DriverVersion` | `BuildNumber` |
| `KM_STATE` (saída) | `State` | `UptimeSeconds` | `RequestsServed` (u64) | — |
| `KM_CAPS` (saída) | `StructSize` | `CapabilityMask` | `MaxRequest` | `Reserved` |

`KM_STATE` tem `ULONG64` no offset 0x08: alinhamento natural 8, sem padding
implícito, tamanho 0x10. Os `C_ASSERT` (linhas 95-103) travam tamanho e offsets.

### 2.2 IOCTLs

| Nome | Código | Entrada | Saída |
|---|---|---|---|
| `IOCTL_KM_GET_VERSION` | `0x00226000` | `KM_QUERY` (0x10) | `KM_VERSION` (0x10) |
| `IOCTL_KM_GET_STATE` | `0x00226004` | `KM_QUERY` (0x10) | `KM_STATE` (0x10) |
| `IOCTL_KM_GET_CAPS` | `0x00226008` | `KM_QUERY` (0x10) | `KM_CAPS` (0x10) |

`CTL_CODE(FILE_DEVICE_UNKNOWN=0x22, 0x800+n, METHOD_BUFFERED, FILE_READ_DATA)`.
Os três valores foram conferidos por recálculo independente (§7.1).

`CapabilityMask` v1 = `0x7` (get_version | get_state | get_caps).
`MaxRequest` = `0` (não há canal de dados).

### 2.3 Regras de validação, em ordem

| # | Condição | Status | Linha |
|---|---|---|---|
| 0 | código desconhecido | `STATUS_INVALID_DEVICE_REQUEST` | 232-237 |
| 1 | `inLen < 0x10` | `STATUS_BUFFER_TOO_SMALL` | 146 |
| 2 | `SystemBuffer == NULL` | `STATUS_INVALID_PARAMETER` | 149 |
| 3 | `inLen != 0x10` | `STATUS_INVALID_PARAMETER` | 152 |
| 4 | `outLen < 0x10` | `STATUS_BUFFER_TOO_SMALL` | 155 |
| 5 | `AbiVersion != 1` | `STATUS_REVISION_MISMATCH` | 160 |
| 6 | `StructSize != 0x10` | `STATUS_INVALID_PARAMETER` | 163 |
| 7 | `Command != IoControlCode` | `STATUS_INVALID_PARAMETER` | 166 |
| 8 | tudo ok | `STATUS_SUCCESS`, `Information = 0x10` | 284 |

A ordem é determinística: um `inLen = 0` falha sempre na regra 1, com ou sem
buffer alocado pelo I/O manager. `Reserved` não é validado (documentado como
"deve ser 0"), para permitir uso futuro sem quebrar clientes antigos.

---

## 3. Driver — decisões e justificativas

### 3.1 Device e permissões

```c
status = IoCreateDeviceSecure(DriverObject, sizeof(KM_DEVICE_EXTENSION),
                              &deviceName, FILE_DEVICE_UNKNOWN,
                              FILE_DEVICE_SECURE_OPEN, TRUE, &sddl,
                              &KM_DEVICE_CLASS_GUID, &deviceObject);
```

- **`IoCreateDeviceSecure`** é a API documentada para device legado com DACL
  explícita. O próprio `wdmsec.h` (linhas 365-377) diz que serve para "raw PnP
  PDOs e **legacy device objects**" e alerta para não usar em FDO de pilha PnP —
  que não é o nosso caso. `wdmsec.lib` existe no kit 22621 e exporta o símbolo
  (`IoCreateDeviceSecure` é `#define` para `WdmlibIoCreateDeviceSecure`).
- **SDDL** `D:P(A;;GA;;;SY)(A;;GA;;;BA)`: DACL protegida (`P`, sem herança),
  `GENERIC_ALL` só para SYSTEM e Built-in Administrators. Nenhum usuário comum.
- **`FILE_DEVICE_SECURE_OPEN`**: o descritor é aplicado a **todo** open por nome,
  não só ao primeiro.
- **`Exclusive = TRUE`**: um handle por vez. Fecha a porta para múltiplos
  clientes e torna o ciclo de vida trivial; como efeito colateral, um cliente
  pode segurar o device e bloquear outro (DoS entre elevados).
- **GUID privado**: permite ao administrador apertar a política pela chave de
  classe, sem recompilar.
- Nome fixo (`\Device\KmCore`, `\DosDevices\KmCore`) é enumerável — decisão
  consciente: não há requisito de ocultação e o escopo do 0005 é demonstrar
  comunicação convencional.

### 3.2 Inicialização e janela de exposição

`IoCreateDeviceSecure` cria o objeto com `DO_DEVICE_INITIALIZING`. O device é
inicializado (campos do extension), o symlink é criado, os `MajorFunction` são
preenchidos e **só então** a flag é limpa (linha 365). Enquanto a flag está
ligada o device não pode ser aberto, então não existe janela em que um cliente
veja o extension zerado.

### 3.3 `IRP_MJ_CREATE`

Exige `FILE_READ_DATA` no `DesiredAccess` (linhas 187-188). `SecurityContext`
nulo (abertura iniciada pelo kernel) é aceito. O cliente abre exatamente com
`FILE_READ_DATA`, então não há dependência de mapeamento de `GENERIC_READ`.

### 3.4 `IRP_MJ_DEVICE_CONTROL`

- Um `switch` decide o tamanho da resposta **antes** de ler o buffer, e um
  segundo `switch` escreve. Não há `goto` para dentro de escopo com VLA (não há
  VLA).
- A resposta é escrita em `Irp->AssociatedIrp.SystemBuffer`, que com
  `METHOD_BUFFERED` é o destino correto; `Information = 0x10`.
- Todo caminho termina em `IoCompleteRequest` com `IO_NO_INCREMENT`; nenhum IRP
  fica pendente, então **não existe rotina de cancelamento** a implementar. Uma
  thread cancelada durante `DeviceIoControl` só espera a conclusão — a operação é
  curta e não bloqueia em I/O.
- `IRP_MJ_CLEANUP` e `IRP_MJ_CLOSE` completam com sucesso e não têm estado a
  limpar (não há objeto por handle).

### 3.5 Estado mutável e sincronização

O único dado mutável é `RequestsServed` (contador de 64 bits no device
extension):

- incremento: `InterlockedIncrement64` (linha 230);
- leitura: `InterlockedCompareExchange64(&v, 0, 0)` (linha 264), que é uma
  leitura atômica de 64 bits alinhados.

Justificativa: `GET_STATE` pode ser chamado concorrentemente por várias threads
no mesmo handle; sem operação atômica haveria *tearing* em 32 bits (x86) e
contagem perdida. Em x64 a leitura alinhada já seria atômica, mas o incremento
nunca é — daí `Interlocked` nos dois lados, por simetria e portabilidade. Não há
lock porque não há invariante entre campos: cada requisição é independente.

`StartInterruptTime` e `State` são write-once antes da exposição (§3.2) e
read-only depois; nenhuma sincronização é necessária.

**Nuance documentada:** `KeQueryInterruptTime()` é tempo de *interrupção*
(avança acordado, não durante suspensão). `UptimeSeconds` é, portanto, "segundos
acordado desde o `DriverEntry`", não tempo de parede.

### 3.6 Unload e liberação

```
IoCreateDeviceSecure falha  → return (nada alocado)
IoCreateSymbolicLink falha  → IoDeleteDevice (libera device + extension) → return
sucesso                     → KmUnload: IoDeleteSymbolicLink → IoDeleteDevice
```

Sem alocação própria (o extension vem do `IoCreateDeviceSecure`), sem dupla
liberação: o symlink só é criado depois do device e só é apagado no unload. O
`DriverObject->DeviceObject` é o próprio device (um só, `Exclusive`).

O SCM só chama `DriverUnload` quando não há handle aberto; se essa premissa
falhar, o unload competiria com um IRP em voo. É o **teste nº 1 da §7.2** (tentar
`sc stop` com handle aberto deve falhar com `STATUS_DEVICE_BUSY`).

---

## 4. Cliente

- Abre `\\.\KmCore` com `FILE_READ_DATA` e `OPEN_EXISTING` (linha 138).
- `_query` monta `KM_QUERY(AbiVersion=1, StructSize=0x10, Command=<código>, 0)`,
  chama `DeviceIoControl` com `out_len = sizeof(resposta)` e valida:
  `returned == sizeof(resposta)` e `resposta.StructSize == sizeof(resposta)`.
- `get_version` valida também `AbiVersion == 1` (defesa em profundidade: o driver
  já recusa versão diferente com `STATUS_REVISION_MISMATCH`).
- Erros de abertura/comunicação: `ctypes.WinError(GetLastError())`. Resposta
  inaceitável (curta ou com `StructSize` errado): `KmCoreError`.
- `close()` em `finally` via context manager; handle invalidado depois.
- Layout verificado no import com `if/raise` (não `assert`, que some com
  `python -O`).

Sem `read`, `write`, PID ou endereço — em nenhum ponto do arquivo.

---

## 5. Modelo de ameaça e permissões

| Superfície | Quem alcança | O que consegue |
|---|---|---|
| `\Device\KmCore` | SYSTEM, Administradores | três consultas |
| `\DosDevices\KmCore` | idem (SDDL do device) | idem |
| IOCTLs | handle com `FILE_READ_DATA` | idem |
| Usuário comum | nada | `STATUS_ACCESS_DENIED` no open |

A ACL não protege contra um processo **já elevado** — nada protege. O que ela
garante é que o driver **não cria superfície nova** para usuário comum, que é o
critério relevante para um driver de kernel. A capacidade exposta é
deliberadamente inútil para um atacante: versão, estado e capacidades.

---

## 6. Compatibilidade de compilação

Toolchain já usada pelo projeto (verificada nos headers, não no build):

| Item | Valor |
|---|---|
| Compilador | MSVC 14.44.x, toolset **v143** |
| SDK/WDK | 10.0.22621 (Include/Lib km, shared, ucrt, um) |
| Arquitetura | **x64** (usa `InterlockedIncrement64` e `ULONG64` alinhado) |
| Includes | `<ntifs.h>`, `<wdmsec.h>` |
| Libs | `ntoskrnl.lib`, `wdmsec.lib` |
| CRT | nenhum |

```
set INCLUDE=E:\VSBuildTools\VC\Tools\MSVC\14.44.35207\include;E:\Windows Kits\10\Include\10.0.22621.0\km;...\shared;...\ucrt;...\um
set LIB=E:\Windows Kits\10\Lib\10.0.22621.0\km\x64;E:\VSBuildTools\VC\Tools\MSVC\14.44.35207\lib\x64

cl /nologo /c /W4 /O2 /GS- /D_UNICODE /DUNICODE /D_AMD64_ /D_WIN64 /D_KERNEL_MODE ^
   /DNTDDI_VERSION=0x0A000006 /D_WIN32_WINNT=0x0A00 km_core.c

link /NOLOGO /SUBSYSTEM:NATIVE /DRIVER /FIXED:NO /DYNAMICBASE /INTEGRITYCHECK ^
   /ENTRY:DriverEntry /OUT:km_core.sys km_core.obj ntoskrnl.lib wdmsec.lib
```

Observações:

- `/GS-` vale só para a nossa translation unit (sem CRT). A `wdmsec.lib` é
  pré-compilada com `/GS`; por isso o link precisa de `BufferOverflowK.lib`
  (ver adendo §6.1). Num projeto MSBuild do WDK, deixe `/GS` ligado.
- `/INTEGRITYCHECK` mantém a postura de produção; para um teste assinado com
  test-signing na VM o bit não impede a carga. Pode ser removido num build
  descartável.
- **Assinatura:** o driver não é assinado. Em Windows normal ele **não carrega**.
  A validação exige VM descartável com `testsigning on` (ou assinatura real). Isto
  é limitação, não bug.
- `IoCreateDeviceSecure` é `_IRQL_requires_max_(PASSIVE_LEVEL)`; `DriverEntry`
  roda em PASSIVE.
- Carga: `sc create KmCore type= kernel binPath= \??\C:\...\km_core.sys` +
  `sc start KmCore`; descarga: `sc stop KmCore`.

### 6.1 Adendo — build verificado (posterior à proposta)

A linha de link acima foi a **primeira tentativa** e falhou: a `wdmsec.lib` é
instrumentada com `/GS` e referencia `__report_gsfailure`, o linker puxa o
runtime de GS *user-mode* (`LIBCMT.lib(gs_report.obj)`) e sobram 5 `LNK2019`
(`__imp_UnhandledExceptionFilter`, `__imp_TerminateProcess`, ...). A linha
verificada é:

```
cl /nologo /c /W4 /O2 /GS- /analyze /D_UNICODE /DUNICODE /D_AMD64_ /D_WIN64 ^
   /D_KERNEL_MODE /DNTDDI_VERSION=0x0A000006 /D_WIN32_WINNT=0x0A00 km_core.c

link /NOLOGO /SUBSYSTEM:NATIVE /DRIVER /FIXED:NO /DYNAMICBASE /INTEGRITYCHECK ^
   /ENTRY:DriverEntry /MAP:km_core.map /OUT:km_core.sys ^
   km_core.obj ntoskrnl.lib wdmsec.lib BufferOverflowK.lib
```

Resultado medido (host, sem instalar nem carregar):

- `cl` exit 0, `link` exit 0; `km_core.sys` com 18.944 bytes.
- Avisos: `C28023`×5 (anotação SAL), `C6014`×1 (falso positivo: o device é
  liberado em `KmUnload`) e 44 de SAL dos headers do WDK. Zero erros.
- PE: `machine 0x8664`, `subsystem Native`, entry RVA `0x1000` (`DriverEntry`),
  `DllCharacteristics 0x1E0`, relocations em `0x8000` (0x38 bytes), dependência
  única `ntoskrnl.exe`, sem exports.
- Imports: 35, todos documentados; nenhuma API interna. 5 são referências
  diretas do nosso `.obj`; 30 vêm de `wdmsec.lib`/`BufferOverflowK.lib`.
- Duas builds independentes: todas as seções byte-idênticas exceto o
  `TimeDateStamp` da entrada `IMAGE_DEBUG_TYPE_REPRO`; só timestamp/checksum
  diferem. **Conteúdo executável reprodutível; binário integral não.**
- **Não houve carga em kernel real.** Estes são resultados estáticos.

---

## 7. Testes estáticos

### 7.1 Executados agora (sem compilar, sem executar driver)

| # | Verificação | Resultado |
|---|---|---|
| 1 | `git apply --check` do driver em `C:\Users\luiz\km_cheat` | ok (exit 0) |
| 2 | `git apply --check` do cliente no repo | ok (exit 0) |
| 3 | Aplicar os dois em sandbox e comparar com o conteúdo pretendido | idêntico (só EOL, por `core.autocrlf`) |
| 4 | `ast.parse` do cliente | ok |
| 5 | Importar o cliente (executa `_check_layout`) | ok; `sizeof` 0x10 nas quatro structs |
| 6 | Offsets: `KM_QUERY.Command` 0x08, `KM_STATE.RequestsServed` 0x08, `KM_CAPS.CapabilityMask` 0x04 | ok |
| 7 | `CTL_CODE` do cliente × recálculo independente | `0x226000/4/8` em ambos |
| 8 | Varredura do fonte do driver: 11 APIs fora de escopo | **0 ocorrências** |
| 9 | Estado mutável no driver | só `RequestsServed` (extension) + `static const GUID` |
| 10 | `C_ASSERT` presentes | 9 |
| 11 | Símbolos nos headers: `IoCreateDeviceSecure` (`wdmsec.h:387`), `KeQueryInterruptTime` (`wdm.h:2841`, macro), `InterlockedIncrement64/CompareExchange64` (`wdm.h`), `STATUS_REVISION_MISMATCH` (`ntstatus.h:2871`), `FILE_DEVICE_SECURE_OPEN` (`wdm.h:7270`) | todos presentes |
| 12 | `wdmsec.lib` contém `IoCreateDeviceSecure`; `ntoskrnl.lib` contém `KeQueryInterruptTime` | ok |
| 13 | Fonte do driver 100% ASCII, LF | ok (368 linhas) |

**Isto não prova funcionamento.** Prova consistência de texto, ABI e escolha de
APIs. Nenhuma linha de código de máquina foi gerada.

### 7.2 A executar depois (build e VM)

> Item 1 foi executado posteriormente (ver §6.1): compila com `/W4 /analyze`,
> mas **não** com zero avisos — ver a lista no adendo. Os itens de VM seguem
> não executados.

1. Compilar com `/W4` e `/analyze` (PREfast) e revisar cada aviso; a expectativa
   de "zero warnings" não se confirmou (SAL dos headers + C28023/C6014).
2. `dumpbin /imports km_core.sys` → só `ntoskrnl.exe`; conferir que **não**
   aparece nenhuma das 11 APIs fora de escopo.
3. Assinar com certificado de teste; VM com `testsigning on` e snapshot.
4. `sc create`/`sc start`; `km_core_client.py` → três consultas ok.
5. **ACL:** `sc sdshow KmCore` e `!object \Device\KmCore` devem mostrar
   `D:P(A;;GA;;;SY)(A;;GA;;;BA)`.
6. **Unload:** `sc stop KmCore` com handle aberto deve falhar
   (`STATUS_DEVICE_BUSY`); com handle fechado deve descarregar sem IRP pendente
   (`!irp`, `!devobj`).
7. **Driver Verifier** (Standard, IRQL, Pool, Handle, Special Pool) durante 1-6.
8. **Fuzz de IOCTL** (matriz da §7.3): sempre NTSTATUS, nunca crash;
   `Information` nunca maior que `outLen`.
9. **Concorrência:** N threads no mesmo handle chamando `GET_STATE`; contador
   consistente, sem crash.

### 7.3 Matriz de rejeição (derivada por inspeção — não executada)

| `inLen` | `outLen` | `AbiVersion` | `StructSize` | `Command` | Resultado esperado |
|---|---|---|---|---|---|
| 0 | 0x10 | — | — | — | `STATUS_BUFFER_TOO_SMALL` (regra 1) |
| 0x08 | 0x10 | 1 | 0x10 | ok | `STATUS_BUFFER_TOO_SMALL` |
| 0x10 | 0x08 | 1 | 0x10 | ok | `STATUS_BUFFER_TOO_SMALL` (regra 4) |
| 0x18 | 0x10 | 1 | 0x10 | ok | `STATUS_INVALID_PARAMETER` (regra 3) |
| 0x10 | 0x10 | **2** | 0x10 | ok | `STATUS_REVISION_MISMATCH` (regra 5) |
| 0x10 | 0x10 | 1 | **0x20** | ok | `STATUS_INVALID_PARAMETER` (regra 6) |
| 0x10 | 0x10 | 1 | 0x10 | **errado** | `STATUS_INVALID_PARAMETER` (regra 7) |
| 0x10 | 0x10 | 1 | 0x10 | ok | `STATUS_SUCCESS`, `Information=0x10` |
| qualquer | qualquer | — | — | IOCTL inválido | `STATUS_INVALID_DEVICE_REQUEST` |

No cliente, os mesmos casos viram `WinError` com o código Win32 correspondente
(`ERROR_INSUFFICIENT_BUFFER` 122, `ERROR_INVALID_PARAMETER` 87,
`ERROR_REVISION_MISMATCH` 1306, `ERROR_INVALID_FUNCTION` 1).

### 7.4 Coerência cliente ↔ driver

| Constante | Driver | Cliente | Valor |
|---|---|---|---|
| ABI | `km_core.c:32` | `km_core_client.py:28` | `1` |
| Device type | `wdm.h` | `:30` | `0x22` |
| Método | `wdm.h` | `:31` | `0` |
| Acesso | `wdm.h` | `:32` | `0x1` |
| Funções | `:51-55` | `:55-57` | `0x800/0x801/0x802` |
| Códigos finais | — | — | `0x226000/4/8` |
| Layout | `:68-103` | `:67-112` | 0x10 / offsets da §2.1 |

Teste automatizável (sem driver): um script que extrai `#define` do `.c` e as
constantes do `.py` e compara os três códigos e os tamanhos. É o que a §7.1 já
fez de forma pontual; vale virar `tools/check_km_core_abi.py` se o 0005 for
aprovado.

### 7.5 Caminhos de falha e liberação

| Caminho | Libera | Dupla liberação? |
|---|---|---|
| `IoCreateDeviceSecure` falha | nada a liberar | não |
| `IoCreateSymbolicLink` falha | `IoDeleteDevice` (device + extension) | não |
| unload | `IoDeleteSymbolicLink` + `IoDeleteDevice` | não |

Sem alocação manual, sem handle, sem objeto de referência: não há o que vazar.
O único recurso "externo" é o symlink, criado uma vez e removido uma vez.

---

## 8. Riscos restantes

1. **Alocação do `METHOD_BUFFERED` acontece antes do driver.** Um cliente
   elevado pode pedir `outLen`/`inLen` grandes e forçar o I/O manager a alocar
   pool não paginado. O driver rejeita a requisição (regra 4/3), mas **não pode
   impedir a alocação**, que ocorre antes do dispatch. Mitigação real: ACL
   admin-only (já existe), cliente disciplinado e, se necessário, quota de job
   object no processo cliente. É limitação do mecanismo, não do código.
2. **`Exclusive = TRUE`** é também um vetor de DoS entre processos elevados.
3. **Premissa do unload** (§3.6) não verificada — teste nº 6 da §7.2.
4. **`DO_DEVICE_INITIALIZING`** como garantia de "não abre antes de inicializar"
   é o comportamento documentado da flag; confirmar no teste (tentar abrir
   durante o `DriverEntry` é impraticável; a garantia é por construção).
5. **Sem assinatura** → não carrega fora de test-signing.
6. **`UptimeSeconds`** é tempo acordado; não é tempo de parede.
7. **`RequestsServed`** conta também requisições inválidas (é o que chegou ao
   dispatch). Documentado; não é um contador de sucessos.
8. **`Reserved` (em `KM_QUERY` e `KM_CAPS`) não é validado** — por design, para
   permitir uso futuro sem quebrar clientes antigos. Hoje é ignorado e devolvido
   como 0.

---

## 9. Limitações conhecidas

- **Não compilado, não executado.** Nenhuma afirmação de funcionamento.
- Compatibilidade de compilação inferida de headers/libs, não de um build.
- Sem `build.bat`/`.vcxproj` (comando na §6).
- x64 apenas.
- Sem versionamento além de `AbiVersion == 1` (a política é rejeitar o que não
  seja exatamente 1).
- Sem `IRP_MJ_SHUTDOWN`/PnP (driver legado; o desligamento não descarrega
  drivers).
- Nenhuma funcionalidade além das três consultas.

---

## 10. Restrições cumpridas

- Nenhum arquivo original alterado; 0001-0004 intactos (hashes reconferidos).
- Nenhum diff aplicado.
- Nada compilado, executado ou instalado.
- Nenhum privilégio administrativo solicitado.
- Sem KDU, kdmapper, BYOVD ou manual mapping.
- Sem leitura/escrita de memória de processo, sem hooks, sem ocultação.
- Backup preservado (`km_cheat_backup\20261122_172616`).

Aguardo aprovação antes de aplicar qualquer alteração.
