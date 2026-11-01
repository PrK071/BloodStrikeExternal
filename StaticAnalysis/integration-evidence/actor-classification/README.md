# Classificação estática de ActorComponent e owners

Data: 2026-10-26. Fonte: recursos MPK da instalação Blood Strike, lidos do disco; nenhuma execução do jogo, bytecode, processo protegido ou memória de processo.

## Resultado

A cadeia de modelo de personagem fecha como **AvatarModel → PoseSenderModel → SimpleModel**. Em `AvatarModel.Load`, o modelo carregado é lido por `model.Skeleton`; o código verifica se esse objeto é exatamente `MObject.ActorComponent` (`__class__` comparado com o tipo) e segue o fluxo usando `owner`. A rotina então consulta `owner.IsCombatAvatar`, `owner.IsATMGuardAI` e `owner.IsPlayerCombatAvatar`. Este é um discriminador semântico no lado do script para reconhecer tipos de owner, e a API `IsPlayerCombatAvatar` é o candidato mais direto a “player”.

Isso **não prova um identificador nativo externo** que um leitor externo possa consultar para separar players de NPCs. Não foi ligado o valor/retorno de `IsPlayerCombatAvatar` a um campo nativo estável, offset, método de interface comprovado ou memória observada. Tampouco foi provado como o owner chega à instância concreta de `ClientPlayer` ou se o valor cobre todos os players/modos. Portanto: há uma distinção explícita no código de gameplay; não há, nesta evidência, um classificador externo nativo utilizável comprovado.

`ActorComponent` sozinho não classifica personagem. `SimpleModel.ReloadSkeleton` lida genericamente com `model.Skeleton` e `ActorParent`/`AddChild`; `WeaponModel` também usa `model.Skeleton`, `AddChild` e `AttachToParent` para conectar modelo de arma à mão. Assim, observar um ActorComponent ou uma relação Parent/child identifica uma estrutura de modelo/conexão, não a categoria do owner. A evidência anterior do índice de tipos nativos também documenta `Messiah::ActorComponent` como componente de esqueleto, sem afirmar classe de player.

## Evidência reproduzível

- `01_parse_actor_modules.py` lê três entradas MPK pelos offsets do `Resources.mpkinfo`, reverte o prefixo XOR e descomprime zlib sob limite de 4 MiB; então usa o parser estático reutilizável `python-format/03-static-marshal.py` e decodificador de instruções CPython 3.14 de `05-opcodes-selected.py`. Exige EOF completo e não chama `marshal.loads`, `eval`, importação de payload nem executa bytecode.
- `resource-code-static.json` registra metadados de entrada, hashes e todos os code objects/instruções dos índices `37243` (`avatar.py`), `94890` (`posesender_model.py`) e `122267` (`base_model.py`). Os hashes decodificados coincidem com `assets/script-candidate-index.json`: `8d428d9bd02fe90e1e2decbbef2505e0db9f64942998329a2e592b3a74cee81c`, `9dfd8aa5a6de063a3a7c93122d7ba81ccd067490a7e4044213604c39523515b0`, `fa89d954bac2e48a5c53b09fc06e6f46c91d04e067221f59836ade8e77b2dc08`.
- `gameplay/python-model-links/model-link-static.json` (entrada `selected-models-static.json`, SHA-256 `0493a5c510cc06a998d4888777696e14195ed947ef7f7be144414017cd58aa9a`) fornece as janelas complementares de `AvatarModel.Load`, `AvatarModel.ReloadSkeleton`, `SimpleModel.ReloadSkeleton`, `WeaponModel` e `SimpleModel.HasActorComponent`.
- Janelas úteis no fluxo CPython 3.14 de `AvatarModel.Load`: bytecode offset 670 testa `__class__ == MObject.ActorComponent`; 830 lê `owner.IsCombatAvatar`; 886 lê `owner.IsATMGuardAI`; 1146 e 1348 consultam `owner.IsPlayerCombatAvatar`. Em `SimpleModel.ReloadSkeleton`, offsets 50–140 testam `isinstance(model.Skeleton, MObject.ActorComponent)` e obtêm `ActorParent`; o fluxo posterior acessa o filho/adiciona ao pai. Em `WeaponModel.AttachWeaponToHandEquip`/`AttachWeaponToRightHand`, o skeleton da arma é adicionado ao modelo de mão e anexado ao parent.

## Escopo e lacuna

Os códigos de avatar/PoseSender/BaseModel foram integralmente parseados até EOF e as instruções decodificadas sem opcode desconhecido. O arquivo amostrado do jogo tem SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`, conforme a identidade fixada no índice estático do projeto; não houve nova análise de binário nesta tarefa. Os índices de recursos são evidência da instalação consultada, não uma garantia de que o overlay de recursos seja atual ou corresponda a qualquer outra build.

Para transformar `IsPlayerCombatAvatar` em classificador externo ainda falta ligar sua implementação/valor a um campo ou método nativo lido externamente, determinar ciclo de vida e confirmar amostras de player, NPC e arma. Não inventar offsets nem inferir pela palavra `ActorComponent`.
