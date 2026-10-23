# Análise estática — Blood Strike Windows x64

Análise realizada em 20/10/2026, horário de São Paulo. Resultado: mapa parcial de tipos, componentes, funções e dependências, com evidências do executável instalado. Os layouts publicados abaixo representam acessos efetivamente observados em instruções. Não são um SDK completo nem uma reconstrução do código fonte.

**Identificação da amostra**

| Identificador | Valor observado |
| --- | --- |
| Arquivo | `E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe` |
| SHA-256 | `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747` |
| Tamanho | 141.431.288 bytes |
| Formato | AMD64 / PE32+ |
| Timestamp COFF bruto | `0x6acbbfba` |
| Timestamp COFF interpretado | `2026-10-11 16:56:26 UTC` |
| Base preferencial | `0x140000000` |
| SizeOfImage | `0x94e9000` |
| EntryPoint RVA | `0x424c4a4` |
| Steam App / build | `3199170` / `25981220` |
| Patch local `pkgversion` | `126` |
| Authenticode | Válida; NetEase (Hangzhou) Network Co., Ltd. |

SHA-256 identifica os bytes examinados. A data COFF é um valor declarado no cabeçalho; não constitui prova independente da data de compilação. O diretório debug contém tipos 2, 12 e 13; não foi encontrado `IMAGE_DEBUG_TYPE_REPRO` tipo 16. Build Steam, patch local e timestamp PE são identificadores diferentes. Regras de RVA, VA e timestamp seguem a [especificação PE da Microsoft](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).

Todas as VAs no material de evidência são **VAs preferenciais**: `0x140000000 + RVA`. A base real com ASLR não foi consultada. O hash permaneceu idêntico antes e depois da análise.

O registro CodeView/RSDS aponta para `G:\NewSpike\src_dev_2024\Engine\Binaries\Win64Release\Game_x64r.pdb`. Trata-se de um caminho embutido, sem acesso ao código desse diretório. Nenhum PDB foi encontrado na instalação pesquisada. O nome `src_dev_2024` não data a build analisada.

**Método e cobertura**

- Parser PE `pefile 2024.8.26`; desassemblador Capstone pacote `5.0.9`, engine nativa reportada `5.0.7`.
- Inventário de imports, exports, seções, CodeView e registros `RUNTIME_FUNCTION`.
- Recuperação de TypeDescriptors MSVC, Complete Object Locators e descritores de bases, com verificações de limites e coerência dos RVAs internos.
- Identificação de tabelas virtuais por ponteiros para COLs, seguida de referências de código e stores dos vptrs nas quatro classes centrais.
- Referências RIP-relative de formas selecionadas de `LEA`/`MOV`, confirmadas em limites de instrução por desassemblagem a partir do início de função indicado pelo PE.
- Conferência independente com o parser local `inspect_build.PortableExecutable`, sem usar `pefile` nem Capstone para recalcular os RVAs e deslocamentos RIP-relative.

Os intervalos de `.pdata` são registros de unwind, não uma contagem exata de funções fonte: há leaf functions sem entrada própria, fragmentos e possíveis funções incorporadas. Essa interpretação segue a [documentação x64 da Microsoft](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170).

| Item inventariado | Quantidade |
| --- | ---: |
| TypeDescriptors estruturalmente reconhecidos | 32.609 |
| Complete Object Locators validados | 21.764 |
| Entradas `RUNTIME_FUNCTION` reconhecidas | 309.153 |
| Símbolos exportados | 651, sendo 639 apontando para código |
| Módulos na tabela de imports | 37 |
| DLLs adjacentes inventariadas | 35 |
| Strings de âncora catalogadas | 2.473 |
| Tabelas virtuais do núcleo examinado | 12 |
| Referências de código verificadas | 370 |
| Unidades de desassemblagem exportadas | 262 |

