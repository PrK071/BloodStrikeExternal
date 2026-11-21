# Kernel driver — post-mortem e ponto de retomada

Registro do processo de tentar levar o transporte de memória do cheat para
nível kernel (Ring 0), por que não vingou nesta máquina, e o que ficou no
lugar. Serve pra retomar o assunto no futuro sem repetir os mesmos erros.

## Objetivo

O leitor de memória original (`win32_memory.py`) usa `OpenProcess` +
`ReadProcessMemory`, que um anticheat user-mode consegue detectar (hook de API
e, principalmente, enumeração de handle). A meta era ler/escrever a memória do
jogo **sem handle de processo**, via driver de kernel carregado/mapado.

## Ambiente / toolchain

Instalado nesta máquina (Windows 11):

- Visual Studio Build Tools 2022 (workload C++, MSVC 14.44.35207)
- Windows SDK + Windows Driver Kit 10.0.22621

Tudo redirecionado pro drive `E:` porque o `C:` tinha pouco espaço:

- MSVC: `E:\VSBuildTools`
- SDK/WDK: `E:\Windows Kits\10`

O `build.bat` do driver usa `INCLUDE`/`LIB` apontando pra esses caminhos. Dois
detalhes que custaram tempo:

- `CL` e `LINK` são variáveis de ambiente reservadas do cl.exe/link.exe. Usar
  esses nomes pra guardar o caminho do executável faz o próprio compilador
  receber o caminho dele como arquivo-fonte. Use `CLC`/`LINKER` como nome.
- O WDK via winget não instala o SDK `shared` (falta `ntdef.h`). É preciso
  instalar o Windows SDK separado (`Microsoft.WindowsSDK.10.0.22621`) pra ter
  `Include\<ver>\shared`, `ucrt` e `um`.

## O driver (duas versões)

`km_rw.sys` foi escrito duas vezes:

1. **WDM com IOCTL** (`IoCreateDevice`/`IoCreateSymbolicLink` + `DeviceIoControl`).
   Funciona quando carregado pelo SCM (`sc start`). Ler/escrever via
   `MmCopyVirtualMemory`, base de módulo e image path via PEB.
2. **Mapeável (manual mapping)** — driver mapeado recebe `DriverObject`/`RegistryPath`
   nulos, então `IoCreateDevice` dá BSOD. A versão 2 comunica por **seção de
   memória compartilhada nomeada** (`\BaseNamedObjects\KmRwShared`) + thread de
   sistema que faz polling dos comandos (read/write/image_path).

## Tentativa 1 — test-signing (falhou)

Assinar o driver com certificado autoassinado e carregar via `sc start`, com
`bcdedit /set testsigning on`.

Passos seguidos:

- `makecert` com EKU de kernel (`1.3.6.1.4.1.311.61.1.1` + Code Signing)
- importado em `LocalMachine\Root` e `LocalMachine\TrustedPublisher`
- `signtool sign /fd sha256 /ph`
- `link /INTEGRITYCHECK` (PE tem o bit `FORCE_INTEGRITY`)
- Secure Boot desligado, `nointegritychecks on`

Resultado: **`sc start` sempre erro `577` / evento de Code Integrity 3004
"file hash could not be found on the system"**, mesmo com assinatura válida
(`signtool verify` OK), cert nos repositórios certos, EKU correta e Secure
Boot off. É uma incompatibilidade conhecida do CI do Windows 11 22H2+ com
certificado autoassinado manual. A solução real seria o fluxo de build do
Visual Studio, que assina com um "WDK Test Certificate" próprio — ou seja,
o problema é o certificado, não o driver.

## Tentativa 2 — kdmapper / BYOVD (BSOD)

kdmapper não tem release compilado; foi compilado do fonte (`TheCruZ/kdmapper`)
com o mesmo toolchain (C++17, `/MT`, `/ENTRY:wmainCRTStartup`, forced-include
com `winnt.h`/`winioctl.h`). Ele embute o `iqvw64e.sys` (Intel) e faz o mapeamento
manual do driver sem assinatura.

Problemas encontrados ao mapear o `km_rw.sys` mapeável:

1. **BSOD garantido (versão 1 da shared memory):** o driver mapeava a seção com
   `ZwMapViewOfSection(section, ZwCurrentProcess(), ...)`. Sob kdmapper, o
   `DriverEntry` roda no contexto do processo mapper (que sai logo depois), então
   a view caía no espaço user-mode dele; a thread de sistema lia um endereço
   inválido em Ring 0 → tela azul.
