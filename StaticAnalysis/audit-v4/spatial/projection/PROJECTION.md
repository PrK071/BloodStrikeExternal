# Projeção e viewport — investigação estática complementar V4

Esta análise acrescenta evidência sem modificar `SPATIAL.md` nem arquivos anteriores. Mesma amostra `BloodStrike.exe`, SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`, base preferencial `0x140000000`. Leitura do arquivo PE como dados. Endereços apresentados são RVAs; VAs nos JSON são preferenciais, sem observação de runtime.

## Conclusão

`GetMainCameraViewProjection` é um **método registrado para `DecalCameraData`**, com implementação recuperada. Ele constrói um `Messiah::PerspectiveCamera` temporário a partir de campos de um objeto obtido por cadeia global, calcula 16 floats e os converte para 16 doubles. Há ligação concreta ao getter refletido **`Messiah.ICamera.GetScreenSize`** e ao armazenamento já identificado como `ICamera.ViewMatrix`.

Esse resultado amplia a viabilidade estática, mas não prova que a matriz calculada seja idêntica à da imagem final: o temporário recebe **2048×2048**, e a rotina desvia para identidade em condições específicas. O mecanismo não é um `ICamera.Project` nem demonstra projeção de ponto, clipping ou aplicação final de viewport.

`CameraProjection` pertence a **outro registro de callbacks com nome e tamanho**, cujo callback copia 64 bytes de uma estrutura indireta. Não foi demonstrado que seu objeto de origem seja o ICamera anterior nem que o conteúdo coincida com o resultado do método de DecalCameraData.

## 1. Nome → registro → wrapper → implementação

A string `GetMainCameraViewProjection` está em `0x5ba6f28`. Não há ponteiro absoluto QWORD para ela no arquivo. A referência RIP validada está em `0x314d934`, bytes `48 8d 0d ed 95 a5 02`, dentro da função de registro `0x314d4c0`.

O início dessa função carrega `DecalCameraData` (`0x5ba6ec8`) em `0x314d4d2` e `MStruct` em `0x314d4d9`; mensagens como `Asyncore::pybase_object_impl<struct Messiah::DecalCameraData>::add_method` aparecem no mesmo fluxo. Em `0x314d92f`, chama `0x3150100`, que retorna o endereço do container `0x8e76be8`. O registro montado contém o nome em +0, o callback `0x314e7f0` em +8, o valor 1 em +0x10 e zero em +0x18. O caminho sem realocação copia 0x20 bytes para `[container+8]` e avança esse cursor em 0x20 (`0x314d95f`–`0x314d96e`); o caminho cheio usa `0x2131d0`.

O callback `0x314e7f0` verifica `[self+0x20]` e rejeita argumentos adicionais, com strings de erro correspondentes. Em `0x314e850` passa o impl em RDX, a saída temporária em RCX e chama `0x314c250` em `0x314e858`. Depois cria um objeto de retorno via `0x1cbb430` e copia oito blocos de 16 bytes para o payload obtido em `[retorno+0x20]`: 128 bytes no total. A implementação `0x314c250` usa a saída RCX e não desreferencia o impl RDX recebido nesse caminho.

## 2. Objeto-fonte e câmera temporária

Na implementação `0x314c250`:

| RVA | Operação observada |
|---|---|
| `0x314c27b` / `0x314c282` | constrói temporário no stack por `0x4843c0` |
| `0x314c288` | lê ponteiro global em `0x80d5980` |
| `0x314c28f` | lê primeiro `+0x58`; testa nulo |
| `0x314c29c` | lê segundo `+0x58` |
| `0x314c2a0` | lê objeto em `+0xd88`; testa nulo |
| `0x314c2b4` | testa byte objeto `+0x418`; se não zero, retorna identidade |
| `0x314c306`–`0x314c319` | consome float objeto `+0x454`, multiplica por constante e chama slot temporário `+0xc0` |
| `0x314c322` | chama `0x2762a0` sobre objeto-fonte; getter GetScreenSize comprovado abaixo |
| `0x314c32e`–`0x314c33d` | chama slot temporário `+0x128` com EDX=R8D=`0x800` |
| `0x314c34a`–`0x314c359` | consome float objeto `+0x458` via slot temporário `+0xd0` |
| `0x314c366`–`0x314c375` | consome float objeto `+0x45c` via slot temporário `+0xc8` |
| `0x314c382`–`0x314c390` | passa endereço objeto `+0x41c` ao slot temporário `+0x68` |
| `0x314c39a`–`0x314c3a8` | chama slot `+0x90`, com R8=0 e RDX apontando aos quatro bytes copiados por GetScreenSize |
| `0x314c3c0`–`0x314c3ea` | converte 16 floats retornados para 16 doubles na saída |

As guardas verificam apenas o primeiro `+0x58` e o resultado `+0xd88` nessa sequência; o segundo `+0x58` é desreferenciado sem guarda local. A cadeia foi observada em instruções, não validada em memória, e não recebe aqui um nome global presumido.

A atribuição de tabela em `0x48446a`–`0x484471` instala `0x4ebf848`. Seu COL em `0x6e389d0` aponta ao TypeDescriptor `0x7cac678`, nome `.?AVPerspectiveCamera@Messiah@@`. Os bytes de COL, ponteiro e TypeDescriptor estão em `perspective-rtti-and-slots.json`.

Slots da tabela recuperados: `+0x68 → 0x4850a0`; `+0x90 → 0x483720`; `+0xc0 → 0x485530`; `+0xc8 → 0x4853d0`; `+0xd0 → 0x485440`; `+0x128 → 0x485270`. O slot `+0x90` lê o endereço retornado pelo slot `+0x28` (`0x178ba0`: `lea rax,[rcx+8]; ret`) e chama `+0x70` (`0x485230`), que copia quatro blocos de 16 bytes do temporário `+0x2d8` até `+0x308`. Há multiplicações e somas em double e conversão para float na composição. Isso sustenta composição matricial, sem impor rótulos linha/coluna ou handedness.

O fallback escreve doubles 1.0 em saída +0, +0x28, +0x50, +0x78 e zeros nos demais elementos: identidade 4×4. Portanto, a existência de uma saída matricial não garante que dados reais de câmera tenham sido obtidos.

## 3. GetScreenSize: cadeia refletida concreta

`Messiah.ICamera.GetScreenSize` (`0x4f5ea18`) possui referências de metadados. O bloco de função em torno de `0x4f58a40` contém esse nome em `0x4f58a50` e o wrapper `0x9553f0` em `0x4f58a90`. Esse wrapper lê ajuste assinado de `0x4f6a0d0`, soma ao argumento RDX e chama o ponteiro de `0x4f6a0c8`.

A célula contém VA preferencial `0x1402762a0` e ajuste zero: bytes `a0 62 27 40 01 00 00 00 00 00 00 00 00 00 00 00`. O getter `0x2762a0` copia WORDs do objeto +0x408 e +0x40a para uma estrutura de quatro bytes e a retorna por ponteiro. Evidências completas: `screen-method-data.json`, `screen-getter-wrappers.json`, `screen-getter-concrete.json`.

Isso fecha uma ligação de nome de ICamera ao objeto consumido pelo método de DecalCameraData. Além disso, esse objeto fornece +0x41c, exatamente o armazenamento associado ao getter refletido ICamera.ViewMatrix no relatório espacial anterior. Não foi determinada nesta etapa a ordem largura/altura dos WORDs apenas pelo nome GetScreenSize.

Os nomes `Messiah.ICamera.SetScreenSize` e `GetScreenSize` são metadados concretos; o inventário adicional de viewport contém também strings de renderizador, Vulkan, shaders e UI. A mera presença desses outros nomes não identifica o viewport exibido ao usuário.

## 4. CameraProjection: callback de cópia distinto

A string `CameraProjection` está em `0x55aef10`. Não há referência absoluta QWORD encontrada. Sua referência RIP validada é `0x1a8c42c`: `48 8d 05 dd 2a b2 03`, na rotina `0x1a8bf50`.

Em `0x1a8c433` prepara comprimento do nome `0x10`; em `0x1a8c43b` prepara R8D=`0x40`; em `0x1a8c445` prepara callback `0x1abd000`; em `0x1a8c450` chama `0x750070`. Esse helper registra callback, nome copiado, hash, índice e tamanho WORD em slots globais de 0x18 bytes na região `0x80f6dc8`, sob trava. As inscrições vizinhas incluem `CameraClipToPrevClip`, `TSAAParams` e `OnePassShadowViewProjArray`. É um registro de fornecimento de dados nomeados coerente com contexto de renderização; o nome fonte exato do sistema não foi reconstruído.

O callback `0x1abd000` executa:

- `0x1abd000`: `48 8b 82 b8 00 00 00` — lê RAX de `[RDX+0xb8]`.
- `0x1abd007`–`0x1abd01c`: lê quatro XMM de `[RAX+0xfa0]`, `+0xfb0`, `+0xfc0`, `+0xfd0`.
- `0x1abd023`–`0x1abd02e`: copia esses 64 bytes para RCX, offsets 0, 0x10, 0x20 e 0x30; retorna em `0x1abd032`.

A origem concreta do argumento RDX de cada invocação e os escritores de origem `+0xfa0` não foram fechados. Não é correto converter esse deslocamento em um campo de ICamera, nem afirmar que o bloco corresponda à mesma matriz de GetMainCameraViewProjection. O callback é consumidor de armazenamento e produtor de saída; o produtor original do armazenamento permanece em aberto.

## 5. Limites e método de busca

Foram buscadas referências QWORD absolutas aos dois nomes e formas RIP LEA/MOV com ModRM RIP-relative em seções executáveis. Candidatos foram validados ao decodificar as funções unwind contendo-os. Cada nome teve uma referência RIP validada nessa cobertura. Isso não é prova de ausência de referências calculadas, strings comprimidas, outras formas de instrução, módulos externos ou aliases.

Não se presume que PerspectiveCamera temporária reproduza câmeras ortográficas, câmera de mira, câmera virtual, câmera de espectador, jitter temporal, resolução dinâmica, subviewport ou imagem final. O ramo `+0x418` e o tamanho fixo 2048×2048 são diferenças explícitas a preservar. Não foi aplicada fórmula de projeção de ponto nem assumida convenção de matriz.

Todos os JSON nesta pasta incluem os RVAs, bytes e offsets de arquivo das instruções relevantes. `ref-functions.json` guarda as funções de registro completas; `linked-functions.json` os wrappers e registrador; `main-viewprojection-implementation.json` a implementação; `camera-temp-and-adjustment.json` a construção do temporário; `temporary-vtable*.json` e `perspective-rtti-and-slots.json` os slots e RTTI. Scratch de reprodução em `work\spatial\projection_*.py`.