Os tipos incluem templates, lambdas, classes de bibliotecas e descritores usados em exceções. Não equivalem a 32.609 classes de gameplay reconstruídas. As 262 unidades também incluem rotinas anônimas e leaf functions; seus nomes semânticos não foram inventados.

**Resultados confirmados — tipos e componentes**

O vínculo entre cada classe abaixo e sua tabela virtual foi sustentado pela cadeia TypeDescriptor → hierarquia → COL → ponteiro anterior à vftable, além de código que instala a vftable na instância.

| Classe | Vftable principal RVA | Função que a instala, RVA | Evidência de store | Confiança |
| --- | --- | --- | --- | --- |
| `Character::Actor` | `0x5565060` | `0x16d0e70` | `0x16d0e9f` carrega a tabela; `0x16d0ea6` grava `[rdi]` | Alta |
| `Messiah::ActorComponent` | `0x559b8f8` | `0x19bf520` | `0x19bf539` carrega; `0x19bf540` grava `[rbx]` | Alta |
| `Messiah::SkeletonComponent` | `0x4fa22a0` | `0xad5c10` | `0xad5c29` carrega; `0xad5c30` grava `[rbx]` | Alta |
| `Messiah::ICamera` | `0x4e57558` | `0x275720` | `0x27573d` carrega; `0x275744` grava `[rdi]` | Alta |

Hierarquias reconstruídas a partir dos descritores de bases:

```text
Messiah::IObject
  ├─ Messiah::IComponent
  │    └─ Messiah::ISkeletonComponent, também com base Messiah::ITickable
  │         └─ Messiah::SkeletonComponent
  │              └─ Messiah::ActorComponent
  └─ Messiah::IEntity, também com TObjectComponent<IEntity>/ObjectComponentBase
       └─ Messiah::ICamera

Messiah::IRefObject
  └─ AnimationCore::Skeleton
       └─ Character::Actor
```

`Character::Actor` pertence a uma hierarquia de esqueleto/animação. Não foi demonstrado que uma instância dessa classe represente diretamente um jogador, inimigo ou entidade de rede.

`SkeletonComponent` e `ActorComponent` têm um subobjeto `ITickable` em `+0x68`. O deslocamento aparece tanto no RTTI quanto nas instruções que instalam as tabelas secundárias. Não é uma inferência baseada em proximidade de strings.

| Layout parcial comprovado | Acesso | Instrução RVA | Confiança |
| --- | --- | --- | --- |
| `Character::Actor +0` | Ponteiro para vftable principal | `0x16d0ea6` | Alta |
| `ActorComponent +0` | Vptr principal | `0x19bf540` | Alta |
| `ActorComponent +0x68` | Vptr do subobjeto `ITickable` | `0x19bf54a` | Alta |
| `SkeletonComponent +0` | Vptr principal | `0xad5c30` | Alta |
| `SkeletonComponent +0x68` | Vptr do subobjeto `ITickable` | `0xad5c3a` | Alta |
| `ICamera +0` | Vptr principal | `0x275744` | Alta |
| `ICamera +0x408` | Inicialização de 4 bytes com `0x10001`; nome do campo desconhecido | `0x275747` | Alta para o acesso |
| `ICamera +0x454` | Inicialização de 4 bytes com `0x42700000`; 60,0 se interpretado como float | `0x27579c` | Alta para os bits; sem nome de campo confirmado |

Não foi publicado `+0x454` como offset de FOV: o valor inicial é sugestivo, mas não demonstra a semântica do campo. Também não foram deduzidos tamanhos completos de objetos a partir desses acessos parciais.

**Resultados confirmados — registro de `GetAllActors`**

| Elemento | RVA | VA preferencial | Evidência / confiança |
| --- | --- | --- | --- |
| String `GetAllActors` | `0x5bb8878` | `0x145bb8878` | NUL-terminated e referenciada pelo registro; alta |
| Rotina que contém o registro | `0x32362d0` | `0x1432362d0` | `.pdata` e desassemblagem; alta para o intervalo |
| Callback associado ao nome | `0x3259770` | `0x143259770` | Store do endereço no mesmo registro; alta |
| Helper chamado durante o registro | `0x1bff870` | `0x141bff870` | Chamada direta; alta para a ligação, nome fonte desconhecido |

