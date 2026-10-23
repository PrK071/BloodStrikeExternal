# BloodStrikeExternal — estado real da investigação

Este repositório reúne o diagnóstico reproduzível e as análises estáticas da build examinada. **Ainda não contém ESP, aimbot, radar ou outro cheat funcional.** Os offsets incluídos foram fornecidos sem versão e continuam sem validação para esta build. Os executáveis do jogo, os diretórios de instalação e os bancos binários do Ghidra não fazem parte do repositório.

## Auditoria estática V2 — 21/10/2026

[StaticAnalysis/AUDITORIA-V2.md](StaticAnalysis/AUDITORIA-V2.md) registra a conferência independente com parser PE próprio e iced-x86, a ligação de `GetAllActors` com `MCharacter`, o retorno em lista Python e a relação demonstrada entre o registro e `ActorComponent`. Inclui 26 descobertas classificadas e os limites de cada uma. Nenhum layout de jogador ou cheat operacional foi validado.

O verificador foi corrigido para publicar sucesso somente após as checagens curadas e registrar falhas sem manter `PASS` antigo. Os quatro controles de verificação passaram. Reprodução: `StaticAnalysis\run-audit-v2.ps1` e `StaticAnalysis\test_audit_controls.py`.

## Análise estática com instruções verificadas — 20/10/2026

Foi adicionada uma análise do executável instalado com pefile e Capstone, identificação por SHA-256/timestamp PE, inventário RTTI, hierarquias, tabelas virtuais, referências de código e dependências. Há evidência de instruções para o registro de `GetAllActors`, seu callback e acessos parciais a estruturas; foram confirmados vptrs de `Character::Actor`, `ActorComponent`, `SkeletonComponent` e `ICamera`.

O relatório completo está em [StaticAnalysis/RELATORIO.md](StaticAnalysis/RELATORIO.md). A análise não implementa funcionalidades de cheat e não valida campos de jogador, equipe, bones ou matriz de câmera em execução. Os offsets externos continuam não validados.

Reprodução: executar `StaticAnalysis\run-static-analysis.ps1`. As nove evidências curadas estão restritas ao SHA-256 da build analisada; uma atualização exige nova demonstração dos endereços.

## Resultado em 20/10/2026

A instalação foi localizada e inspecionada. ESP, aimbot, radar e no-recoil **ainda não estão implementados ou validados**. O código presente nesta pasta é o diagnóstico reproduzível da instalação e das permissões de leitura.

### Instalação identificada

- Pasta: `E:\SteamLibrary\steamapps\common\BLOODSTRIKE`.
- Executável: `Engine\Binaries\Win64\BloodStrike.exe`.
- Steam App ID: `3199170`; build do depot instalado: `25981220`.
- Versão local `LocalData\Patch\pkgversion`: `126`. Este identificador é separado do build do Steam.
- PE AMD64, 141.431.288 bytes, base preferencial `0x140000000`, `SizeOfImage = 0x94e9000`.
- SHA-256: `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`.
- Assinatura Authenticode verificada por `Get-AuthenticodeSignature`: válida; NetEase (Hangzhou) Network Co., Ltd.
- O manifesto embutido declara `asInvoker`. O processo observado, entretanto, está elevado; o manifesto não prova qual mecanismo do launcher produziu essa elevação.

### Arquivos fornecidos

O JSON possui 70 entradas, sem build, data, módulo base, tipos dos campos ou descrição completa das estruturas. Os cinco valores zero não foram automaticamente tratados como inválidos: zero também pode ser um deslocamento legítimo.

Os seis valores grandes, **interpretados como RVAs do BloodStrike.exe**, ficam fora de sua imagem:

| Entrada | Valor |
| --- | --- |
| `il2cpp.get_handle` | `0xe7ccc60` |
| `base_networkable.typeinfo` | `0xe43c280` |
| `main_camera.typeinfo` | `0xe4863e8` |
| `BaseViewModel.BaseViewModel_C` | `0xe4a2f20` |
| `ListComponent_Projectile.ListComponent_C` | `0xe4dd1c0` |
| `TOD_Sky.TOD_Sky_C` | `0xe401ad8` |

O JSON não identifica outro módulo base. Nenhum foi presumido.

### Evidências no executável

- Strings ASCII: `NewSpike` (752 ocorrências), `Messiah` (41.862), `FpsPlacer` (81).
- `GetAllActors` aparece uma vez, como string no RVA `0x5bb8878`. **Esse endereço é da string, não da função nem da lista de entidades.**
- Não foram encontradas as strings ASCII exatas `BaseNetworkable`, `TOD_Sky` ou `il2cpp`. A ausência de strings, isoladamente, não prova a ausência de uma tecnologia.
- Existe uma seção PE chamada `PyRuntim`.
- O endereço `0x8a8e810` citado na página de referência cai na parte virtual, sem bytes correspondentes no arquivo, da seção `.data`. Isso é compatível com armazenamento inicializado em runtime, mas **não valida que seja o Actor Manager desta build**.

Essas evidências sustentam a identificação Messiah/NewSpike descrita pelo autor de https://globality.live/case-bloodstrike . Os fragmentos publicados não fornecem o layout completo e validado necessário às quatro funcionalidades solicitadas.

## Acesso ao processo

Na observação inicial, PID `12712`: consulta limitada autorizada; abertura com `PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ` retornou erro Win32 `5` (acesso negado).

Após o jogo ser reaberto, PID `13088`: mesmo resultado. O token do jogo estava elevado; o processo Python de inspeção estava sem elevação. Nenhuma leitura de memória foi executada.

A diferença de elevação é uma barreira concreta a investigar, mas o diagnóstico não prova que seja a única causa. Igualar a elevação não garante que o acesso será concedido ou que os offsets estejam corretos.

## Arquivos e reprodução

- `inspect_build.py`: parser PE32+ com verificações de limites, hash SHA-256, módulos importados, localização de strings, verificação dos RVAs fornecidos e consulta dos tokens/permissões.
- `run-inspection.ps1`: resolve o PID atual e executa o diagnóstico; não solicita nem altera elevação automaticamente.
- `reports/build-25981220-patch126.json`: resultado efetivamente observado com PID `13088`.

Em um terminal PowerShell, executar:

```powershell
& '.\run-inspection.ps1'
```

O script apenas consulta arquivos e permissões e grava o relatório nesta pasta. Não injeta DLLs, não escreve no processo e não executa os arquivos do jogo. Não depende de pacotes Python externos.

Não foram criados nem executados testes automatizados nesta etapa. As execuções registradas são inspeções reais da instalação. Ainda faltam derivação e validação dos layouts de entidades, jogador local, câmera, equipes e armas, além de acesso de leitura autorizado que funcione no processo atual.
