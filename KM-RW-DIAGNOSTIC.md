# Diagnóstico — `km_rw.sys` e os BSODs

Análise estática aprofundada. Nenhum carregamento, mapper, BYOVD ou alteração de
binário/código foi executado. Apenas leitura (`dumpbin`, Event Viewer, fontes).

> **Fase seguinte:** `DriverEntry` e gerenciamento de memória auditados em
> [`KM-RW-DRIVERENTRY-REVIEW.md`](KM-RW-DRIVERENTRY-REVIEW.md) (causa raiz,
> tabela de operações de memória e correção da semântica dos parâmetros do `0x1E`).
> O item "causa provável" da §6 foi atualizado por causa daquela revisão.

## 0. Escopo e artefatos analisados (hashes SHA-256)

| Arquivo | SHA-256 |
|---|---|
| `km_rw.sys` | `83F53EA9B6F2B00F1D210D507022BFD35D6EDF9FF6481A95FD16E1DCDF438A5B` |
| `km_rw.c`   | `651FC5106E1B7D3FB351CADAE4321C0343A6E224D93281C3BA0911DC727460A2` |
| `km_rw.obj` | `4E2402FA9686164263186CD523A390DDF59396DF9FC0EA8190493CD3B49CDFB6` |
| `build.bat` | `E66BA20AF321841126F0D587EA51CBF17F3F60E7EDB928F50FA5C01A46C86430` |

