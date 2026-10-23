# Evidência PE: RTTI e produtores candidatos de gameplay

A inspeção foi feita como leitura estática do arquivo `E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe`. O SHA-256 foi conferido como `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747` antes de cada script. A fonte é compatível com o contexto Steam build 25981220 / patch 126 anotado em `results/provenance.json`. `RawPE` de `audit_v2.py` fez o mapeamento RVA/arquivo e a decodificação de instruções; nenhuma execução do jogo nem acesso a processo ocorreu.

O catálogo cobre as 21.764 hierarquias em `results/rtti-hierarchies.json` (SHA-256 e tamanho de entrada em `chain-evidence.json`) e pesquisa substrings nos 32.609 descritores de `results/rtti-types.json`. O resultado completo de triagem está em [catalog.json](catalog.json); buscas por substring incluem nomes decorados, lambdas e métodos e, por si só, não classificam tipos.

## Cadeia de tipos e usos confirmados

- RTTI `Messiah::IPlayer`, COL RVA `0x6e43518`, descreve herança de `IStoryboard`, `IComponent` e `IObject` (além de si próprio). O COL e seu descritor foram relidos pelo `RawPE`; assinatura, self-RVA e descritor coincidem com a hierarquia catalogada.
- RTTI `Messiah::ClientPlayer`, COLs `0x6ea2828` e `0x6ea28f0`, deriva de `IPlayer`, `IStoryboard`, `IComponent`, `IObject` e `IInputFilter`. As duas entradas correspondem a subobjetos em offsets 0 e 3.424. As vtables candidatas em `0x4f9ca40` e `0x4f9ca90` são ligadas a COLs por ponteiros relocados em dados.
- No código, a função iniciada em `0xa76b40` carrega essas vtables (`0xa76b63`, bytes `48 8d 05 d6 5e 52 04`; `0xa76b6d`, bytes `48 8d 05 1c 5f 52 04`) e grava os ponteiros em `[rbx]` e `[rbx+0xd60]`. A função em `0xa77290` repete as gravações. Isso liga as tabelas RTTI a caminhos de inicialização de objeto; os símbolos de função não estão disponíveis, então a atribuição “construtor” é uma inferência estrutural.
- RTTI `Messiah::ActorComponent`, COLs `0x6f72620` e `0x6f726c0`, deriva de `SkeletonComponent`, `ISkeletonComponent`, `IComponent`, `IObject` e `ITickable`; subobjetos nos offsets 0 e 104. A cadeia é confirmada pelos COLs e pelas vtables candidatas `0x559b8f8` e `0x559b9f0`.
- Código em `0x19bf520` carrega as vtables de `ActorComponent` (`0x19bf539`, bytes `48 8d 05 b8 c3 bd 03`; `0x19bf543`, bytes `48 8d 05 a6 c4 bd 03`) e as grava em `[rbx]` e `[rbx+0x68]`. Outras funções em `0x19bf730`, `0x19bf960` e `0x19bfb60` também referenciam as duas tabelas. Esse é um produtor concreto do tipo de componente, com semântica exata das funções não nomeadas.

## Propriedades refletidas relevantes

O PE contém a string `IGameplay.Player` no RVA `0x4f501e0`; uma tabela de dados aponta para ela no RVA `0x4f6e1c0`, ao lado dos nomes `IGameplay`, `IComponent` e `Player`. Campos adjacentes apontam para funções pequenas cujo código usa o offset `+0x58`: `0x58b020` retorna o endereço `this+0x58` (`48 8d 42 58; c3`), `0x92bec0` lê `[this+0x58]` (`48 8b 41 58; c3`) e `0x948bd0` substitui o valor em `[this+0x58]` (`48 89 7b 58`), com chamadas de notificação se o valor antigo/novo não for nulo. A proximidade de ponteiros na tabela refletida e a forma dos acessores sustentam uma propriedade `IGameplay.Player` armazenada em `+0x58`. O tipo exato do valor e a identidade de instâncias concretas não são provados por esse trecho.

