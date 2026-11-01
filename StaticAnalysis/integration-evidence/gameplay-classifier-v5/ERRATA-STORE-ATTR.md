# Errata: resolução de `STORE_ATTR`

Data: 2026-11-01. Aplicável somente às interpretações de nomes de atributo; não altera bytes de MPK, IDs de stream, hashes ou artifacts selados.

## Erro nesta investigação

O primeiro rascunho atribuiu incorretamente `owner` aos stores em `AvatarModel.Load` nos offsets de bytecode 1040 e 1114. A tabela de nomes foi resolvida com `arg >> 1`, o que não é a regra de `STORE_ATTR` em CPython 3.14. A regra correta é índice direto em `co_names`:

- Índice MPK `143510`, `AvatarModel.Load`, offset 1040, argumento 32: `co_names[32] == "position"`.
- Índice MPK `143510`, `AvatarModel.Load`, offset 1114, argumento 33: `co_names[33] == "yaw"`.
- Índice MPK `122267`, `BaseModel.__init__`, offset 4, argumento 0: `co_names[0] == "owner"`; essa atribuição permanece confirmada.
- Índice MPK `68957`, `SimpleModel.Load`, offset 1528, argumento 40: `co_names[40] == "owner"`; nesse store, o objeto-alvo na pilha é `self.model`, e o valor é `self.owner`.

Os três streams foram decodificados com hash verificado e parse marshal até EOF. Os detalhes e identificadores estão em `11-corrected-owner-store-attr-audit.json`.

## Leitores legados afetados

Os arquivos abaixo são preservados sem alteração, por serem evidência histórica selada. A errata deve acompanhar qualquer reutilização de seus campos `resolved_name`/`name` associados a stores:

- `StaticAnalysis/integration-evidence/actor-classification/01_parse_actor_modules.py:29` usa `names[arg >> 1]` para `STORE_ATTR`. Portanto, `STORE_ATTR.resolved_name` no `actor-classification/resource-code-static.json` não é confiável sem resolver o argumento original de novo. As conclusões no README desse diretório sobre offsets 670, 830, 886, 1146 e 1348 são `LOAD_ATTR`; essa errata não as afeta.
- `StaticAnalysis/integration-evidence/gameplay/python-model-links/05_python_model_links.js:23,26` usa `names[arg >> 1]` também para `STORE_ATTR`. Portanto, nomes desse opcode em `gameplay/python-model-links/model-link-static.json` não são confiáveis; a errata não altera as instruções, offsets, bytes ou hashes armazenados.
- `StaticAnalysis/integration-evidence/camera-binding/01-decode-binding.py:18` e `24-decode-callers.py:18` usam `names[arg]` para stores, então não apresentam esse erro específico.

Não editei, regenerei ou alterei manifests/artifacts selados. O resolvedor corrigido de V5 está no arquivo `07_owner_tag_chain_static.py`; a auditoria focada adicional está em `11-corrected-owner-store-attr-audit.json`.
