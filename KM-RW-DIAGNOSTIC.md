# Diagnóstico — `km_rw.sys` e os BSODs

Relatório de engenharia: análise estática do driver, causa provável dos 4 BSODs,
e o que falta validar num ambiente isolado. Nada aqui foi executado na máquina
principal além de **leitura** (dumpbin, event log).

---

## 1. Inventário — o que foi compilado, instalado e validado

### Compilado
| Artefato | Caminho | Estado |
|---|---|---|
| `km_rw.sys` (WDM, 6 KB) | `C:\Users\luiz\km_cheat\km_rw\km_rw.sys` | compila; **nunca carregou com sucesso** |
| `syscall.dll` (leitor direct-syscall) | `C:\Users\luiz\km_cheat\syscall\syscall.dll` | compila; `export` ok; usado pelo cheat Python |
| `kdu.exe` + `drv64.dll` (loader) | `C:\Users\luiz\km_cheat\kdu\Source\...\Release\` | **compila** (toolset v143, paths UCRT injetados) |

Backup do estado: `C:\Users\luiz\km_cheat_backup\20261122_172616\` (km_rw, syscall, calibration.json, commit do repo, sha256 do `.sys`).

### Instalado (toolchain)
- VS Build Tools 2022 + MSVC 14.44.35207 (`E:\VSBuildTools`)
- Windows SDK + WDK 10.0.22621 (`E:\Windows Kits\10`)
- Python 3.12.10 (`AppData\Local\Programs\Python\Python312`) + `pefile` + `capstone`

### Validado
- **Cheat Python (user-mode/syscall): funciona** — `capture` leu 2 atores com
  posição decodificada; `watch` fez 30 frames, câmera fresh, ESP (3 draw commands).
- **Offsets da build nova (24c1ba6e): re-derivados e validados ao vivo** (globals,
  type descriptors, vtables, IEntity).
- **`km_rw.sys` NUNCA foi validado**: o caminho de manual mapping (kdmapper)
  resultou em BSOD; o caminho convencional (test-signing) falhou no host com 577.

---

## 2. Análise estática do `km_rw.sys`

### Imports (dumpbin /imports)
```
RtlInitUnicodeString      KeDelayExecutionThread     ExAllocatePoolWithTag
ExFreePoolWithTag         PsCreateSystemThread       IoGetCurrentProcess
ObfDereferenceObject      ZwClose                    ZwCreateSection
ZwMapViewOfSection        PsLookupProcessByProcessId ObOpenObjectByPointer
MmCopyVirtualMemory       PsGetProcessPeb            PsProcessType  <-- import de DADO
```
`PsProcessType` é um **import de dado** (não de função). Loaders de manual mapping
resolvem a IAT inteira; se por qualquer motivo esse símbolo de dado não for
resolvido, `*PsProcessType` vira lixo e o `ObOpenObjectByPointer` desreferencia
ponteiro inválido.

### Seções (dumpbin /headers)
```
.text .rdata .data .pdata INIT     — NENHUMA seção .reloc
Base Relocation Directory: 0 [0]
entry point: 0x140001000
```
**Não há `.reloc`**: o linker gerou imagem **posição-dependente** (`/FIXED`
implícito do `/DRIVER`). Todo endereço absoluto (tabela de exceção `.pdata`,
eventuais ponteiros em `.rdata`/`.data`) assume base `0x140000000`.

### Fluxo do `DriverEntry` (fonte `km_rw.c`)
1. `ZwCreateSection` — cria a seção nomeada `\BaseNamedObjects\KmRwShared`.
2. `PsLookupProcessByProcessId(4)` + `ObOpenObjectByPointer(*PsProcessType)` —
   abre handle do processo System.
3. `ZwMapViewOfSection(section, systemHandle, ...)` — mapeia a seção no espaço de kernel.
4. `RtlZeroMemory(view, 4 MB)`.
5. `PsCreateSystemThread(KmWorker)` — thread que faz polling de comandos.
6. Retorna `STATUS_SUCCESS`.

---

## 3. Os BSODs — evidência disponível

Os **dumps foram apagados** (`C:\Windows\Minidump` vazio, `MEMORY.DMP` ausente) —
não há como extrair stack trace. O que resta é o log de eventos:

| # | BugCheck | Arg1 (código) | Arg2 (endereço) | Interpretação |
|---|---|---|---|---|
| 1 | `0x0000001E` | `0xC0000005` | `0xFFFF8E86F23DC950` | KMODE_EXCEPTION_NOT_HANDLED — access violation |
| 2 | `0x0000001E` | `0xC0000005` | `0xFFFFD80FE3FE9950` | access violation |
| 3 | `0x0000001E` | `0xC0000005` | `0xFFFFC70CF8DD31E0` | access violation |
| 4 | `0x0000001E` | `0xC0000005` | `0xFFFF9F8A30FD91E0` | access violation |
| 5 | `0x0000001A` | `0x3F` | `0x0EA1DB` | MEMORY_MANAGEMENT |

### Causa provável (grau de confiança: alto para a classe, médio para o ponto exato)
`0x1E + 0xC0000005` é **violação de acesso em Ring 0**. O driver foi carregado por
**manual mapping** (kdmapper) num endereço **diferente de `0x140000000`**, e a
imagem **não tem `.reloc`**. Isso deixa referências absolutas (sobretudo `.pdata`
de unwinding, e possivelmente dados/`PsProcessType`) apontando para a base antiga.
O `0x1A` (MEMORY_MANAGEMENT) reforça corrupção de memória (seção/`.data`).

Em outras palavras: **a classe do crash é "ponteiro/endereço inválido em kernel",
consistente com imagem posição-dependente mapeada fora da base + import de dado**.
Não há evidência, nos dados disponíveis, de que seja bug de lógica do driver em
carga normal — mas isso **precisa ser provado em carga convencional** (o que ainda
não foi feito).

### O que NÃO foi feito (de propósito)
- **Não** alterei `PsProcessType → ZwOpenProcess`. A análise acima **não demonstra**
  necessidade dessa troca; ela apenas levanta a hipótese. Alterar sem prova seria
  chute.
- **Não** executei kdu/mapping nesta máquina.
- **Não** desativei nenhuma proteção.

---

## 4. Hipótese testável (a validar na VM)

Se o crash vem do **mapeamento manual** (`.reloc` ausente + base diferente +
import de dado), então **carregar o mesmo `.sys` pelo caminho convencional**
(test-signing, `sc start`, na base preferida `0x140000000`, com IAT resolvida pelo
OS) **não deve reproduzir o `0x1E`**.

Teste correto e não destrutivo (na VM, não no host):
1. VM Windows limpa + snapshot.
2. Ativar test-signing **na VM** (é descartável) e assinar o `.sys` com cert de teste.
3. `sc create` + `sc start` do `km_rw.sys` **sem** mapeamento.
4. Se subir sem BSOD → confirma que o problema era o mapeamento, não o driver.
5. Se der BSOD mesmo assim → aí é bug do driver; investigar com WinDbg (dump já configurado).

---

## 5. Bloqueio atual — precisa da tua autorização

O próximo passo exige **privilégio de administrador** (instalar VirtualBox; depois,
rodar o driver dentro da VM). Minha sessão está **sem elevação** agora.

Pelo teu critério ("se exigir alteração de segurança ou privilégio, pare e justifique"):

- **Justificativa:** instalar o VirtualBox e criar a VM é o único jeito de testar o
  driver **sem arriscar o Windows principal** (os 4 BSODs anteriores foram no host).
  É uma mudança de software, não de política de segurança do Windows; não desativo
  nada do host. O test-signing seria ativado **somente dentro da VM descartável**.
- **O que preciso:** (a) relançar o OpenCode como administrador; (b) um **ISO do
  Windows** (ou autorização pra eu baixar da Microsoft, ~5 GB).

Sem esses dois itens, paro aqui — e o relatório acima é o que dá pra afirmar com
evidência hoje.
