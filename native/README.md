# aeon

Execute `Aeon.exe`. Insert mostra ou oculta o menu; F8 encerra.

O titulo aeon usa Mom's Typewriter, de Christoph Mueller. Os controles usam Poppins Medium, com a licenca OFL incluida na pasta fonts. As fontes sao carregadas somente neste processo, sem instalacao no Windows. Mantenha a pasta `fonts` junto ao executavel.

Fonte original: https://www.dafont.com/moms-typewriter.font
O arquivo original foi preservado. `fonts/MTReadme.txt` contem a permissao de redistribuicao e deve acompanhar a fonte.

`branding.json` registra se a familia correta foi selecionada pelo Windows; uma substituicao silenciosa de fonte e rejeitada.

O codigo C++20 esta em `rook.cpp`. Compilar com Zig 0.14.1: `./build.ps1 -Zig C:/caminho/zig.exe`. O arquivo de calibracao e as configuracoes ficam ao lado do executavel.

O painel de 770x557 usa a paleta ameixa documentada no DESIGN.md do projeto de referencia: fundo #0d0c10, barra #111015, paineis #151219, selecao #342838, destaque #756079 e foco #b7a1bd. Navegacao, abas, grupos, bordas finas e controles compactos seguem o mesmo padrao visual, com as paginas combate, visuais e ajustes correspondendo aos recursos existentes. A previa do ESP e ilustrativa.

`Aeon.exe --preview` renderiza uma imagem local design-preview.bmp da interface, sem leitura do jogo nem entrada automatizada. O alinhamento em movimento e a convergencia da mira C++ continuam sem confirmacao visual nesta rodada.
