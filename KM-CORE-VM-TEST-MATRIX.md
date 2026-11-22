# KM-CORE — Matriz de testes de VM (G1, G2, T1–T12)

**Status: nenhum item executado.** Todos dependem de uma VM Windows 10 22H2 x64
(build 19045) que ainda não existe neste host (sem ISO e sem hipervisor
instalado). Nada aqui é aprovação: os testes de runtime só passam a valer depois
de executados, com evidência anexada.

## Classificação das evidências

| Tipo | O que prova | Onde aparece |
|---|---|---|
| **Estática** | consistência de fonte, ABI e binário; nada de runtime | `tools/check_km_core_abi.py`, `tools/compare_pe.py` |
| **Transporte falso** | lógica do cliente contra um `DeviceIoControl` simulado; nada de kernel | `tests/test_km_core_client.py` (28 testes) |
| **Runtime** | carga, IOCTLs reais, ACL, unload, Verifier | G1/G2 e T1–T12 (esta matriz) |

Nenhum resultado estático ou de transporte falso substitui um teste de runtime.

---

## 0. Pré-condições gerais (valem para todos os itens abaixo)

| Item | Requisito |
|---|---|
| Host | Windows 10 Home 19045; VirtualBox; nenhum driver experimental carregado |
| Guest | Windows 10 Home 22H2 x64, build 19045; UBR registrado (não precisa ser 6466) |
| Snapshot | `pre-driver`, tirado após updates e antes de instalar o driver |
| Assinatura | test-signing **somente no guest**; certificado de teste; host intocado |
| Ferramentas no guest | `tools/check_ntoskrnl_export.ps1`, `sc.exe`, Driver Verifier, WinDbg |
| Coleta | `C:\km-test\` no guest + export para `E:\KM-CORE-VM\Dumps\` |
| Proibições | KDU, kdmapper, BYOVD, manual mapping, alteração de boot/CI do host |

Cada item abaixo repete só as pré-condições **específicas**; as gerais valem
sempre.

---

## 1. Gates

### G1 — kernel do guest exporta `IoCreateDeviceSecure`?

- **Objetivo:** saber se o kernel do guest exporta `IoCreateDeviceSecure`.
- **Pré-condições:** guest instalado e atualizado; snapshot `pre-driver` existente;
  nenhum driver instalado ainda.
- **Procedimento:**
  ```
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\check_ntoskrnl_export.ps1
  ```
  (script em `tools/check_ntoskrnl_export.ps1`; sem elevação, só leitura).
- **Resultado esperado:** `exit 0` e `export : IoCreateDeviceSecure RVA=0x...`;
  ou `exit 2` (ausente). Ambos são resultados válidos.
- **Evidência:** saída completa do script (build, versão, SHA-256 do
  `ntoskrnl.exe`, RVA ou ausência).
- **Critério de aprovação:** caminho identificado e registrado; ausência **não** reprova.
- **Critério de interrupção:** `exit 3` (erro de parse) ou discrepância entre build/SHA e o
  que o guest reporta.

### G2 — caminho de resolução do wrapper

- **Objetivo:** identificar qual caminho o wrapper escolheu (export do kernel ou fallback).
- **Pré-condições:** G1 concluído; driver instalado e parado; WinDbg anexado
  (kernel debug por pipe serial); `.map` da build disponível no host.
- **Procedimento:** quebrar em `km_core_base + 0x5108` (o `call rax` de
  `WdmlibIoCreateDeviceSecure`, conforme o `.map`), iniciar o serviço e ler
  `RAX`. `RAX` dentro do `ntoskrnl` ⇒ caminho quente; dentro do `km_core` ⇒
  fallback.
- **Resultado esperado:** um dos dois caminhos, sem RAX nulo.
- **Evidência:** `lm` dos dois módulos, valor de RAX, captura do WinDbg.
- **Critério de aprovação:** caminho identificado e anotado.
- **Critério de interrupção:** RAX nulo/inesperado ou desvio de fluxo.

---

## 2. Resumo

| ID | Objetivo | Status |
|---|---|---|
| T1 | Carga e inicialização | não executado |
| T2 | Device e link simbólico | não executado |
| T3 | ACL efetiva | não executado |
| T4 | Consultas válidas | não executado |
| T5 | IOCTLs inválidos | não executado |
| T6 | Concorrência | não executado |
| T7 | Handle e `DesiredAccess` | não executado |
| T8 | Unload | não executado |
| T9 | Driver Verifier | não executado |
| T10 | Chave de classe | não executado |
| T11 | Falha de inicialização | não executado |
| T12 | Crash (condicional) | não executado |

---

## 3. Testes

### T1 — Carga e inicialização

- **Objetivo:** `DriverEntry` retorna sucesso e o serviço fica `RUNNING`.
- **Pré-condições:** snapshot `pre-driver`; driver assinado com cert de teste;
  G1 registrado.
- **Procedimento:**
  ```
  sc create KmCore type= kernel start= demand binPath= \??\C:\km-test\km_core.sys
  sc start KmCore
  sc query KmCore
  ```
- **Resultado esperado:** `STATE: 4 RUNNING`; sem bugcheck; nenhum evento 7031/7034.
- **Evidência:** saída de `sc`, `Get-WinEvent System` da janela do teste.
- **Critério de aprovação:** serviço `RUNNING` + zero bugcheck.
- **Critério de interrupção:** qualquer bugcheck → T12.

### T2 — Device e link simbólico

- **Objetivo:** confirmar que `\Device\KmCore` e `\DosDevices\KmCore` existem e estão tipados corretamente.
- **Pré-condições:** T1 aprovado; WinDbg anexado.
- **Procedimento:** `!object \Device\KmCore`, `!object \DosDevices\KmCore`,
  `!devobj <addr>`; conferir `DeviceType 0x22` e ausência de
  `DO_DEVICE_INITIALIZING`.
- **Resultado esperado:** os dois objetos presentes, tipo correto, flag já limpa.
- **Evidência:** saída do WinDbg salva em arquivo.
- **Critério de aprovação:** ambos presentes e tipados corretamente.
- **Critério de interrupção:** device ausente com serviço `RUNNING`.

### T3 — ACL efetiva

- **Objetivo:** confirmar que somente SYSTEM e Administradores abrem o device.
- **Pré-condições:** T2 aprovado; conta padrão disponível no guest.
- **Procedimento:** ler o SD com `!object \Device\KmCore`; tentar
  `CreateFile("\\.\KmCore", FILE_READ_DATA)` como usuário padrão.
- **Resultado esperado:** SD `D:P(A;;GA;;;SY)(A;;GA;;;BA)`; usuário padrão recebe
  `ERROR_ACCESS_DENIED` (5).
- **Evidência:** SD do `!object` + código de erro da abertura.
- **Critério de aprovação:** SD exato **e** negação para usuário padrão.
- **Critério de interrupção:** qualquer acesso concedido a usuário padrão.

### T4 — Consultas válidas

- **Objetivo:** confirmar que as três consultas retornam dados coerentes.
- **Pré-condições:** T3 aprovado; 0006 aplicada (commit `ccec2cd`); cliente
  copiado para o guest.
- **Procedimento:** `python km_core_client.py` três vezes.
- **Resultado esperado:** ABI `1`; driver `1.0 build 1`; state `ready`; caps
  `get_version, get_state, get_caps`; `max xfer 0`; `RequestsServed` crescendo.
- **Evidência:** saída completa das três execuções.
- **Critério de aprovação:** os três blocos corretos e contador monotônico.
- **Critério de interrupção:** `WinError`, ABI divergente ou contador regredindo.

### T5 — IOCTLs inválidos

- **Objetivo:** confirmar que entradas malformadas devolvem status, nunca crash.
- **Pré-condições:** T4 aprovado; harness `C:\km-test\ioctl_fuzz.py` escrito a
  partir da tabela abaixo.
- **Procedimento:** enviar a matriz e registrar `GetLastError` por caso.

  | Caso | Entrada | Status esperado |
  |---|---|---|
  | IOCTL desconhecido | código fora de `0x800–0x802` | 1 (`INVALID_FUNCTION`) |
  | `inLen` curto | `0x08` | 122 (`INSUFFICIENT_BUFFER`) |
  | `inLen` excedente | `0x18` | 87 (`INVALID_PARAMETER`) |
  | `outLen` curto | `0x08` | 122 |
  | ABI | `AbiVersion=0/2` | 1306 (`REVISION_MISMATCH`) |
  | `StructSize` | `0x08` | 87 |
  | `Command` | código trocado | 87 |

- **Resultado esperado:** cada caso com o status da tabela; nenhum bugcheck.
- **Evidência:** tabela preenchida (caso → `GetLastError`) + Event Log limpo.
- **Critério de aprovação:** todos os status corretos e zero crash.
- **Critério de interrupção:** bugcheck ou status divergente.

### T6 — Concorrência

- **Objetivo:** confirmar que consultas paralelas no mesmo handle não corrompem estado.
- **Pré-condições:** T4 aprovado; harness com 8 threads.
- **Procedimento:** 8 threads × 1000 `GET_STATE` no mesmo handle; ler
  `RequestsServed` antes e depois.
- **Resultado esperado:** delta ≥ 8000 (o driver conta todas as requisições), sem crash e
  sem `WinError`.
- **Evidência:** log do harness + contador final.
- **Critério de aprovação:** sem crash e delta consistente.
- **Critério de interrupção:** qualquer erro de IOCTL sob concorrência.

### T7 — Handle e `DesiredAccess`

- **Objetivo:** mapear o comportamento de abertura (`FILE_READ_DATA`, `GENERIC_READ`, acesso 0, segunda abertura).
- **Pré-condições:** T4 aprovado.
- **Procedimento:** abrir com `FILE_READ_DATA`; com `GENERIC_READ`; com `0`; e
  uma segunda abertura simultânea.
- **Resultado esperado:** `FILE_READ_DATA` aceito; `0` negado; segunda abertura negada
  (`SHARING_VIOLATION`, 32). `GENERIC_READ` é **medição** — o resultado define a
  documentação, não reprova.
- **Evidência:** quatro resultados com código de erro.
- **Critério de aprovação:** primeira aceita, `0` e segunda negadas; `GENERIC_READ`
  documentado.
- **Critério de interrupção:** duas aberturas simultâneas aceitas.

### T8 — Unload

- **Objetivo:** confirmar recusa de unload com handle aberto e descarga limpa depois.
- **Pré-condições:** T3 aprovado; T7 executado (comportamento de handle
  conhecido); snapshot existente.
- **Procedimento:** (1) com um handle aberto, `sc stop KmCore`; (2) fechar o
  handle e repetir; (3) `!object \Device\KmCore` depois.
- **Resultado esperado:** (1) falha com `STATUS_DEVICE_BUSY`/`ERROR_BUSY`; (2) sucesso;
  (3) device e link ausentes.
- **Evidência:** saídas de `sc stop` e `!object`.
- **Critério de aprovação:** recusa com handle aberto + descarga limpa depois.
- **Critério de interrupção:** unload aceito com handle aberto (risco de use-after-free).

### T9 — Driver Verifier

- **Objetivo:** confirmar ausência de violações de IRQL/pool/handle sob Driver Verifier.
- **Pré-condições:** T1–T8 aprovados sem Verifier; snapshot novo (para reverter
  fácil).
- **Procedimento:**
  ```
  verifier /standard /driver km_core.sys
  verifier /querysettings
  shutdown /r /t 0
  ```
  repetir T1–T8 com o Verifier ativo.
- **Resultado esperado:** zero bugcheck de verificação (`0xC4`, `0xC1`, `0xC5`, `0xCD`,
  `0x50`, `0xF7`); `!verifier 3` sem violações.
- **Evidência:** `verifier /querysettings` antes/depois, `!verifier`, dumps.
- **Critério de aprovação:** T1–T8 passam com o Verifier ativo.
- **Critério de interrupção:** qualquer bugcheck de verificação.
- **Reversão:** `verifier /reset` + reboot; registrar que foi revertido.

### T10 — Chave de classe

- **Objetivo:** documentar o artefato de registro criado por `IoCreateDeviceSecure`.
- **Pré-condições:** T1 aprovado; acesso ao registro do guest.
- **Procedimento:** exportar
  `HKLM\SYSTEM\CurrentControlSet\Control\Class\{4b7c1a10-2f3d-4c8e-9a51-6d7b2e18c044}`
  antes e depois da carga; conferir `Security`, `DeviceType`, `Exclusive`.
- **Resultado esperado:** chave presente; valores coerentes com o SDDL e o device.
- **Evidência:** dois `.reg` exports.
- **Critério de aprovação:** artefato documentado (não é falha).
- **Critério de interrupção:** valores de segurança divergentes do SDDL.

### T11 — Falha de inicialização

- **Objetivo:** confirmar que falhas de alocação são tratadas sem bugcheck e sem recurso órfão.
- **Pré-condições:** T1–T8 aprovados; snapshot novo; Verifier disponível.
- **Procedimento:**
  ```
  verifier /lowresources /driver km_core.sys
  shutdown /r /t 0
  ```
  repetir `sc start KmCore` 5× e conferir que a falha é controlada.
- **Resultado esperado:** falha de alocação tratada (serviço não sobe) **sem** bugcheck,
  **sem** vazamento (`!poolused`/`!verifier`) e **sem** device/link órfão.
- **Evidência:** status de `sc start`, `!object` (nada criado), pool.
- **Critério de aprovação:** falha limpa, nada órfão.
- **Critério de interrupção:** bugcheck ou device órfão.
- **Reversão:** `verifier /reset` + reboot.

### T12 — Crash (condicional)

- **Objetivo:** preservar e atribuir a causa de um bugcheck, se ocorrer.
- **Pré-condições:** dumps configurados no guest (`CrashDumpEnabled=1/2`);
  ocorrência de bugcheck em qualquer teste anterior.
- **Procedimento:** `!analyze -v`, `lm`, `kb`, `!verifier 3`; exportar o dump
  para `E:\KM-CORE-VM\Dumps\`.
- **Resultado esperado:** causa atribuída a módulo/instrução; dump preservado.
- **Evidência:** dump + saída do WinDbg.
- **Critério de aprovação:** não se aplica (só roda em falha); a análise é a evidência.
- **Critério de interrupção:** não se aplica.

---

## 4. Configuração do Driver Verifier (reversível)

```
verifier /standard /driver km_core.sys     # instala
verifier /querysettings                    # evidência do que está ativo
verifier /reset                            # remove (sempre ao fim)
```
`/standard` cobre special pool, pool tracking, IRQL e handle checking.
Low-resource simulation é separado (`/lowresources`, usado em T11). Toda mudança
exige reboot no guest e é revertida ao final. O host não é tocado.

## 5. O que já está coberto (e o que não está)

| Cobertura | Ferramenta | Prova |
|---|---|---|
| ABI cliente↔driver↔binário | `tools/check_km_core_abi.py` | estática |
| Lógica do cliente / 0006 | `tests/test_km_core_client.py` (28) | transporte falso |
| Build reprodutível | `km_core/build.ps1` + `tools/compare_pe.py` | estática (conteúdo executável idêntico; binário integral não) |
| Carga, ACL, IOCTL, unload, Verifier | esta matriz | **não executado** |

## 6. Critérios globais de interrupção

1. Qualquer bugcheck → parar a matriz, preservar dump, ir para T12.
2. ACL divergente ou acesso indevido → parar.
3. `sc stop` aceito com handle aberto → parar (risco de use-after-free).
4. Teste sem evidência coletada não conta como aprovado.
5. Nenhuma alteração de código durante a execução da matriz.