Backup: `C:\Users\luiz\km_cheat_backup\20261122_172616\`.
`.sys` compilado em `Sat Nov 21 14:05:03 2026` (time date stamp `0x6B01CF3F`).

---

## 1. Resumo executivo

- O `km_rw.sys` é um driver WDM x64, **imagem position-independent** (sem `.reloc`
  necessário), com `DYNAMIC_BASE` ligado, 15 símbolos de `ntoskrnl.exe` — 14 funções
  e **1 de dado** (`PsProcessType`). Compilado com MSVC 14.44 (v143) + WDK 10.0.22621.
- Os BSODs foram **4× `0x0000001E` (KMODE_EXCEPTION_NOT_HANDLED) com `0xC0000005`
  (access violation) + 1× `0x0000001A` (MEMORY_MANAGEMENT)** — crashes de kernel com
  violação de acesso e corrupção de memória.
- **A ausência de `.reloc` NÃO é, por si só, a causa.** A imagem é position-independent,
  o que é válido tanto para carga convencional quanto para mapeamento. Trocar essa
  conclusão pelo contrário seria erro de análise.
- A causa provável mais consistente com a evidência é a **interação do runtime do
  driver (mapeamento de seção no processo System + thread de sistema) com o caminho
  de manual mapping** — não a estrutura PE, nem os imports, nem a compilação.
  Confiança: **média** na classe; **baixa/média** no ponto exato (falta dump).

---

## 2. Estrutura PE (`dumpbin /headers`)

| Campo | Valor |
|---|---|
| Machine | `0x8664` (x64), 5 seções |
| ImageBase | `0x140000000` |
| AddressOfEntryPoint | `0x1000` (RVA) → `0x140001000` |
| SizeOfImage | `0x6000` |
| SectionAlignment / FileAlignment | `0x1000` / `0x200` |
| Subsystem | `1` (Native) |
| **DllCharacteristics** | `0x1E0` |
| **Base Relocation Directory** | **RVA `0`, size `0`** (sem `.reloc`) |
| Checksum | `0x0000C4E6` (válido, não-zero) |

`DllCharacteristics = 0x1E0` = `FORCE_INTEGRITY(0x80)` | `DYNAMIC_BASE(0x40)` |
`NX_COMPAT(0x100)` | `HIGH_ENTROPY_VA(0x20)`.

Seções:

| Seção | VA | Virtual size | Permissões | Observação |
|---|---|---|---|---|
| `.text` | `0x1000` | `0xA00` | R-X | código |
| `.rdata` | `0x2000` | `0x3C0` | R-- | IAT + strings |
| `.data` | `0x3000` | `0x18` | RW- | globais `g_shared`, `g_data` |
| `.pdata` | `0x4000` | `0x6C` | R-- | unwind (RVA-based) |
| `INIT` | `0x5000` | `0x1FA` | RW- discardable | `DriverEntry` |

### 2.1 O que a ausência de `.reloc` significa (e o que NÃO significa)

**Significa:** o linker não encontrou **nenhuma** referência que precise de base
relocation. O código x64 usa **RIP-relative** para globais/IAT; `.pdata` usa RVAs
(não VAs absolutas); a IAT é preenchida pelo loader. Resultado: imagem
**auto-suficiente em qualquer base** — por isso `DYNAMIC_BASE` está ligado e mesmo
assim não há `.reloc` (se houvesse relocs, haveria seção). É um **estado válido**, não
um defeito.

**Consequências reais para o carregamento:**
- **Carga convencional:** o loader pode carregar na base preferida `0x140000000`.
  Como não há `.reloc`, ele **não consegue realocar** — se `0x140000000` estiver
  ocupada, a carga **falha** com `STATUS_CONFLICTING_ADDRESSES` (erro limpo, não BSOD).
- **Manual mapping:** sem relocs a aplicar, o mapper pode mapear em qualquer base; as
  referências RIP-relative continuam corretas.

**O que NÃO pode ser concluído:**
- ❌ "o BSOD foi porque faltou `.reloc`". A imagem é position-independent; a ausência
  é coerente. Nada na evidência liga a ausência de `.reloc` ao `0x1E`/`0x1A`.
- ❌ "o driver está quebrado por não ter `.reloc`". Não está; para a base preferida
  (carga normal) ele é carregável.
- ⚠️ A única ressalva legítima: sem `.reloc`, **carga convencional em base diferente
  falha** (não corrompe). Isso é comportamento esperado, não bug.

---

## 3. Inventário de imports (`dumpbin /imports`)

Todos de **`ntoskrnl.exe`** (nenhuma outra dependência de DLL; sem libs de terceiros).

**Funções (14):**
`RtlInitUnicodeString`, `KeDelayExecutionThread`, `ExAllocatePoolWithTag`,
`ExFreePoolWithTag`, `PsCreateSystemThread`, `IoGetCurrentProcess`,
`ObfDereferenceObject`, `ZwClose`, `ZwCreateSection`, `ZwMapViewOfSection`,
`PsLookupProcessByProcessId`, `ObOpenObjectByPointer`, `MmCopyVirtualMemory`,
`PsGetProcessPeb`.

**Dado (1):** `PsProcessType`.

**Resolvidos pelo kernel:** todos acima são exports do `ntoskrnl` (funções e o dado).

**Dependências adicionais:** nenhuma. Sem CRT, sem `Wdf`, sem outro `.sys`.

### 3.1 Análise de `PsProcessType`

- É um **export de dado** (`POBJECT_TYPE`/`POBJECT_TYPE*`, conforme a versão do header),
  consumido em `ObOpenObjectByPointer(..., *PsProcessType, ...)`.
- O manual mapping do kdmapper resolve imports pelo **export table**
  (`portable_executable.cpp` lê `IMAGE_DIRECTORY_ENTRY_IMPORT`;
  `intel_driver.cpp:GetKernelModuleExport` percorre `AddressOfNames`/`AddressOfFunctions`).
  O export table cobre funções **e** dados — logo `PsProcessType` **tende a ser
  resolvido** nesse caminho. **Não há evidência, no código ou no log, de resolução
  falha.**
- **Como uma referência inválida explicaria um `0xC0000005`:** se o slot de IAT de
  `PsProcessType` ficasse `0`/lixo (loader que só resolve *funções*, ex.
  `MmGetSystemRoutineAddress`), `ObOpenObjectByPointer` desreferenciaria um
  `ObjectType` inválido → violação de acesso em Ring 0 → `0x1E`/`0xC0000005`. É um
  mecanismo **plausível**, porém **não confirmado** aqui (o kdmapper não usa esse
  caminho, e não há dump para provar onde o acesso falhou).

**Decisão:** **não** substituo `PsProcessType` por `ZwOpenProcess`. A análise não
demonstra que essa troca seja necessária — além de `ObOpenObjectByPointer` **evitar**
o access-check que o `ZwOpenProcess` faria no processo System. Trocar seria especulação
e possivelmente regressão.

---

## 4. Investigação dos BSODs

### 4.1 Fatos confirmados (do Event Log)
- Janela 13:40–14:02 de 21/11/2026: **5 ciclos** de `Kernel-Boot` seguidos de
  `Kernel-Power 41` (crítico) e `WER 1001` (erro).
- Stop codes (WER 1001):
  - **5× `0x0000001E`** com Arg1 `0xFFFFFFFFC0000005` (STATUS_ACCESS_VIOLATION).
    Para `0x1E`, Arg2 é o **endereço da instrução** (não o endereço acessado),
    Arg3 é `ExceptionInformation[0]` (**0 = leitura, 1 = escrita**) e Arg4 é o
    **endereço virtual acessado**. Os cinco Arg4 são VAs **user-mode**, todos
    múltiplos de 64 KB: `0x1F6F5FC0000`, `0x16DE55A0000`, `0x21E77730000`,
    `0x17AF38E0000`, `0x1CA71FA0000` (3 leituras + 2 escritas).
  - **1× `0x0000001A`** (`0x3F`, `0xEA1DB`, `0x27F7AE28`, `0x1AABD40A`) —
    MEMORY_MANAGEMENT, em **19/11** (dois dias antes, outro estágio do projeto).

> **Correção:** a versão anterior deste documento chamou Arg2 de "endereço" do
> acesso. Arg2 é a instrução; o endereço acessado é Arg4. A análise completa da
> semântica, do alinhamento dos cinco endereços e da atribuição crash→build está em
> [`KM-RW-DRIVERENTRY-REVIEW.md`](KM-RW-DRIVERENTRY-REVIEW.md) §6.
- **Dumps ausentes:** `C:\Windows\Minidump` vazio e `C:\Windows\MEMORY.DMP` inexistente
  (embora citados nos eventos). **Sem stack trace disponível.** WinDbg não instalado.

### 4.2 Hipóteses plausíveis (não confirmadas)
1. **Interação runtime × mapper:** `DriverEntry` mapeia uma seção nomeada no processo
   System e cria uma thread de sistema; sob o contexto do mapper isso pode produzir
   corrupção/`0x1A`, e a thread pode tocar memória inválida (`0x1E`).
2. **Bug no shellcode/mapeamento do kdmapper** (o `0x1A` — MEMORY_MANAGEMENT — sugere
   corrupção que pode estar no mapeador, não no driver).
3. **Import de dado não resolvido** (`PsProcessType`) → `0xC0000005` — mecanicamente
   possível, sem evidência.
4. **`RtlZeroMemory(view, 4 MB)`** se a view mapeada for menor que 4 MB → escrita além
   da view → violação de acesso.

### 4.3 Conclusões que dependem de dump (indisponível)
- A instrução/endereço exato que falhou, o módulo responsável no frame, e a stack.
- Se o crash ocorreu dentro do código do driver (`.text`) ou no shellcode do mapper.
- A natureza exata da corrupção no `0x1A` (pool vs tabela de páginas).

**Não atribuo responsabilidade definitiva ao driver nem ao mapper.** A evidência atual
só permite afirmar a **classe** (violação de acesso em kernel + corrupção de memória),
não o **ponto**.

---

## 5. Configuração de compilação

| Item | Valor | Adequação |
|---|---|---|
| Toolset | MSVC 14.44.35207 → forçado `v143` (projeto original `v145`, Taigei `v142`) | para driver kernel, forçar v143 via `/p:PlatformToolset=v143` é aceitável; o WDK 22621 assina esse toolset |
| WDK/SDK | 10.0.22621 (Include/Lib/km x64) | ok para WDM x64 |
| Arquitetura | x64 (`machine 0x8664`) | ok |
| Configuração | Release (`/O2 /GS-`) | ok |
| Linker | `/SUBSYSTEM:NATIVE /DRIVER /INTEGRITYCHECK /DYNAMICBASE /ENTRY:DriverEntry` | **apropriado** para driver carregado pelo mecanismo convencional |
| Relocations | `DYNAMICBASE` ligado, **sem `.reloc`** (zero relocs reais) | coerente (imagem position-independent); não é omissão |
| Libs | `ntoskrnl.lib`, `ntstrsafe.lib` | ok |

**Veredito da compilação:** a configuração é **adequada** para um driver de kernel
carregado pelo loader convencional. O `DYNAMIC_BASE` + `INTEGRITYCHECK` + `NATIVE`
estão corretos. Não há evidência de `Machine`/`Subsystem`/CRT/`/FIXED` conflitante.
Logo, **a compilação não é a causa provável.**

---

## 6. Causa provável (com confiança)

| Hipótese | Confiança | Justificativa |
|---|---|---|
| Estrutura PE quebrada (`.reloc`) | **descartada** | imagem position-independent; `.reloc` ausente é válido |
| Imports (incl. `PsProcessType`) | **descartada** | 15/15 exports confirmados no `ntoskrnl` 19045; `PsProcessType` é dado em `ALMOSTRO`; kdmapper/KDU resolvem por export table |
| Compilação | **baixa** | flags corretas para driver convencional |
| **Acesso a VA user-mode de outro processo no contexto errado (`RtlZeroMemory`/thread)** | **alta** | Arg4 dos 5 `0x1E` são VAs user 64 KB-alinhados; as duas únicas referências a `view+0` produzem exatamente os padrões 3 leituras + 2 escritas observados |

**Conclusão principal:** o problema **não está** na estrutura PE, nos imports nem na
compilação. É o **modelo de memória** do driver: ele guarda e usa um VA **user-mode do
processo System (PID 4)** e o desreferencia de um contexto cujo espaço de
endereçamento não o contém (kdmapper executa `DriverEntry` na thread do processo do
kdmapper). Análise completa, incluindo por que o KDU não sofre disso no entry:
[`KM-RW-DRIVERENTRY-REVIEW.md`](KM-RW-DRIVERENTRY-REVIEW.md).

> Ressalva temporal: o `.sys` analisado foi linkado às **14:05:03**, depois do último
> crash (**14:02:03**). Ele nunca foi executado. A conclusão é *por construção*, não
> laudo do binário que crashou.

---

## 7. Informações ainda necessárias para confirmar

1. **Dump do crash** (`MEMORY.DMP`/`Minidump`) → `!analyze -v` no WinDbg: stop code,
   módulo, stack, instrução.
2. **Carga convencional (test-signing) do MESMO `.sys`** numa VM: reproduz `0x1E`?
   - Se **não** reproduz → confirma que era o contexto do mapeamento, não o driver.
   - Se **reproduz** → é bug de runtime do driver (aí sim analisar seção/thread).
3. **Mapeamento com um driver trivial known-good** (ex. DummyDrv do KDU) para validar
   o loader isoladamente.
4. Se o mapa no PID 4 **sucede** nesta build (não testado) e se o DACL da seção
   permite `NtOpenSection` por cliente não elevado.

---

## 8. Próximas etapas seguras (sem tocar o Windows principal, sem admin ainda)

1. Revisão do `DriverEntry`/gerenciamento de memória: **feita** —
   [`KM-RW-DRIVERENTRY-REVIEW.md`](KM-RW-DRIVERENTRY-REVIEW.md). O `RtlZeroMemory`
   **não** estoura o tamanho da view; ele acessa um VA que não existe no contexto do
   loader. Achados independentes: `Size` sem limite (overflow real de até 12 MB) e
   corrida de protocolo.
2. Preparar (quando autorizado) VM limpa + snapshot + WinDbg e repetir a carga
   **convencional** de um driver de exemplo **assinado** primeiro.
3. Só então decidir sobre o `km_rw.sys` no ambiente isolado.

> Nada foi alterado em código/binário nesta fase; backup preservado; hashes acima.
