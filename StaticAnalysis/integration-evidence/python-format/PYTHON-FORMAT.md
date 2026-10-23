# Formato Python dos payloads selecionados

Data: 22/10/2026. Trabalho estático em arquivos; sem executar/importar bytecode do jogo, criar CodeType do host ou usar `marshal.loads`. V2/V3/V4 preservadas. Scripts de reprodução e fontes primárias estão nesta nova pasta.

## Resultado

Os payloads examinados são compatíveis com **marshal de code objects CPython 3.14.0 após um cabeçalho próprio de oito bytes**. A versão foi sustentada por evidência independente do PE e pela estrutura e instruções dos payloads, não presumida pelo magic.

- **32/32** índices originalmente selecionados em `wrapped-zlib-probe.json`: marshal consumido exatamente até EOF; **294 code objects** recuperados.
- Esses **294 code objects** passaram a verificação das instruções CPython 3.14, inclusive avanço por inline caches e EXTENDED_ARG, sem opcode desconhecido nem cache baseline não zero.
- Quatro índices adicionais autorizados: **629 code objects**, todos com parsing até EOF e a mesma validação de opcodes/caches.
- Total nesta etapa: **36 payloads e 923 code objects**, sem executar nenhum deles.

`marshal-static-results.json` contém os primeiros 32; `initial-opcode-validation.json` registra a verificação das suas instruções; `selected-models-static.json` contém os quatro modelos com campos e instruções completos.

## 1. Versão incorporada: evidência do PE

O executável, SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`, contém a string literal `3.14.0` no RVA **`0x58bee18`**, além de dezenas de caminhos de fontes `PythonCore3\Python-3.14.0\...`. Exemplo independente: `Objects\object.c` em `0x580d5f0`.

O literal é referenciado por código que monta uma string de versão. Em **`0x2ba9a79`**, bytes `4c 8d 0d 98 53 d1 02`, carrega o literal em R9; em `0x2ba9a85` carrega o formato `%.80s (%.80s) %.80s`; em `0x2ba9a9d` chama o formatador com destino na região `0x8e3a780`. A função anterior `0x2ba99e0` usa a mesma região e inicialização. Os registros unwind dividem esse trecho; não foi executada a função nem atribuído nome exportado por suposição.

`pe-version-strings.json` e `runtime-version-function.json` preservam essas strings e instruções com RVA, bytes e offset de arquivo. Isso sustenta uma base de runtime **3.14.0**, sem afirmar ausência de modificações proprietárias.

## 2. Magic e cabeçalho

Todos os 36 payloads examinados começam:

`2b 0e 0d 0a 00 00 00 00 63 ...`

O magic `0x0e2b` é decimal 3627, exatamente o valor de CPython v3.14.0, conforme [pycore_magic_number.h](https://raw.githubusercontent.com/python/cpython/v3.14.0/Include/internal/pycore_magic_number.h). Portanto, o magic de quatro bytes coincide com o padrão dessa versão; o encapsulamento continua específico do jogo.

O primeiro objeto marshal começa no offset **8**, com `0x63` (`TYPE_CODE`). Pular 16 bytes, como num `.pyc` moderno convencional, não corresponde ao layout observado. A [implementação padrão de importlib](https://raw.githubusercontent.com/python/cpython/v3.14.0/Lib/importlib/_bootstrap_external.py) usa cabeçalho de 16 bytes. Aqui apenas os oito bytes observados são descritos: o DWORD zero em +4 não recebeu interpretação presumida de timestamp/flags. Também não foi reconstruído o importador nativo que remove esse cabeçalho.

## 3. Parser de dados e estrutura recuperada

`03-static-marshal.py` implementa um leitor declarativo baseado no layout de [marshal.c de CPython v3.14.0](https://raw.githubusercontent.com/python/cpython/v3.14.0/Python/marshal.c). Ele produz listas, dicionários de metadados, strings e bytes; não cria funções ou objetos executáveis.

Para TYPE_CODE, lê cinco inteiros: argcount, posonlyargcount, kwonlyargcount, stacksize e flags. Depois lê code, consts, names, localsplusnames, localspluskinds, filename, name e qualname; segue firstlineno, linetable e exceptiontable. As referências marshal e a flag de referência são acompanhadas, inclusive reserva de referências de code objects antes dos seus campos.

São recuperados **co_filename, co_name, co_qualname, co_names e co_consts** com limites reais de objetos. Nos JSON, nomes abreviados `filename`, `name`, `qualname`, `names` e `consts` correspondem a esses campos. Code objects aninhados aparecem separadamente por `marshal_offset`; em constantes, são representados por referência ao offset e nome. Bytes de constantes têm tamanho/hash/prefixo hexadecimal, evitando construir artefatos executáveis. Tuplas/listas/sets são representados como sequências de dados; o parser não pretende reconstruir todos os tipos exatos do runtime.

O leitor impõe limite de 4 MiB por leitura, profundidade 150, 500 mil nós e 100 mil elementos por container. Referências inválidas, truncamento, comprimentos negativos/excessivos e tags desconhecidas são rejeitados. `06-parser-checks.py` confirma cinco rejeições esperadas e um controle de leitura tipada. Esse é um parser para as amostras verificadas, não uma implementação universal auditada de todo marshal arbitrário.

## 4. Instruções e caches

As tabelas primárias [opcode_ids.h](https://raw.githubusercontent.com/python/cpython/v3.14.0/Include/opcode_ids.h) e [pycore_opcode_metadata.h](https://raw.githubusercontent.com/python/cpython/v3.14.0/Include/internal/pycore_opcode_metadata.h) fornecem IDs e quantidade de inline caches. Em 3.14, **RESUME é 128 (`0x80`)**. O byte inicial `80 00` é coerente com essa versão e não exigiu hipótese de embaralhamento de opcodes.

`05-opcodes-selected.py` lê unidades de dois bytes, acumula EXTENDED_ARG e avança sobre o número de cache words próprio de cada opcode. Valida que caches baseline tenham bytes zero. Os JSON da primeira fase também preservam todas as wordcodes, inclusive CACHE; no resultado dos quatro modelos, `instructions` contém as instruções com argumento acumulado e `cache_words`.

A validação estrutural não equivale a executar a máquina virtual ou verificar completamente stack effects, CFG, exceções, resolução de nomes, importações e lógica de gameplay. Operandos não são todos anotados semanticamente: alguns IDs de nomes/flags são empacotados. Não se devem usar argumentos brutos de LOAD_ATTR/LOAD_GLOBAL como índice direto sem aplicar as regras específicas de 3.14.

## 5. Quatro índices adicionais

Somente os quatro índices indicados foram relidos/descomprimidos da nova lista. Hash comprimido e hash decodificado foram comparados com `script-candidate-index.json`; EOF zlib e ausência de trailing foram conferidos novamente.

| Índice | co_filename recuperado estruturalmente | Code objects |
|---|---|---:|
| 17226 | `gclient/framework/util/MHelper.py` | 82 |
| 25281 | `gclient/gameplay/logic_base/models/weapon_model.py` | 68 |
| 68957 | `gclient/framework/models/simple_model.py` | 165 |
| 143510 | `gclient/gameplay/logic_base/models/avatar_model.py` | 314 |

Isso substitui a antiga evidência de mero substring por campos de code object delimitados. Exemplos de associações de co_names: `SimpleModel.SetStoryboardTickEnabled` contém `IsInWorld`; `SimpleModel.ReloadSkeleton`, `SimpleModel.HasActorComponent`, `AvatarModel.Load` e `AvatarModel.ReloadSkeleton` contêm `ActorComponent`. Essas associações indicam pontos para análise de instruções; isoladamente não provam comportamento, tipo runtime ou alcance de uma chamada.

## 6. Fontes, reprodução e limites finais

`02-fetch-sources.py` baixa apenas fontes textuais do tag fixo CPython v3.14.0; `primary-sources.json` registra URLs, arquivos e SHA-256. Nenhum desses arquivos de fonte Python foi importado para processar o bytecode. O módulo executado via runpy nos scripts 05/06 é exclusivamente o parser escrito nesta pasta; o bytecode alvo só entra como dados.

Ordem de reprodução: 01 inventaria versão do PE; 02 fixa fontes primárias; 03 processa as 32 entradas já selecionadas; 04 preserva a função de versão; 05 valida opcodes e processa os quatro índices novos; 06 verifica rejeições do parser. Interpretador de análise: `C:\Users\luiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

