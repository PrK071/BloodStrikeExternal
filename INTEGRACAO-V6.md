# Integração V6 — 01/11/2026

A V6 corrige o vínculo entre modelo e proprietário, implementa a rota de dados de `genv.player`, acrescenta leitura tipada das propriedades replicadas e verifica o corpo de um predicado Python sem executá-lo. **108 testes passaram localmente**, com nove integrações nativas em processos/janelas próprios. O ESP/aimbot completo ainda exige filtros de adversário/estado e validação do jogo; esta entrega não declara essa meta concluída.

O trabalho desta etapa ficou em arquivos e testes próprios. Nenhum processo protegido foi aberto, nenhuma função/bytecode do alvo foi executado e nenhum evento de mouse foi enviado. A suíte pertence ao projeto; não há certificação ou testes oficiais da NetEase, nem execução remota de CI afirmada.

## V5 × V6

| Área | V5 | V6 | Limite atual |
|---|---|---|---|
| Proprietário do modelo | Leitura do owner como possível host com marcador de jogador | O produtor passa `self.area`; ponte nativa area → host e associação reversa implementadas | Overrides Python continuam fora da leitura de dados armazenados |
| Modelo principal | Candidato AvatarModel por MRO/owner | Exige também `host.model == instance` e `instance.model == P` nos dados armazenados | Não prova ausência de previews ou duplicações em execução |
| Armazenamento Python | Dicionário combinado positivo | Managed dict, inline values e split values da ABI 3.14 GIL suportados | Tabelas laterais de builtins e layouts diferentes são recusados |
| Jogador local | Desconhecido | `_PyRuntime` → interpretadores → módulos → `gclient.genv.player`, com identidade area/host | Precisa existir na captura; ambiguidade ou replay distinto não é resolvido por palpite |
| HP e campos de estado | Sem leitor | Descoberta por nome no mapa da classe; int64/double e células mistas tipadas | Campo armazenado não é automaticamente o resultado do getter Python |
| Adversário | Desconhecido | Corpo base e overrides analisados; verificador de bytecode/operandos implementado | Método realmente selecionado e dispatch dos operandos ainda exigem prova |
| Estado de vida | Desconhecido | Consumidores distinguem `ALIVE` e `DYING`; âncora do enum nos defaults identificada | Valor/tipo do enum não observado; HP não é convertido em vivo/morto |
| Testes | 73 aprovados | 108 aprovados, zero falhas/erros/skips | Testes de buffers não equivalem a instâncias do jogo |

## Descobertas e confiança

Os IDs desta seção são novos; não renumeram ou substituem as evidências V2/V3/V4/V5. A amostra permanece SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. Todos os endereços citados como RVA pertencem a essa amostra, não a um processo observado. Os MPKs têm hashes próprios, reconferidos; o hash do executável sozinho não identifica overlays de scripts ou atualizações de recursos.

| ID | Conclusão sustentada | Confiança e evidência | Limitação |
|---|---|---|---|
| BS-V6-001 | O owner atribuído ao AvatarModel é o proxy nativo de area, que conduz ao host Python | Alta, `combat-state-v6/phase2-owner-shape/` e `native-properties-v6/prop-and-area-accessors.json`; getters nomeados e stores conferidos | Host efetivo de uma instância ainda depende dos bytes observados |
| BS-V6-002 | Há uma rota nativa para os dicionários dos módulos por interpretador | Alta, `local-player-v6/local-player-route.json`, tabela `xdebugpy` e getters independentes | Head é o mais recente; não assumir main. Em disco, o ponteiro head é zero |
| BS-V6-003 | Os produtores publicam o jogador em `genv.player`/`main_player` e limpam por identidade | Alta, `combat-state-v6/01-semantic-modules.json` | Replay tem outra seleção; o leitor recusa contexto conflitante |
| BS-V6-004 | As propriedades numéricas podem ser lidas por nome e descritor da classe | Alta para representação, `native-properties-v6/native-map-contract.json`, getters/setters e construtores | Não há índice universal de equipe/HP. Tags não numéricas permanecem desconhecidas |
| BS-V6-005 | A leitura passiva dos links do modelo pode usar managed/split/inline storage 3.14 | Alta para ABI fixada, `native-properties-v6/managed-models/managed-layout-contract.json` | Dados armazenados não executam nem substituem resolução de descritores |
| BS-V6-006 | `IsEnemy` não possui uma regra universal demonstrada para todos os modos | Alta, `combat-state-v6/phase3-opponent-predicate/` e `phase6-active-method/` | A classe/marcador do objeto não identifica sozinho o método ativo |
| BS-V6-007 | O corpo base pode ser comparado incluindo instruções e operandos sem executar Python | Alta para o baseline e normalização comum, `predicate-code-v6/` e `ExternalCore/predicate.py` | Instrumentação/executores são recusados; corpo igual não certifica dispatch/getters |
| BS-V6-008 | Os consumidores de mira usam uma allowlist de `CombatState`; HP positivo não é prova equivalente | Alta, `combat-state-v6/phase5-aim-eligibility/` | Inteiro de `ALIVE` desconhecido; `7` nos fixtures é dado sintético sem significado de enum |