2. **Correção:** mapear a seção no **processo System (PID 4)** via
   `PsLookupProcessByProcessId` + `ObOpenObjectByPointer` + `ZwMapViewOfSection`,
   obtendo endereços de kernel válidos.
3. **Ainda assim BSOD** (4 no total, entre 13:51 e 14:01). Causa não fechada.
   Suspeitas restantes: ausência de seção `.reloc` no PE (o `link` não gerou
   relocations mesmo com `/DYNAMICBASE` `/FIXED:NO`) → referências absolutas
   erradas quando mapeado fora da base preferida; ou resolução de import/SSN
   do kdmapper com esse driver específico.
4. **`run_kdmapper.ps1` via UAC + `-Wait`** foi interrompido por reboot a cada
   BSOD, dificultando capturar a saída do mapper.

Conclusão: depurar driver mapeado por tentativa-e-erro na máquina real não é
viável. Cada tentativa = uma tela azul.

## Decisão: user-mode com syscall

Kernel abandonado nesta máquina. O cheat voltou pra user-mode com dois níveis
mais baixos que o `ReadProcessMemory` original:

- `ntll_memory.py` → **`NtProcessMemory`**: `NtOpenProcess` + `NtReadVirtualMemory`
  + `NtWriteVirtualMemory` chamados direto do ntdll. Pula o hook do kernel32.
- `syscall_memory.py` + `syscall.dll` → **`SyscallProcessMemory`**: instrução
  `syscall` crua (ADRs resolvidos em runtime lendo o stub do ntdll, então
  funciona em qualquer build). Pula o hook do kernel32 **e** do ntdll.

**Limite honesto:** os dois ainda abrem um handle no processo do jogo, e isso é
enumerável (`NtQuerySystemInformation`). O syscall esconde a *chamada*, não o
*handle*. Só o kernel esconderia o handle — por isso a tentativa acima.

## O leitor syscall (como funciona)

`syscall.dll` exporta `sc_open_process`, `sc_read`, `sc_write`, `sc_close`.
Internamente:

- `resolve_ssn("NtXxx")` lê o stub do ntdll (padrão `4C 8B D1 B8 <ssn>`) e
  extrai o System Service Number em runtime.
- `raw_syscall` monta um stub `mov r10, rcx; mov eax, <ssn>; syscall; ret` em
  memória `PAGE_EXECUTE_READWRITE` e chama com os 5 argumentos da convenção x64
  (o 5º vai pro stack em `[rsp+0x28]`).

Build: `km_cheat/syscall/build.bat` (fora do repo). O `.dll` compilado está em
`ExternalCore/syscall.dll`.

## Segurança — reverter

Enquanto testávamos kernel, ficaram ligados `testsigning` e `nointegritychecks`
(reduzem a proteção de driver do Windows). Foram revertidos:

```
bcdedit /set testsigning off
bcdedit /set nointegritychecks off
sc delete KmRw
```

+ reboot. Certificados `CN=KmRw Test` removidos dos repositórios.

## Como retomar o kernel depois

1. **Fazer em VM**, com WinDbg habilitado (kernel debugging), nunca na máquina
   principal.
2. Começar por um driver **mínimo** (só `DriverEntry` + `DbgPrint`) mapeado pelo
   kdmapper. Se carregar sem BSOD, adicionar a seção compartilhada depois.
3. Gerar a `.reloc` de verdade: conferir com `dumpbin /headers` que "Base
   Relocation Directory" não é `0 [0]`. Se for zero, investigar flags de link
   (`/FIXED:NO`, `/DYNAMICBASE`) ou usar um `.def`/base diferente.
4. Considerar o fluxo de assinatura do Visual Studio (WDK Test Certificate) em
   vez de `makecert` manual, que foi o que barrou o test-signing.
5. Alternativa mais robusta que kdmapper: usar um driver vulnerável que exponha
   read/write de memória **virtual por PID** direto (evita o page-table walk e
   reduz pontos de falha).

## Arquivos relevantes

- `ExternalCore/win32_memory.py` — leitor kernel32 original (baseline).
- `ExternalCore/ntll_memory.py` — leitor ntdll direto.
- `ExternalCore/syscall_memory.py` — leitor via `syscall.dll`.
- `ExternalCore/syscall.dll` — stubs de syscall (compilado).
- `ExternalCore/km_memory.py` — leitor do driver kernel (não usado; ficou de
  registro da arquitetura de seção compartilhada).
- Fora do repo (`C:\Users\luiz\km_cheat\`): `km_rw/` (fonte + `build.bat` do
  driver), `kdmapper/` (fonte compilado), `syscall/` (fonte + build do DLL).
