# ICamera.GetScreenPointFromWorldPoint: corpo e contrato estático

Amostra SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. Somente leitura do PE/MPKs; nenhum processo do jogo, bytecode ou função nativa alvo foi executado.

## Nome ao corpo

A string **Messiah.ICamera.GetScreenPointFromWorldPoint** está no RVA **0x4f776f0**. O registro em **0x4f4f930** aponta a esse nome em **0x4f4f940** e seu adaptador de chamada em **0x4f4f980 → 0x93dde0**. A rotina 0x96e400 referencia diretamente esse registro para inicialização do método. O adaptador 0x93dde0:

- Usa ajuste assinado em **0x4f42a00**, cujo valor estático é **zero**.
- Chama o ponteiro em **0x4f429f8**, cujo valor estático é VA **0x140276300**.
- Recebe self em RDX e buffer de argumentos/retorno em R8; passa **R8+0xc** como entrada float3 ao corpo e copia os **12 bytes de retorno** para o início desse buffer.

O thunk **0x276300** preserva o endereço de saída RDX e chama **0x275db0**, passando self em RCX, saída em RDX e entrada float3 em R8. Logo o corpo foi recuperado por ligação de metadados, não por semelhança de aritmética.

Provas: native-projection-blocks.json, projection-wrapper-functions.json, projection-concrete-functions.json, screenpoint-member-cell.json, screenpoint-concrete.json, screenpoint-helper.json.

## Campos confirmados e aritmética

O corpo lê três floats da entrada e subtrai **camera+0x7c, +0x80, +0x84** respectivamente. Não lê origens/anchors inteiros nesse caminho. Chamando esses deltas dx,dy,dz:

```
X = (dx * m41c + dy * m428) + dz * m434
Y = (dx * m420 + dy * m42c) + dz * m438
Z = (dx * m424 + dy * m430) + dz * m43c
inv = 1 / max(abs(Z), float32(0.000001))
Xn = X * inv
Yn = Y * inv
angle = (FOV * float32(pi/180)) * float32(0.5)
alpha = 1 / tanf(angle)
w = float32(uint16(camera+0x408))
h = float32(uint16(camera+0x40a))
x = ((h * Xn) * alpha + w) * float32(0.5)
y = (h - (h * Yn) * alpha) * float32(0.5)
z = -Z if Z < 0 else float32(-1)
return (Q(x), Q(y), Q(z))
```

**Cada operação ADDSS/SUBSS/MULSS/DIVSS é float32 separada**, na ordem indicada; não fundir em FMA nem manter toda expressão em double. Os produtos/somas de X e Y aparecem intercalados no código, porém com a associação acima. `abs(Z)` apaga o bit de sinal e MAXSS limita o divisor. Os comportamentos SSE específicos de NaN e ambiente de arredondamento não foram generalizados para fórmula matemática ideal.

O campo **FieldOfView** está confirmado pela reflexão: registro0x4f43e60 → wrapper0x943d40 → membercell0x4f4b568 (ajuste zero0x4f4b570) → getter0x964160, `lea rax,[rcx+0x454]`. **Near** segue wrapper0x944a20/cell0x4f4c860/getter0x964240 → **+0x458**; **Far** segue0x945e10/cell0x4f4d8f8/getter0x9642e0 → **+0x45c**. **IsOrthographic** getter0x93be00 retorna **+0x418**; **OrthoScale** getter0x941240 retorna **+0x44c**. O corpo de world-to-screen não usa Near/Far/IsOrthographic/OrthoScale.

A interpretação horizontal/vertical de +0x408/+0x40a é sustentada pelo uso em x/y neste corpo, além do getter nomeado GetScreenSize já auditado na V4. Não se presume que esses WORDs coincidam com pixels físicos da janela ou client rect, particularmente sob escala da UI/resolução dinâmica.

### Tangente e quantização

A rotina matemática **0x426b930** recebe o ângulo float32 e retorna float32; possui aproximação racional ímpar, redução periódica e inversão -1/tan no quadrante alternado, consistentes com tanf. A identificação semântica é também corroborada pelo fallback Python do próprio jogo descrito abaixo, que usa explicitamente math.tan no mesmo ponto. Não foi feito ensaio executando essa rotina para prometer igualdade de ULP com uma biblioteca matemática externa.