### Correção do owner e dos links

A interpretação direta da V5, que procurava o marcador de jogador no próprio `.owner`, foi rejeitada para o produtor examinado. O fluxo entrega `self.area`. Os callbacks nativos demonstram:

```text
B = [AreaPy + 0x20]
N = [B]
H = [N + 0x38]
HostPy = [H]

[HostPy + 0x20] == H
[H + 0x10] == AreaPy
```

O leitor exige os tipos-base Asio area/entity nos MROs e as associações reversas. Depois compara os links armazenados `HostPy.model == AvatarModel` e `AvatarModel.model == P`, além de `P.instance == AvatarModel`. Isso recusa links antigos/secundários nos casos cobertos. O MRO AvatarModel continua necessário porque armas também têm owner jogador. O resultado continua sendo candidato `player`; não é convertido automaticamente em `opponent`.

Os Asio area/entity/map têm tamanho-base `0x28`, diferente do PyIEntity de `0x30`. Não se transferiu um layout entre esses tipos. A leitura das associações não chama `area.owner()`, `area.prop()` ou qualquer API do alvo.

### Identidade local e representação dos valores

`python_runtime.py` valida cookie/versão/GIL da tabela nativa, percorre a lista limitada de interpretadores e procura um módulo exato sob `gclient.genv`. O tipo do módulo e seu dicionário são conferidos. Ciclos, múltiplos contextos, aliases conflitantes e `replay_player` distinto deixam o jogador local desconhecido.

`native_properties.py` segue o mapa da area, enumera os nomes e valida descritor, índice, schema, backlinks e limites da storage. Aceita int64, double e tags mistas numéricas comprovadas. Ausência, incompatibilidade ou falha de leitura produz diagnóstico; não se usa zero ou o default do descritor para completar campos ausentes. O pipeline expõe esses dados em `classification.facts.values`; HP pode aparecer no rótulo como valor armazenado.

`python_managed.py` distingue ponteiro de dict em `obj-0x18`, inline values válidos e dicionário materializado. No split dict, índices pertencem ao schema compartilhado, não ao número de atributos ativos desta instância. O byte `valid` não é exigido para values não embedded, onde fica sem inicialização no construtor examinado. A precedência dos inline values foi preservada.

`python_values.py` só decodifica tipos builtin exatos corroborados: None/bool, inteiros de dígitos de 30 bits, float double finito e Unicode ASCII compacto. Não chama conversões nem interpreta subclasses automaticamente. Os layouts e os headers oficiais fixados estão em `python-values-v6/scalar-layout-proof.json`.

### Predicado e dispatch

O corpo base `IGameLogicBase.IsEnemy` recusa a mesma instância e argumentos falsey; considera inimigos quando alguma facção é negativa, ou quando as facções diferem. Essa interpretação depende do corpo específico e do comportamento dos argumentos. Foram encontrados overrides de modos/componentes, e `CanDamage` pode permitir dano em aliados por opção. `IsEnemy`, `CanDamage`, `IsFriend` e `IsTeammate` não foram tratados como sinônimos.

O verificador exige tipos exatos de function/code, assinatura/flags, constantes bool exatas, nomes de atributos/locais, kinds, ausência de closure/defaults e exception table esperada. Normaliza especializações comuns e ignora somente os payloads de cache ao comparar instruções. O fingerprint canônico do corpo base é `b632457e07b643ddb05ff3b4de958097174ce648941cd15075b3b9f6831f20c5`. Duas passagens independentes comparam a identidade e os demais bytes relevantes. Monitoramento, executores ou opcode desconhecido falham explicitamente.

O lookup nativo do host tenta a resolução genérica antes do fallback para o mapa. Um atributo de instância, descritor ou método customizado pode alterar o valor efetivo de `host.faction`; o valor bruto de NumericMap não resolve essa questão. Da mesma forma, verdade do objeto pode envolver slots de bool/length do tipo efetivo. O relatório complementar `native-properties-v6/attribute-dispatch/` registra essa fronteira. `PredicateBody` retorna `active_dispatch_verified=false` e `operand_semantics_verified=false`; não libera alvos sozinho.

`AssistAim.SelectTarget` usa `CombatState.ALIVE` por default; um consumidor específico permite `ALIVE` e `DYING`. O objeto membro pode ser ancorado em `AssistAim.__dict__['SelectTarget'].__defaults__[-1][0]`, após validar módulo/classe/função. O import demonstrado é `gshare.consts.CombatState`. Não se atribuiu inteiro a esses nomes, nem se chamou o enum para descobrir sua conversão.

