# Captura real — PID 10936

A leitura inicialmente falhou com WinError 5. Com o coletor elevado, a leitura funcionou.

- Imagem mapeada completa: 156.143.616 bytes; nenhuma lacuna de leitura.
- SHA-256 do dump: `3c0727c320c66ae35ca5c61bef8f8b577be301f9f76077954d86c371181e0fec`.
- Base desta execução: `0x7ff7a61d0000`; não reutilizar como endereço fixo.
- Registro: dois atores, duas posições decodificadas, categorias desconhecidas no menu.
- Câmera nativa Aurora: 1334 × 750; FOV da origem: 40; cópia de visão compatível.
- Passaram as checagens de RTTI, aliases e observações repetidas implementadas no coletor.

`BloodStrike.mapped-image.bin` contém a imagem virtual do módulo. O binário permanece local e está ignorado pelo Git; o manifesto preserva seu hash e as faixas lidas. Não é um PE reconstruído para execução nem um dump completo do heap. A captura foi sequencial com o jogo em execução; não é atômica.

`live-offsets.json` separa RVAs, campos e ponteiros observados nesta execução. Os offsets já existentes foram exercitados; não se derivaram novos offsets fixos de HP/equipe.

O quadro foi marcado como antigo pelo limite de idade do pipeline. HP, equipe, estado de vida, classificação de jogador, visibilidade, calibração e correspondência com os pixels finais continuam sem validação. Nenhum movimento de mira foi enviado.

A navegação automática até o treino não foi executada: a ferramenta de interface retornou `Computer Use native pipe is unavailable`, inclusive após reiniciar a conexão. Os dados desta pasta se limitam à observação no menu.
