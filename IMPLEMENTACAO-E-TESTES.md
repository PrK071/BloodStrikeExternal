# Implementação e testes — 26/10/2026

O coletor já funciona contra um espaço de memória gravado e contra um processo filho de teste, usando `OpenProcess`/`ReadProcessMemory` reais no segundo caso. A projeção também está implementada como função independente, baseada no método nativo recuperado. **Isso ainda não entrega um ESP/aimbot funcional em Blood Strike.** O jogo não foi executado, aberto nem lido nesta etapa.

## O que mudou

| Antes | Agora | Limite |
|---|---|---|
| Decodificador isolado de posição | `ExternalCore/registry.py` percorre a raiz do registro e entrega componentes, atores, Parent, serial e posição quando sustentada por RTTI | Não classifica jogadores ou adversários |
| Sem aquisição implementada | `win32_memory.py` oferece leitor Win32 com handles de consulta/leitura, tamanho exato e lock contra `close()` concorrente | Validado com filhos próprios; acesso ao jogo não testado |
| Parent tratado apenas como relação | `rtti.py` calcula o objeto completo e um único subobjeto público IEntity não virtual | Rejeita hierarquia ambígua, base virtual e deslocamento de construção; não implementa todo `dynamic_cast` |
| Projeção em aberto | `screenpoint.py` reproduz o fluxo de `ICamera.GetScreenPointFromWorldPoint` → helper RVA `0x275db0` | Seleção final da câmera/viewport e frame dos anchors continuam abertos; `math.tan` não promete igualdade bit a bit com tanf do jogo |
| Oito testes de posição | **40 testes, zero falhas/erros/skips no Windows local**, JSON e JUnit com hashes do código | CI Linux/Python 3.13 foi configurada, sem execução remota observada |

## Suíte do projeto

Estes são testes automatizados mantidos pelo projeto, feitos com `unittest`. Não existe nesta entrega suíte fornecida/aprovada pela NetEase nem certificação oficial do jogo.

Da raiz do projeto, com Python 3.12+ x64:

```powershell
python tools/run_tests.py
```

Alternativa PowerShell:

```powershell
.\tools\run-tests.ps1 -Python 'C:\caminho\python.exe'
```

Não requer pacotes de terceiros, instalação do jogo nem providers REA/Ghidra. A saída está em `reports/tests/summary.json` e `reports/tests/junit.xml`. Ambos são invalidados antes da descoberta de testes, evitando preservar um PASS anterior após interrupção. O código de saída é diferente de zero em falha. O relatório vincula o resultado aos hashes dos arquivos testados.

Cobertura executada:

- Posição: float32 antes da soma double, anchors assinados, sentinela coletiva/mista, limites e buffers mutáveis.
- Memória/registro: lacunas e sobreposição de segmentos, leituras parciais, build divergente, raiz nula, registro vazio, ciclos, limite de nós, chave zero/duplicada, serial divergente e mudanças entre leituras.
- RTTI: ajuste não nulo do objeto completo e de IEntity, ausência de base, ambiguidade, visibilidade e construção.
- Projeção: origem e orientação da base, FOV vertical/viewport retangular, pontos atrás da câmera, profundidade zero, arredondamento half away from zero e entradas inválidas.
- Integração nativa: leitura do registro inteiro em filho próprio, mutação observada, endereço inválido/não committed, fechamento idempotente, seleção por caminho completo e fechamento concorrente com leitura em curso.
- CLI/relatórios: sucesso de ponta a ponta a partir de snapshot, procedência preservada, build recusada antes de abrir processo, erro substituindo saída antiga, subtests deliberadamente falhos e falha de inicialização de classe.

No Linux os quatro testes Win32 são marcados como não aplicáveis. O job Windows exige que os quatro passem sem skip. `.github/workflows/test.yml` configura Windows/Linux e Python 3.12/3.13 com publicação de relatórios como artefatos. **Workflow escrito não equivale a CI executada.**

## Uso do coletor

Modo offline:

```powershell
python -m ExternalCore snapshot captura.json --output quadro.json
```