## Reproduzir

Python 3.12+ x64 e biblioteca padrão, na raiz do projeto:

```powershell
python tools/run_tests.py --output-dir reports/tests-v6
python StaticAnalysis/integration-evidence/runtime-v6/verify_delivery.py
```

O primeiro comando executa o projeto sem depender da instalação do jogo. O segundo precisa da amostra e dos MPKs locais nos caminhos da investigação, além dos manifestos anteriores. Ele invalida o resultado anterior antes da conferência. O resultado foi PASS: 30.484 registros de bytes, incluindo repetições, correspondentes a 19.548 pares distintos de RVA/tamanho, e 346 payloads MPK comprimidos/decodificados com hashes iguais. Esses totais incluem evidências V5 reutilizadas e extrações exploratórias; igualdade de bytes não certifica a semântica de cada decode nem cobertura completa de CFG. A preservação dos 98 arquivos selados da V4 foi reconferida.

Há dois exemplos reproduzíveis no formato `bloodstrike-external-memory-v1`, ambos rotulados como buffers sintéticos de teste:

```powershell
python StaticAnalysis/integration-evidence/runtime-v6/make_example.py
python -m ExternalCore scene reports/examples-v6/state-memory.json --output quadro.json --svg quadro.svg
python -m ExternalCore predicate reports/examples-v6/predicate-memory.json --function 0x200011f88 --output predicado.json
```

`0x200011f88` é o endereço do objeto function no exemplo sintético entregue, também registrado em `reports/examples-v6/addresses.json`; não é endereço/offset do jogo. Para outra entrada, o parâmetro precisa identificar seu objeto function real. Os comandos CLI dos exemplos foram executados e os resultados conferidos em `reports/examples-v6/verification.json`. O verificador conserva a procedência e não resolve o método ativo. Erros substituem um resultado antigo por um registro de falha. A CLI rejeita saída que sobrescreva a entrada/amostra.

Relatórios atuais: `reports/tests-v6/summary.json`, `junit.xml`, `console.txt`. Os **108 testes** incluem nove integrações nativas próprias e cobertura de ABI Python, metadados inconsistentes, links reciclados/alterados, limites, aliases/replay, propriedades não suportadas e falsos matches de predicado. Os 47 arquivos de fonte/teste vinculados ao resultado foram reconferidos. A execução V5 permanece histórica, vinculada à sua versão de fontes.

## Hipóteses e próximos passos

| Hipótese | Estado V6 | Consequência |
|---|---|---|
| `.owner` já é o host Python marcado | Rejeitada no produtor analisado | Usar a ponte nativa e a identidade reversa |
| Owner jogador basta para classificar um corpo | Rejeitada | Armas também têm owner; exigir MRO e links do modelo |
| Mesmo endereço/serial identifica a mesma vida | Não demonstrada | Não manter alvo ou categoria por endereço entre frames |
| `faction != local.faction` é regra universal de inimigo | Rejeitada como regra universal | Resolver método/mode ativo e seus operandos |
| `server_hp > 0` significa `ALIVE` | Não demonstrada | Preservar HP e combat_state como dados separados |
| Links primários armazenados eliminam qualquer preview | Aberta | Confirmar caminhos de criação e instâncias observadas |
| Mesmo corpo Python basta para reproduzir a decisão | Rejeitada | Ainda verificar dispatch, verdade e getters/comparações |

As três perguntas da V4 permanecem delimitadas: a chave observada é o serial de 32 bits associado ao ator/Skeleton, sem prova global de não reutilização; o registro aceita componentes de modelos, não uma categoria universal de jogadores; e a invalidação possui caminhos internos conhecidos, mas leituras externas iguais não demonstram uma geração de vida nem um intervalo seguro de uso. A V6 melhora a classificação de uma associação observada, sem resolver essas garantias globais.

A continuação estática deve fechar a resolução efetiva de `IsEnemy` e dos atributos dos hosts, a representação do enum de estado e os produtores que distinguem previews. Validação dinâmica controlada ainda precisa observar fábrica/tipos reais, associações, transições de vida, seleção de câmera/viewport e calibração de entrada. O log por evento deve manter sequência, thread, operação, chave, componente/Parent, metadado nativo/RTTI, fábrica, W/P, IsInWorld e uma geração de vida observada. Um endereço reutilizado inicia outra instância, não a continuidade da anterior.

Nenhuma evidência desta etapa demonstra funcionamento do cheat em partida. O overlay, a projeção e o planejamento continuam implementados e testados nos limites descritos; os filtros desconhecidos continuam recusando alvos.
