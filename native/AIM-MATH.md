# Modelo matemático da mira

Este documento descreve os cálculos usados pela mira em `rook.cpp`. As expressões são do controlador implementado; elas não implicam previsão de movimento futuro nem garantem acerto. O módulo isolado de pesquisa preditiva é independente e não está ligado a este controlador.

## 1. Projeção do alvo

Um ponto mundial `p = (px, py, pz)` é transformado para coordenadas da câmera pela matriz `view`:

```text
x = px·view[0] + py·view[3] + pz·view[6] + view[9]
y = px·view[1] + py·view[4] + pz·view[7] + view[10]
z = px·view[2] + py·view[5] + pz·view[8] + view[11]
```

O ponto só é projetado se `z < -0.001`, isto é, à frente da câmera segundo a convenção da matriz. Para dimensões da viewport `W × H` e escalas de projeção `sx`, `sy`:

```text
screenX = W/2 + (W/2)·sx·x/(-z)
screenY = H/2 - (H/2)·sy·y/(-z)
```

O erro de mira, em pixels, é medido do centro da viewport:

```text
ex = screenX - W/2
ey = screenY - H/2
distância = √(ex² + ey²)
```

A seleção do ponto acompanha a opção do menu: centro do corpo na posição local `y = 1.0` ou ponto de cabeça estimado em `y = 1.55`, transformado pela pose da entidade. A segunda opção é uma aproximação geométrica, não um osso anatômico identificado.

## 2. Erro em pixels para ângulo

Para um campo de visão vertical de calibração `F` graus e altura calibrada `Hc`, a distância focal equivalente em pixels é:

```text
f = (Hc/2) / tan(F·π/360)
```

Com a escala da projeção atual (`sx`, `sy`), os erros na tela viram ângulos por:

```text
θx = atan(ex / ((W/2)·sx))
θy = atan(ey / ((H/2)·sy))
```

A calibração medida armazena ganhos `gx`, `gy` em contagens de mouse por pixel para seu FOV. O comando angular equivalente é:

```text
dx = θx · f · gx
dy = θy · f · gy
```

Usar `atan` desfaz a relação perspectiva da projeção; assim o erro angular não depende linearmente do zoom. O perfil é escolhido pelo FOV atual, com tolerância de `0.6°`. Sem perfil compatível, usa-se o perfil base, cuja equivalência de sensibilidade em outras armas/zooms não está demonstrada. Armas diferentes com o mesmo FOV também não são distinguíveis por essa seleção.

## 3. Suavização e limites por atualização

Se a suavidade configurada for `τ` milissegundos e o intervalo entre quadros for `Δt`, a fração da correção aplicada é:

```text
α = 1                              se τ ≤ 0
α = 1 - exp(-clamp(Δt, 0, 100)/τ)  caso contrário
```

O ganho proporcional atual `k = 0.6` dá a correção preliminar `d = k·α·(dx,dy)`. Ela é limitada por um orçamento angular que cresce com o tempo do quadro:

```text
θlim = min(2°, 100°/s · clamp(Δt, 0, 50 ms))
θd = √((dₓ/(f·gx))² + (dᵧ/(f·gy))²)
```

Se `θd > θlim`, os dois componentes de `d` são multiplicados por `θlim/θd`. A expressão de `θd` é calculada após o ganho e a suavização na implementação. Além do limite angular, `speed` limita o comprimento do vetor de contagens por quadro. As partes fracionárias das contagens são carregadas ao quadro seguinte para reduzir erro de truncamento.

Suavidade `0` desliga apenas o filtro exponencial adicional: o ganho `0.6`, o limite angular e o limite de velocidade continuam valendo. `smooth_ms` é uma constante de tempo, não um atraso fixo.

## 4. Zona de parada e estabilidade

O controlador usa a distância `√(ex²+ey²)` e uma histerese:

```text
entra na zona de parada quando erro ≤ 0.65 px
permanece parado até erro > 1.25 px
```

Depois de enviar movimento não nulo, aguarda pelo menos `35 ms` e uma alteração observada na base de rotação da câmera (`max |viewatual[i] - viewsalva[i]| > 10⁻⁵`) antes de permitir outro comando. A alteração não identifica sua causa: movimento manual ou recuo também podem mudar a câmera. Trocas de FOV aguardam `80 ms` de estabilidade, com tolerância de `0.05°`.

Ao perder o alvo retido enquanto a ativação permanece pressionada, a nova aquisição espera `300 ms`. A primeira aquisição e a retenção de um alvo válido não têm essa pausa.

## 5. O que o modelo não calcula

O controlador de runtime usa a posição observada no quadro atual e realimentação pela câmera. Ele **não** estima velocidade por Kalman, não extrapola a trajetória, não resolve a equação analítica de interceptação de projétil e não compensa aceleração. Essas técnicas pertencem ao ambiente matemático de pesquisa independente; seus resultados não alimentam `rook.cpp`.

## Referências no código

- Projeção: `Camera::project`.
- Suavização: `smoothingAlpha`.
- Conversão angular e comando limitado: `angularMouseDelta`, `boundedCorrection`.
- Zona de parada: `aimDeadzone`.
- Estabilidade e troca de alvo: `CameraFeedbackGate`, `ZoomStability`, `TargetSwitchGate`.