Trecho decisivo, com limites de instrução confirmados:

```asm
; x86-64 | BloodStrike.exe com o SHA-256 acima | endereços abaixo são RVAs
0x3239679  B9 20 00 00 00                 mov ecx, 0x20
0x3239681  E8 E2 2A 01 01                 call 0x14424c168
0x3239686  48 8D 15 EB F1 97 02           lea rdx, [rip+0x297f1eb] ; string RVA 0x5bb8878
0x3239693  48 89 10                       mov [rax], rdx
0x3239696  48 8D 15 D3 00 02 00           lea rdx, [rip+0x200d3]   ; callback RVA 0x3259770
0x323969D  48 89 50 08                    mov [rax+0x08], rdx
0x32396A4  C7 40 10 04 00 00 00           mov dword ptr [rax+0x10], 4
0x32396AB  48 89 70 18                    mov [rax+0x18], rsi
0x32396AF  E8 BC 61 9C FE                 call 0x141bff870
```

O bloco solicita 32 bytes e escreve nome em `+0`, callback em `+8`, flags em `+0x10` e outro ponteiro em `+0x18`. Isso corresponde ao registro `PyMethodDef` em Windows x64. A interpretação dos quatro campos e de `METH_NOARGS` é apoiada pela [documentação oficial de estruturas da API C do Python](https://docs.python.org/3/c-api/structures.html#c.PyMethodDef). O vínculo nome ↔ callback é demonstrado pelos próprios stores; a identificação com a API Python é uma interpretação de alta confiança apoiada nesse padrão.

**Resultados confirmados — acessos dentro da enumeração**

O callback chama `0x19d45e0` em `0x32597a5`. Esse helper contém:

```asm
; x86-64 | BloodStrike.exe com o SHA-256 acima | RVA do helper 0x19d45e0
48 8B 05 A9 87 1A 07  mov rax, [rip+0x71a87a9] ; lê ponteiro no RVA 0x8b7cd90
C3                    ret
```

O RVA `0x8b7cd90` designa armazenamento de um ponteiro lido por esse fluxo. Está na extensão virtual da `.data`, sem bytes correspondentes no arquivo. O acesso é comprovado pela instrução, enquanto o valor do ponteiro, seu conteúdo e seu estado durante a partida permanecem desconhecidos.

| Acesso observado | Instrução RVA | O que pode ser afirmado | Confiança |
| --- | --- | --- | --- |
| `[resultado_do_helper +0x08]` | `0x32597aa` | Ponteiro usado como sentinela no percurso | Alta para o fluxo |
| `[sentinela +0]` | `0x32597ae` | Primeiro nó do percurso | Alta para o fluxo |
| `[nó +0x18]` | `0x32597c0` | Obtém valor de 8 bytes | Alta para o acesso |
| `[valor_anterior +0x40]` | `0x32597c4` | Obtém outro ponteiro, que é testado contra zero | Alta para o acesso |
| Byte em `[ponteiro_anterior +0x130]`, máscara `0x10` | `0x32597cd` | Condição que filtra a enumeração | Alta para a operação; significado do bit desconhecido |
| `[nó +0]` | `0x325982f` | Avança até reencontrar a sentinela | Alta para o fluxo |

O padrão é compatível com uma estrutura encadeada com sentinela. Não foi demonstrado o tipo exato de container C++, o layout completo de cada nó ou a identidade de todos os elementos retornados. A função também realiza conversão de elementos e acumulação no objeto de retorno, mas os nomes fonte dos helpers não foram recuperados.

**Python/C++ e Asyncore**

Foram reconhecidos `Messiah::PythonAsyncoreModule` e 1.109 TypeDescriptors com o padrão `Asyncore::pybase_object_impl<...>`, incluindo especializações relacionadas a `PyActorComponent`, `PySkeletonComponent` e `PyICamera`. Há strings `add_method`/`add_getset`, seções `PyRuntim`/`AsyncioD` e registros de métodos nativos como o demonstrado acima.

Os metadados confirmam a presença de tipos Asyncore e wrappers C++ nomeados. Em conjunto com os registros de métodos, sustentam a integração C++/Python. Não foi estabelecida a versão exata do Python incorporado nem foi tratada a classe C++ Asyncore como o módulo Python padrão `asyncore`.

O catálogo inclui 210 strings com prefixo `CharacterImp.ActorComponent.`, 139 com `Messiah.SkeletonComponent.` e 14 com `ICamera.`. São nomes disponíveis para investigação, não 363 funções já identificadas e validadas.

**Câmera: o que continua sem confirmação**

Os metadados de `ICamera.ViewMatrix` e `ICamera.FieldOfView` apontam, respectivamente, para wrappers em `0x93f1a0` e `0x943d40`. Eles leem um ajuste e chamam um delegado indiretamente:

- ViewMatrix: leituras dos RVAs `0x4f45138` e `0x4f45130`, nas instruções `0x93f1a4` e `0x93f1ae`.
- FieldOfView: leituras dos RVAs `0x4f4b570` e `0x4f4b568`, nas instruções `0x943d44` e `0x943d4e`.

Esses slots estão zerados no arquivo. Não foi estabelecido o caminho completo de sua inicialização. O código indireto não autoriza concluir um offset final de matriz, posição de câmera ou FOV. Os vínculos com os nomes de propriedades vêm dos ponteiros dos metadados; o papel exato de cada slot da estrutura de reflexão não foi generalizado para toda a engine.

**Dependências verificadas**

`imports.json` contém as 37 dependências declaradas e seus símbolos/IAT RVAs. Entre os módulos com nomes próprios estão `CrashHunter_PC3.dll`, `NRD.dll`, `NgSocialNet.dll`, `NtUniSdkBase.dll`, `OrbitSDK.dll` e `libenvsdk.dll`. Os demais incluem APIs Win32 de janela, áudio, rede, criptografia e dispositivos. Não há diretório de delay imports declarado no executável.

`local-dependencies.json` registra tamanho, SHA-256, máquina, timestamp e imports das 35 DLLs imediatamente adjacentes. Também existem bibliotecas em subpastas, como Web, Streamline e ccplayer; a análise transitive dessas subpastas não foi incluída. A presença de um arquivo como OpenCV, Steam ou DLSS não comprova que ele tenha sido carregado nesta execução.

Uma particularidade: o `dbghelp.dll` adjacente é x86 (`0x14c`), enquanto o executável é x64. A tabela de imports registra o nome `dbghelp.dll`, sem provar qual caminho o loader resolveria. Não foi afirmado que essa cópia x86 seja carregada pelo executável x64, nem atribuída falha de funcionamento a ela.

**Offsets externos, outras builds e hipóteses**

O arquivo fornecido `bloodstrike-offsets.json` tem 70 entradas, sem build, data válida ou módulo base. Nenhuma entrada foi promovida a layout confirmado.

Seus seis valores grandes, incluindo nomes `il2cpp.get_handle`, `base_networkable.typeinfo` e `TOD_Sky.TOD_Sky_C`, ficam fora do `SizeOfImage` desta amostra quando interpretados como RVAs do executável principal. A nomenclatura é incompatível com os tipos centrais confirmados nesta análise, mas a build e o jogo de origem não foram determinados apenas por esse fato.

O endereço `0x8a8e810`, citado anteriormente em material externo, continua não validado para esta build. Sua presença dentro da extensão virtual de `.data` não é evidência semântica. O getter efetivamente ligado ao fluxo de `GetAllActors` desta amostra lê `0x8b7cd90`.

Não há amostra de uma segunda versão para comparação. Portanto, não foi possível identificar positivamente uma tabela como pertencente a outra build específica. Itens externos permanecem classificados como **origem/versão não comprovadas**, e não como offsets corrigidos ou equivalentes.

Hipóteses ainda abertas: campos de posição/transform, identificação de jogador local, relação entre ator de animação e entidade de gameplay, equipes, bones, ownership dos componentes, matriz de projeção, FOV, tamanho completo de objetos e ciclo de vida das raízes globais. Nenhum desses campos foi preenchido por aproximação.

**Verificação executada e métricas**

- Hash do executável preservado durante a análise.
- Dois parsers concordaram em base, tamanho da imagem, entrada e timestamp.
- 38.445 registros de instrução conferidos contra bytes nos offsets de arquivo recalculados pelo segundo parser.
- 370 destinos RIP-relative conferidos por soma independente de RVA + tamanho + deslocamento com sinal.
- 132 slots de vftable conferidos contra os ponteiros de 64 bits do arquivo.
- Nove conjuntos de evidência curada passaram por verificação de bytes exatos, restrita ao SHA-256 desta build.

Resultado dessa conferência: `PASS`, conforme `results/verification.json`. Isso valida a consistência do material estático; não valida comportamento de objetos em partida.

Execução completa medida: 19,517 s de parede e 12,672 s de CPU. Pico de working set do processo Python: 559.403.008 bytes, aproximadamente 533,5 MiB; working set no fim da medição: 373.592.064 bytes. Esses valores incluem leitura do PE, estruturas de análise e relatórios em memória. Não são métricas de FPS, latência ou custo de um cheat.

**Artefatos e reprodução**

- `analyze_static.py`: extração estática, inventários, desassemblagem e referências.
- `verify_evidence.py`: segunda conversão RVA/arquivo, conferência dos bytes e nove conjuntos curados.
- `run-static-analysis.ps1`: executa extração e conferência.
- `requirements.txt` e `vendor/`: versões locais das ferramentas; pefile MIT e Capstone BSD, com avisos de licença preservados nos pacotes.
- `results/summary.json` e `provenance.json`: identificação e métricas.
- `results/confirmed-evidence.json`: endereço RVA, VA preferencial, offset de arquivo, bytes, interpretação, confiança e limites de cada conjunto confirmado.
- `results/rtti-types.json`, `rtti-hierarchies.json`, `core-hierarchies.json`, `core-vtables.json`: metadados e mapa parcial de tipos. Os inventários amplos não são listas de offsets operacionais aprovados.
- `results/function-evidence.json`, `disassembly.txt`, `code-xrefs.json`, `xref-windows.json`: código e contexto verificável. Dumps grandes podem estar truncados explicitamente; as janelas preservam o contexto das referências selecionadas.
- `results/imports.json`, `exports.json`, `local-dependencies.json`, `anchor-strings.json`, `external-offsets-unvalidated.json`: inventários auxiliares e separação do material não validado.

```powershell
# PowerShell | reprodução da análise estática | Windows x64
& 'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\run-static-analysis.ps1'
```

O verificador das evidências curadas exige o hash desta amostra. Se o jogo atualizar, esses endereços não serão automaticamente considerados válidos. A extração genérica pode ser refeita, mas a curadoria precisa ser novamente demonstrada.

Limites de cobertura: somente o executável principal e DLLs adjacentes foram analisados em profundidades diferentes; não houve decompilação de todas as rotinas, execução dos binários, consulta de memória do jogo ou acesso aos fontes. Também não foram executadas injeção, alterações do jogo ou interferência no anti-cheat.

A próxima etapa estática mais útil é reconstruir a inicialização dos delegados de reflexão e correlacionar seus acessos com os tipos já reconhecidos. Isso pode esclarecer os campos de câmera e ownership de componentes sem aceitar valores de outra build.
