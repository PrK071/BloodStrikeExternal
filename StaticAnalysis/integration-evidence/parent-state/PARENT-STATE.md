# Associação e Parent.IsInWorld

Amostra SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. RVAs, base preferencial `0x140000000`. Apenas arquivo em disco. Este complemento não modifica a V4 selada.

O literal `0x5b` em `0x19c0138` é o **índice de um token internado**, e não evidência de um identificador independente da propriedade. O helper leaf `0x470dc0` recebe esse índice, carrega o ponteiro em `0x4e93470 + índice*8` e o coloca no objeto temporário de lookup.

| Ligação | Evidência |
|---|---|
| Seleção do índice | `0x19c0138`: EDX=0x5b; chamada a `0x470dc0` em `0x19c0141` |
| Helper | `0x470dc2` obtém tabela `0x4e93470`; `0x470dc9` lê `[tabela+índice*8]` |
| Slot selecionado | `0x4e93748` contém VA preferencial `0x144e71948` (`INT-P-D01`) |
| Token | `0x4e71948` contém VA preferencial `0x144e9d9d8` (`INT-P-D02`) |
| Texto | `0x4e9d9d8`: `IsInWorld\0` (`INT-P-D03`) |

O objeto submetido ao lookup vem de `C+0x40` em `0x19c012b`, campo já ligado a `IComponent.Parent` pela V3. A função obtém seus metadados em `0x19c0146`, procura a chave montada por `0x470ff0` e lê o valor retornado pela propriedade. O resultado booleano chega a R12B em `0x19c01c6`; Parent nulo ou resultado falso produz zero em `0x19c01cc`.

Na mesma função, o teste de R12B controla notificações/ativação do ator e o caminho de inserção conhecido. A remoção da chave antiga ocorre quando existe ator antigo, mesmo quando R12B está falso; não foi confundida com a condição da nova inserção. O nome da propriedade resolve uma lacuna semântica da V4: a condição é **Parent.IsInWorld**.

Há uma segunda evidência independente do nome: os metadados refletidos de `IEntity.IsInWorld`, preservados em `INT-P-D04` e anteriormente em `V3-D01`, ligam o getter `0x952640` ao bit `0x10` de `+0x130`. O filtro de `GetAllActors` testa esse bit no Parent. Para Parent efetivamente do tipo IEntity e com essa propriedade, a consulta na associação e o filtro pertencem à mesma semântica declarada. Não se presume que qualquer IObject contendo o nome implemente o mesmo getter, nem que o estado permaneça igual entre os dois instantes.

**Conclusão de confiança alta:** a associação consulta uma propriedade denominada IsInWorld no Parent. Isso reforça uma relação com participação no mundo e transições da entidade, sem definir uma categoria de gameplay. Não prova jogador/NPC, alvo válido, exclusividade de associação, sincronização ou segurança de uma referência externa.

`trace_parent_state.py` reproduz os ponteiros/texto, extrai os CFGs selecionados e confere comprimentos com Capstone. `data.json`, `code.json` e `summary.json` preservam os bytes e limites. Os identificadores antigos continuam intactos; a seleção nova usa `INT-P-*`.