O formato `bloodstrike-external-memory-v1` contém `module` (`base`, `size`, `sha256`), `provenance` e segmentos `{ "address": inteiro, "hex": "..." }`. Não executar Python do snapshot. A identidade é declarada pelo arquivo; ela não prova que os bytes sejam de uma captura real. Os testes declaram explicitamente a procedência sintética.

A CLI também implementa `capture --pid PID --sample CAMINHO --output quadro.json`. Esse caminho **não foi executado contra o jogo**. Exige PID explícito e confere o SHA em disco antes de abrir qualquer processo; compara caminho completo e tamanho do módulo e usa a base obtida do módulo, sem presumir base preferencial. Falha de permissão é propagada. Identidade por arquivo/caminho/tamanho não prova igualdade de cada página do módulo em execução.

O resultado mantém todos os registros examinados, com motivo quando uma posição não é decodificada. `IsInWorld` é estado de engine, não categoria de gameplay. Somente `IEntity` resolvido por RTTI recebe o decodificador de posição. O leitor não chama funções do jogo.

## Consistência e validade

Cada tentativa compara duas passagens, incluindo todos os bytes de RTTI/posição utilizados; falhas não produzem quadro parcial. Há limite de nós, detecção de ciclos e quantidade limitada de tentativas. Isso permite rejeitar certas mudanças durante a aquisição.

**Duas passagens iguais não são snapshot atômico nem prova de lifetime.** Uma transição A→B→A pode escapar, assim como destruição/recriação no mesmo endereço. O serial pode sofrer wrap e não foi demonstrado como geração universal. Nenhum campo recebe o rótulo de geração de vida observada sem observação correspondente. A validade pode mudar imediatamente após o retorno.

## Projeção e integração restante

`decode_camera(buffer)` lê os campos demonstrados e `project_screenpoint(camera, float3)` executa a aritmética. Preserva a ordem das operações float32 e quantização em décimos; usa `math.tan` alargado/arredondado, sem promessa de ULPs idênticos ao CRT do alvo. Rejeita entradas não finitas/FOV inválido como contrato do consumidor. O método nativo não aplica Near/Far nem branch ortográfico. O consumidor deve checar `in_front`; X/Y também existem para pontos atrás.

A origem da entrada deve corresponder a `camera+0x7c`. `GetEntityPosition` soma anchors inteiros em double; o helper de tela lê/subtrai apenas floats e não consulta anchors. **Não foi demonstrado que ligar diretamente os dois resultados produza a projeção correta de toda entidade.**

O novo vínculo de scripts chega a `GetGameplay().Player.Camera`; acessores de ClientPlayer sustentam Camera em `+0xd88`. A transição do tipo declarado IComponent para ClientPlayer concreto e a alimentação do viewport final ainda precisam ser fechadas. `ActorComponent` também é usado por modelos de armas; não fornece sozinho seleção de alvos. O código novo não presume adversário, equipe, vida ou bones.

Ainda faltam esses vínculos e sua validação em instâncias reais para ligar aquisição → projeção → overlay → seleção de adversário → mira. A restrição vigente de acesso ao processo protegido impede declarar essa validação concluída nesta entrega. Não é solicitada nova permissão.

## Evidências e fontes

- Layout do registro e chave: `StaticAnalysis/AUDITORIA-V2.md`, `AUDITORIA-V3.md`, `AUDITORIA-V4.md`; identificadores e manifestos anteriores preservados.
- Campos de posição: `StaticAnalysis/integration-evidence/entity-position/ENTITY-POSITION.md`.
- Câmera e método de tela: `StaticAnalysis/integration-evidence/camera-binding/CAMERA-BINDING.md`, `SCREENPOINT-CONTRACT.md` e respectivo manifesto.
- Categorias: `StaticAnalysis/integration-evidence/actor-classification/README.md`.
- API oficial [ReadProcessMemory](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory) e [formato PE/RVA](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format).
- Configuração de CI baseada nos projetos oficiais [setup-python](https://github.com/actions/setup-python) e [upload-artifact](https://github.com/actions/upload-artifact). Essas fontes documentam ferramentas; não validam semântica ou funcionamento do cheat no jogo.