A rotina **0x426b1c0**, chamada para cada coordenada depois de multiplicar por float32(10), usa **0x42952f0**. Este helper remove bits fracionários da mantissa: primeiro com parâmetro1 (trunca para múltiplos0.5), depois parâmetro0 (trunca para inteiro). Quando a segunda operação remove fração, soma +1 ou -1 conforme sinal. Para entrada finita ordinária, isso demonstra **arredondamento ao inteiro mais próximo, empate afastando de zero**. A rotina de projeção multiplica o retorno por float32(0.1).

```
Q(v) = float32(round_half_away_from_zero(float32(v * float32(10)))
               * float32(0.1))
```

Não usar round() do Python (empate para par). Valores especiais, overflow, ambiente FP alterado e diferenças de tanf exigem contrato separado. Constantes preservadas em screenpoint-math.json: pi/180=0.01745329238474369, epsilon=9.999999974752427e-7, .1=0.10000000149011612, .5=0.5,10=10,1=1,-1=-1. math-contiguous.json contém o helper de bits completo até retorno; RUNTIME_FUNCTION dividia o corpo e por isso round-classify-helper.json sozinho é incompleto.

## Corroboração Python e domínio de coordenadas

Busca literal limitada aos9.705 streams indexados encontrou5 módulos com o método; todos os resultados estão em literal-screenpoint-callers.json. Foram decodificados apenas71683 (CommonTopLogo),125644 (UIDirector),136897 (MarkTopLogo) e17226 (MHelper), com hashes reconferidos. MHelper17226 não possui esse termo.

**CommonTopLogo._UpdateMarkToplogo**, índice71683, marshal16356, carrega `MEngine.GetGameplay().Player.Camera` em offsets34–106 e chama o método nativo com `MType.Vector3(*self.mark_toplogo_pos)` em156–216. O corpo também lê camera.Transform.translation, mas não aplica esse valor ao argumento antes da chamada.

**CommonTopLogo.GetScreenPointFromWorldPointPython**, marshal17012, é uma implementação manual paralela:

- Obtém camera pela mesma cadeia em90–162 e ViewMatrix em164–186.
- Constrói world_pos de mark_toplogo_pos, subtrai **camera.GetOrigin()** em248–278 e aplica **ViewMatrix.transform_v** em292–316.
- Se componente z é negativa, retorna profundidade positiva por -z; caso contrário escolhe -1.
- Usa max(abs(z),1e-6), **math.tan(0.5*math.pi*camera.FieldOfView/180)** e fórmula x/y equivalente.
- Usa **MUI.GetScreenWidth/GetScreenHeight**, em vez dos WORDs lidos pelo corpo nativo, e não faz quantização explícita em décimos. Portanto corrobora a geometria, sem constituir espelho bit a bit.

**UIDirector.WorldToScreen**, índice125644, marshal90229, chama o mesmo método em150–172 quando worldpos já é Vector3; caso contrário cria `MType.Vector3(*worldpos)` em186–244. Não há correção de anchor anterior nessa função. Depois efetua escalas de UI; essas escalas não pertencem ao corpo ICamera recuperado.

**Contrato que permanece aberto:** o input nativo é float3 no mesmo frame dos floats de camera+0x7c. A semântica do produtor mark_toplogo_pos/worldpos e a conversão de uma posição absoluta `translation_float + anchor_integer` para esse input **não foi demonstrada**. Não subtrair anchors ou converter posições double por suposição. O nome WorldPoint não elimina esse limite.

## Relação com renderização

Este é um método geométrico explícito de ICamera utilizado por UI e marcas do gameplay. Sua aquisição lógica de câmera está ligada a Player.Camera nos callers. Isso reduz a necessidade de identificar CameraProjection para reproduzir **este método**, mas não prova equivalência com pixels finais sob câmera alternativa, jitter, escala, viewport parcial ou resolução dinâmica.

O slot **PerspectiveCamera+0x70**, implementação **0x485230**, simplesmente copia64 bytes de self+0x2d8..+0x318 para o buffer de saída. Está provado nesse tipo pela tabela RTTI da V4. O objeto do slot+0x70 no escritor CameraProjection continua sem tipo demonstrado, portanto os dois não foram equiparados.

Não há leitor externo implementado nesta etapa. Nenhum arquivo de ExternalCore/tests/README foi modificado.
