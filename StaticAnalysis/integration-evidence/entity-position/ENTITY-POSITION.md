# IEntity: decodificador de posição por snapshot

Implementado `ExternalCore/entity_position.py`, somente Python 3.12/stdlib, e `tests/test_entity_position.py`. O componente recebe um buffer já adquirido e não abre processos, procura ponteiros ou detecta tipos. **Implementação: pronta. Validação offline: 8 testes aprovados. Validação dinâmica: zero.** Não representa um cliente/ESP funcional.

## Prova estática reconferida

Amostra SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`, PE em disco, base preferencial `0x140000000`. Todos os endereços abaixo são RVAs, exceto deslocamentos de objeto explicitamente marcados.

- `0x2d84498`, bytes `48 8d 0d 71 04 e0 02`, carrega string `GetEntityPosition`, RVA `0x5b84910`; `0x2d844a5` a grava no registro. `0x2d844a8`, bytes `48 8d 0d 61 0e 00 00`, carrega callback `0x2d85310`, gravado em +8 do mesmo registro em `0x2d844af`.
- No callback, `0x2d85342`/`0x2d8534d` preparam RTTI de IEntity (`0x7de5d78`) e IObject (`0x7dd90c8`) para helper de conversão em `0x2d85356`. O resultado é testado em `0x2d8535b`; o ramo de sucesso passa o ponteiro convertido em RCX e chama `0x8977b0` em **`0x2d85368`**.
- Após a chamada, `0x2d85374` lê duas doubles de saída+0x48/+0x50 e `0x2d85378` lê a terceira de +0x58; prepara esses três valores para a construção do retorno Python em `0x2d85393`.

`verified-instructions.json` guarda bytes, RVAs, offsets de arquivo e instruções completas do helper/callback, mais o trecho de registro. `cfg-and-types.json` guarda arestas intraprocedurais e RTTI bruta: todos os endereços decodificados desses dois corpos são alcançáveis nos CFGs selecionados. Calls são listados separadamente; não foram expandidos os demais callees nem assumido sucesso de conversão para qualquer objeto arbitrário.

## Campos e regra exata do helper 0x8977b0

| Campo relativo ao argumento IEntity ajustado | Prova de instruções |
|---|---|
| Transform float32[12] em +0x58..+0x87 | loads `0x897828`, `0x897835`, `0x897839`, `0x897866`, `0x897876`, `0x89788a` e loads de tradução abaixo |
| Tradução float32 x/y/z em +0x7c/+0x80/+0x84 | **`0x897820`**, **`0x89783d`**, **`0x897848`** |
| Origem/anchor signed int32[3] em +0x1ac/+0x1b0/+0x1b4 | comparações `0x8977bc`, `0x8977d8`, `0x8977ec`; loads `0x897808`–`0x89781c` |
| Saída corrigida double[3] em +0x48/+0x50/+0x58 | soma/conversão `0x897853`–`0x897897`, stores `0x8978c0`, `0x8978c5` |

As três comparações com `0x7fffffff` são combinadas por OR/cmov; **`0x897806`** salta a `0x897820` somente se TODAS são sentinela. Esse ramo usa origem (0,0,0). Se qualquer componente difere da sentinela, o bloco lê e utiliza os TRÊS int32 originais — inclusive os valores sentinela remanescentes em um caso misto. Não há substituição por componente.

O helper converte cada float32 para double (`CVTPS2PD`) e cada int32 **assinado** para double (`CVTSI2SD`), então soma com `ADDSD`. O código Python primeiro desempacota little-endian float32 e signed int32; a soma ocorre nos floats Python (double). Não efetua soma intermediária em float32.

Os primeiros nove elementos da matriz são os floats originais alargados. A última trinca recebe a posição corrigida. A API devolve esses doze valores sem impor convenção linha/coluna, unidade, eixo vertical, handedness ou relação com câmera.

## API e contrato

`decode_entity_position(snapshot, *, entity_offset=0) -> EntityPositionSnapshot`

O buffer deve ser contíguo e conter pelo menos **0x1b8 bytes desde entity_offset**, incluindo os três anchors completos até +0x1b7. Aceita buffers como bytes/bytearray/memoryview. Rejeita offset negativo, tipo de offset inválido, buffer insuficiente e não contíguo, com mensagens específicas. Copia apenas a faixa necessária antes de decodificar; aquisição coerente e identificação de IEntity ficam com o caller.

O dataclass imutável contém:

- `position`: resultado das três somas double;
- `local_translation`: valores float32 armazenados, já representados em double;
- `anchor_raw`: três int32 observados;
- `anchor_used`: raw inteiro ou (0,0,0), conforme a regra coletiva;
- `anchor_applied`: se o ramo de origem foi usado;
- `transform`: nove elementos alargados e posição corrigida como última trinca.

Não há filtro de finitude inventado: NaN/infinidades seguem como valores float. Isso não os declara posições válidas. Também não se preserva ou promete equivalência de payloads binários de NaN, sinalização de exceções de FP ou modos SSE não padrão; testes cobrem a aritmética numérica normal demonstrada.

## Validação offline e limites

Comando executado da raiz do projeto:

`python -m unittest discover -s tests -p test_entity_position.py -v`

**8 testes PASS**: identidade/expansão da matriz com todas sentinelas; anchors negativos e extremos assinados; arredondamento float32 prévio e soma double; três casos mistos com cada eixo alternadamente não sentinela; buffer de tamanho exato e entidade em prefixo; truncamentos inclusive um byte faltante; tipos/offsets/contiguidade inválidos; snapshot mutável não retido e valores não finitos.

O caso 16777217 prova uma diferença material: o float32 armazenado vira 16777216; somar anchor 1 em double produz 16777217, resultado que uma soma em float32 perderia. Os testes mistos exigem valores grandes nos eixos ainda sentinela, impedindo a implementação incorreta de tratar cada sentinela individualmente.

Nenhum teste abre o jogo ou lê memória. A identificação dos offsets depende estritamente da amostra fixada; não foi provado que persistam em outra build. Não se demonstra aquisição de registro, lifetime de entidade, jogador local, seleção de adversários, projeção, câmera ou desenho de tela. O resultado é um componente isolado de decodificação, com confirmação estática e offline e sem confirmação dinâmica.
