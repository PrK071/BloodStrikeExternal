# Identidade do bloco CameraProjection — integração estática

Data: 22/10/2026. Amostra em disco: `E:\SteamLibrary\steamapps\common\BLOODSTRIKE\Engine\Binaries\Win64\BloodStrike.exe`, SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. Cada script que abre o PE verifica esse hash. Base preferencial `0x140000000`; endereços abreviados são RVAs. Não houve execução do alvo, acesso a processo ou alteração dos arquivos audit-v4.

## Resultado e confiança

**Não foi fechada a identidade entre `[contexto+0xb8]` do callback CameraProjection e o destino dos escritores da matriz.** A nova evidência identifica com confiança alta o dono virtual de `0x222ed0`: **`Messiah::VulkanShader`**, slot `+0x18` da tabela `0x4e549a8`. Isso explica por que a pesquisa por callers diretos dessa rotina não fornece a origem do contexto.

A cadeia até ICamera continua incompleta. Não há evidência nova que autorize chamar +0xfa0 de campo de ICamera, equiparar objeto do vcall +0x70 a ICamera ou identificar a matriz com a imagem final.

| Estado | Conclusão |
|---|---|
| Alta, local | `0x222ed0` é slot +0x18 da tabela com RTTI `Messiah::VulkanShader` |
| Alta, local, já documentada na V4 | O segundo argumento original desse método chega como RDX do callback do registro, via `0x7dac30` e `0x766370` |
| Alta, local, já documentada na V4 | Callback `0x1abd000` copia 64 bytes de `[[RDX+0xb8]+0xfa0]` |
| Alta, local, já documentada na V4 | Escritor `0xc47f9c` copia saída de vcall +0x70 para `[[[arg2+8]+0x30]+8]+0xfa0` |
| Aberta | Identidade entre os dois arg2/contextos e entre seus blocos |
| Aberta | Tipo dinâmico do objeto `[[arg2+8]+0x10]` do escritor |
| Aberta | Ligação independente desse bloco de renderização com o ICamera refletido |

## 1. Dono virtual do consumidor

A pesquisa de ponteiros absolutos encontra o valor VA preferencial `0x140222ed0` em `0x4e549c0`. Recuando sobre entradas executáveis contíguas, a tabela começa em `0x4e549a8`; a entrada observada é +0x18. O QWORD anterior em `0x4e549a0` aponta para COL `0x6e1bc40`.

O COL contém assinatura 1, offset de subobjeto 0, deslocamento de construção 0, TypeDescriptor RVA `0x7de3708`, CHD RVA `0x6e1bc68` e self RVA `0x6e1bc40`. O nome em TD+0x10 é `.?AVVulkanShader@Messiah@@`. Bytes completos e offsets de arquivo estão em `vulkan-shader-rtti.json`.

A rotina `0x222b00` instala essa tabela em `[RBX]` em `0x222b92`/`0x222b99`. Os caminhos `0x222db0` e `0x262f20` também instalam a mesma tabela em `[RCX]` e depois limpam/liberam campos. Esses usos corroboram a tabela de classe; os campos +0xb8 dessas rotinas são relativos ao próprio shader e não foram confundidos com o segundo argumento contexto de `0x222ed0`.

Isso é uma distinção importante: **self do shader ≠ contexto passado em RDX**. O RTTI de self não tipa automaticamente o contexto ou o seu campo +0xb8.

## 2. Callers e ponto onde a proveniência para

A busca sobre seções executáveis por E8/E9 rel32, com verificação de limite de instrução dentro de RUNTIME_FUNCTION, não encontrou caller direto de `0x222ed0` ou de `0xc46ca0`. A busca por QWORD absoluto encontrou a entrada virtual de `0x222ed0` acima, mas nenhum QWORD absoluto de `0xc46ca0`.

A varredura de formas RIP LEA/MOV recuperou as instalações da tabela VulkanShader; não recuperou endereço de `0xc46ca0` nessa cobertura. Não se interpreta ausência nessas formas como rotina inacessível. Chamadas virtuais, tabelas relativas, aliases e entradas de unwind divididas podem impedir um xref direto simples.

A proveniência concreta permanece:

`VulkanShader::método_slot18(self, contexto, ...)`

`contexto → arg2 original de 0x222ed0 → adapter 0x7dac30 → dispatcher 0x766370 → callback RDX`

`callback → [contexto+0xb8] → bloco+0xfa0..+0xfd0`

Falta localizar e tipar um callsite virtual efetivo desse método, carregando esse contexto, ou um escritor de contexto+0xb8 que demonstre por fluxo a origem do bloco.

## 3. Escritores de +0xb8: catálogo e candidatos eliminados

`04-b8-stores.py` catalogou **2065 stores QWORD da forma REX.W MOV [base+disp32 0xb8],registrador**, validados por decodificação em registros unwind. O catálogo não equivale a 2065 escritores do contexto: inclui stack, estruturas sem relação, ponteiros de tabela, vetores e ownership. O deslocamento isolado foi usado apenas para gerar candidatos.