Não foi aplicada a conclusão a todos os 9705 payloads do índice. Os 130 rejeitados da indexação e o item omitido por tamanho permanecem fora da amostra. Co_filename é conteúdo do próprio code object, não garantia de existência de arquivo `.py` independente ou de que todo código seja carregado em uma partida. Não houve extração de árvore de scripts, execução target, import target ou uso de marshal.loads do host.

## Correção do mapa de opcodes e reutilização

A revisão identificou que a regex inicial também capturava os marcadores `HAVE_ARGUMENT`, `MIN_SPECIALIZED_OPCODE` e `MIN_INSTRUMENTED_OPCODE`, sobrescrevendo os nomes dos opcodes 43, 129 e 234. Os scripts 03 e 05 agora excluem esses três marcadores. Os resultados foram regenerados; o parsing de 923 code objects e as verificações de caches permanecem aprovados. O teste adicional fixa `43 → WITH_EXCEPT_START`, `129 → BINARY_OP_ADD_FLOAT` e `234 → INSTRUMENTED_END_FOR`.

O script 05 agora possui `main()` protegido por `if __name__ == '__main__'`. Pode ser carregado por `runpy.run_path(path, run_name='static_decoder')` para reutilizar `Reader`, `safe`, `ops`, `caches` e `instructions(words)` sem reler payloads ou regravar os resultados. `words` é uma lista de dicionários `{'opcode': byte, 'arg_byte': byte}`. O script 08 comparou SHA-256 dos três outputs antes/depois desse carregamento e confirmou ausência de alterações. Evidência em `opcode-map-correction.json`; fontes primárias preservadas. O script 07 registra a migração aplicada e não faz parte da ordem normal de reprodução 01–06/08.