Há ainda a string `Messiah.ClientPlayer.Char` no RVA `0x51c47e0`, referenciada por registros que também contêm `ClientPlayer` e `Char` (ponteiros em `0x51f91f0` e `0x51f9210`). Isto sustenta a presença de um membro refletido `Char` associado nominalmente a `ClientPlayer`. Os callbacks candidatos próximos são wrappers genéricos; não identificam, por si, o tipo nem o objeto retornado. Portanto, a cadeia `IGameplay.Player` → instância de `ClientPlayer` → personagem não está fechada por prova estática nesta etapa.

A string `CharacterImp.ActorComponent.IsEnableVisibilityOptimize` (RVA `0x5633a00`) aparece em estruturas refletidas com os nomes `ActorComponent` e `IsEnableVisibilityOptimize` e ponteiros relocados para código ao redor. Isto vincula o tipo/componente a metadados de `CharacterImp`, mas o campo nomeado é de otimização de visibilidade, não uma classificação de player. Nomes RTTI de closures associados a `ActorComponent` incluem `_CreateAttachedRigidBodyByGuid`, `_LoadSkeletonAndGraphDeferred_on_ot` e `_SphereSweepCollisionBoneMatchUserTag`; são nomes refletidos/decorados, não provas de chamadas ou de semântica em runtime.

## Evidência negativa e limites

Não há tipo RTTI com nome `LocalPlayer`, `PlayerController` ou `Enemy` nas 21.764 hierarquias. A única ocorrência `CharacterController` é `physx::Cct::CharacterControllerManager`, um tipo PhysX; não é uma classe de personagem de gameplay identificada. As 10 hierarquias cujo nome próprio contém `Team` são de `MiniMapTeammateElement` ou auxiliares relacionados, sem evidência de atributo de time do personagem. As 8 ocorrências com `Health` são classes/dados de dano e destruição (por exemplo, `ChunkHealth`/`BondHealth`), sem tipo próprio `Messiah::Health` nem ligação demonstrada a vida de player. `MCharacter` aparece em parâmetros/reflection e nomes de métodos; não há tipo RTTI concreto próprio `Messiah::MCharacter` nesta hierarquia. A ausência é específica ao inventário RTTI do PE; não significa ausência em recursos de script.

As ocorrências de `PlayerController` e `LocalPlayer` não aparecem em ASCII nem UTF-16LE na imagem PE. `Enemy` também não aparece nesses formatos. Termos curtos (`Team`, `Health`, `Parent`, `Character`) retornam ruído e nomes de editor/engine. Coincidência de texto, localização ou nome de interface não foi usada como classificador.

O achado separado de `Parent.IsInWorld` em `integration-evidence/parent-state/` não é reproduzido nem contado como associação de tipo aqui: é estado/propriedade, não classificação de personagem. Também não há, nesta evidência PE, ligação comprovada entre o ponteiro `Parent`, um `ActorComponent` específico e uma instância de `ClientPlayer`. A indexação recém-feita de scripts/recursos pode oferecer novas classes de gameplay, mas análise de bytecode e decodificação de recursos estão fora deste relatório.

## Reprodutibilidade e artefatos

Os scripts salvos nesta pasta são:

- [01_catalog.py](01_catalog.py): verifica o SHA fixado e cataloga candidatos RTTI e ocorrências textuais, com exemplos limitados por termo.
- [02_chain.py](02_chain.py): verifica COLs, heranças, vtables e referências para tipos/strings selecionados.
- [03_trace.py](03_trace.py): grava janelas de código e metadados com RVA, file offset e bytes.
- [04_reflection_callbacks.py](04_reflection_callbacks.py): decodifica candidatos de acessor próximos aos registros refletidos.

Os resultados estruturais estão em [chain-evidence.json](chain-evidence.json), [trace-evidence.json](trace-evidence.json) e [reflection-callbacks.json](reflection-callbacks.json). Os JSONs registram SHA do PE e entradas RTTI; as instruções guardam RVA, offset, bytes e texto do decoder. [catalog.json](catalog.json) contém totais de busca, candidatos e limites.

Todos os scripts usam Python 3.12, módulos padrão e `audit_v2.RawPE`; o parser importa `iced-x86` local de `StaticAnalysis/audit-vendor`. Cada script aceita `--binary` e por padrão aponta ao executável acima, abortando se o SHA não for o fixado. A confirmação hash de cada execução está em seus resultados.