Um filtro exploratório por loads próximos destacou `0x7593e0`. A inspeção completa mostra que `0x75953c` grava `[R14+0xb8]=[R15+8]`, enquanto `0x759531` grava `[R14+0xb0]=[R15]`. Antes há incremento de refcount `[ponteiro+8]`; depois decrementos e chamadas virtuais de destruição `[vtable]` e `[vtable+8]`. Esse padrão é coerente com par payload/controle de ownership. **Não foi promovido a escritor do contexto CameraProjection.** A evidência está em `context-candidate-7593e0.json`.

Outros trechos próximos ao produtor foram lidos em `selected-unlinked-functions.json`:

- `0x7823b0` move vários campos de uma estrutura para outra e zera a origem, incluindo +0xb8/+0xc0/+0xc8. O move de +0xb8 sozinho não identifica a estrutura como contexto do shader.
- `0xc43fb0` grava +0xb0/+0xb8 de um objeto depois de inserções em coleções; não houve alias demonstrado com arg2 de `0x222ed0`.
- `0xc562d0`, `0xc56500` e `0xc579f0` armazenam em +0xb8 resultados de criação/configuração de recursos, próximos a alocações pequenas e descritores. Não foi recuperada ligação com o bloco de 64 bytes em questão.
- `0xc57650` inicializa +0xa8/+0xb0/+0xb8 com o mesmo registrador zerado; não há identificação do contexto.
- `0xc610d0` permuta ponteiros +0xa8..+0xe0. A permutação não fornece a origem inicial nem a tipagem necessárias.

O filtro `06-prioritize.py` é heurística lexical e não realiza SSA, liveness ou prova de fluxo através de calls/branches. Seu resultado não constitui evidência positiva de identidade. Foram preservados o catálogo integral e os trechos selecionados para evitar que candidatos não resolvidos desapareçam da auditoria.

## 4. Fluxo recuperado e elo ausente

O escritor V4 de entrada lógica `0xc46ca0` tem fluxo local:

`objeto_virtual = [[arg2_escritor+8]+0x10]`

`bloco_destino = [[[arg2_escritor+8]+0x30]+8]`

`bloco_destino[0xfa0:0xfe0] = 64 bytes retornados por vcall objeto_virtual,+0x70`

O callback tem fluxo local:

`bloco_origem = [arg2_VulkanShader+0xb8]`

`output[0:0x40] = bloco_origem[0xfa0:0xfe0]`

O elo necessário é uma atribuição ou sequência de chamadas que prove:

`[arg2_VulkanShader+0xb8] == [[[arg2_escritor+8]+0x30]+8]`

Essa igualdade **não foi demonstrada**. A rotina de inicialização `0x789fe0` também possui múltiplos donos de blocos; a identidade inicial escrita em +0xfa0 pode existir em vários objetos simultaneamente. Compartilhar inicializador, tamanho ou posição da matriz não fecha o alias.

O slot +0x70 do objeto_virtual não pode ser chamado de getter de PerspectiveCamera apenas porque outra classe conhecida possui operação compatível nesse slot. Seriam necessários vptr instalado/RTTI, construção tipada ou conversão demonstrada nesse caminho específico.

## 5. Cobertura, reprodução e corte

Scripts de reprodução foram salvos nesta pasta desde o começo. `01-callers.py` é uma tentativa exploratória por regex não sobreposta; **os resultados autoritativos de E8/E9 são os de `02-overlap-callers.py`**, que examina todas as ocorrências sobrepostas e valida instruções. `03-table-rip.py` pesquisa formas RIP e mostra a origem da tabela. `04-b8-stores.py` gera o catálogo bruto. Scripts 05–09 fazem triagem textual e inspeção, e 10 grava evidência final da tabela/RTTI e funções selecionadas.

Os scripts só leem o executável e gravam arquivos nesta nova pasta. Usam RawPE/iced-x86 da auditoria V2 sem alterar o módulo. Executar com o Python de análise `C:\Users\luiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

Critério de corte: recuperar xrefs diretos/ponteiros das duas entradas, identificar o dono concreto da entrada virtual, catalogar a família de stores +0xb8 e inspecionar candidatos de carga próxima e rotinas junto ao produtor. Não houve tentativa de declarar negativos globais sobre mais de dois mil stores sem análise de aliases. Stores vetoriais abrangendo +0xb8 a partir de +0xb0, cópias de bloco, ponteiros ajustados, código sem unwind, outras codificações e outros módulos continuam fora dessa busca específica.

A próxima prova útil deve partir de um callsite virtual do slot VulkanShader +0x18 com contexto identificado, ou de uma estrutura/contexto tipada populada pelo produtor. Até esse elo existir, o material sustenta caminhos locais de renderização e um backlog concreto de investigação, não uma cadeia externa completa de aquisição e projeção.
