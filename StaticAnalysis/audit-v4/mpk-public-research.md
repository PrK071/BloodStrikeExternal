# Pesquisa pública de implementação: MPK / MPKINFO da NetEase

Consulta: 2026-10-21. Escopo: documentação e código público para reconhecimento de cabeçalho/índice de arquivos de recursos em disco. Nenhuma ferramenta ou binário foi baixado ou executado; não houve acesso ao jogo/processo nem inspeção de arquivos locais.

## Achado principal: parser Rust aberto, apenas MPKINFO versão 1

O repositório público [fangfang1984/netease-messiah-tools](https://github.com/fangfang1984/netease-messiah-tools) se descreve como ferramentas para arquivos do motor Messiah, “primarily aimed towards Diablo Immortal”. A árvore do repositório lista uma pasta `mpk`. O código fonte textual acessível diretamente é [mpk/src/lib.rs](https://raw.githubusercontent.com/fangfang1984/netease-messiah-tools/main/mpk/src/lib.rs); o binário CLI está em [mpk/src/main.rs](https://raw.githubusercontent.com/fangfang1984/netease-messiah-tools/main/mpk/src/main.rs), e o pacote declara versão 0.1.0 em [mpk/Cargo.toml](https://raw.githubusercontent.com/fangfang1984/netease-messiah-tools/main/mpk/Cargo.toml). O repositório tem licença MIT conforme a página do projeto.

O próprio código implementa explicitamente **somente versão 1**: `MPKFileHeader::read_header` lê dois inteiros little-endian de 32 bits (`version`, `file_count`) e faz `assert!(version == 1)`; a leitura do índice também afirma “Currently only MPK Version 1 is supported”. Cada entrada tem comprimento de nome `u16`, bytes UTF-8 do nome, `offset:u32`, `size:u32`, `flags:u32`; `flags & 1` é interpretado como diretório e `flags >> 1` como número do pacote. O leitor deriva os arquivos de dados do nome-base de `.mpkinfo`: índice de pacote 0 corresponde a `<basename>.mpk`; os demais a `<basename><number>.mpk`. O script CLI recebe caminho do `.mpkinfo` e diretório de saída.

O leitor também inspeciona magic de cada payload e implementa no código casos `ZZZ4`, `CCCC` seguido de `ZZZ4`, e prefixo `E2 06` (descrito no comentário como zlib “mangled”). Para o ramo `CCCC`/`ZZZ4`, o próprio autor chama 20 bytes finais de “overhang” desconhecido e os ignora. Isso é descrição do comportamento publicado do parser, não validação independente de todos os arquivos. Fonte direta: [lib.rs, linhas exibidas pelo GitHub raw](https://raw.githubusercontent.com/fangfang1984/netease-messiah-tools/main/mpk/src/lib.rs).

## Script QuickBMS do autor

[Índice de scripts QuickBMS do autor](https://mirror.aluigi.org/quickbms_list.php) lista `netease_mpk.bms` como **“NetEase Ace Racer mpkinfo/mpk (script 0.2)”**, com ZZZ4/LZ4/LZMA. O link direto é [netease_mpk.bms](https://mirror.aluigi.org/bms/netease_mpk.bms), mas o navegador desta pesquisa recusou abrir o arquivo por seu MIME `application/octet-stream`. O conteúdo do script portanto não foi lido diretamente.

Há uma cópia textual parcial do parser versão 1 no tópico [Ace Racer MPK no ResHax](https://reshax.com/topic/9208-netease-ace-racer-mpk-archive-unpack-help/). O trecho postado pelo próprio `aluigi` lê `VER` (comentário `# 1`), contagem, e para cada entrada `name_length:u16`, nome, offset, size e file-number/flags; divide os bits baixos do campo final para obter o número de pacote e usa `<basename>.mpk`, `<basename>1.mpk`, etc. para endereçar os dados. No mesmo tópico, o autor esclarece que a ferramenta espera como entrada `.mpkinfo`, e que uma atualização 0.2 passou a lidar com compressão e pular diretórios. Esse trecho não é a revisão integral 0.2, então detalhes adicionais da revisão atual não podem ser presumidos.

O tópico documenta validação pelo autor do script em arquivos fornecidos de **Ace Racer Android APK 1.1.5**; no início houve um `.mpkinfo` que não correspondia ao `Resources6.mpk`, atribuído a mistura de versões. Essa é uma limitação concreta: índice e arquivos de dados precisam pertencer ao mesmo conjunto/versão. Não é teste em Blood Strike.

## MPKINFO versão 2: especificação superficial, campos sem semântica

[XeNTaXWiki: NetEase MPK/MPKINFO](https://wiki.xentax.spektr.name/index.php/NetEase_MPK_MPKINFO) descreve endian little, sem signature, e uma forma rotulada versão 2: `u32 version`, `u32 number_of_files`, depois registros de 20 bytes, com campos `8 bytes unknown`, `u32 file size?`, `u32 file type?`, `4 bytes unknown`. A mesma página avisa que versão 1 difere de versão 2 e associa o formato a jogos Messiah, mas lista Ace Racer e Vive Le Football como exemplos. A especificação marca tamanho/tipo como incertos e deixa dois campos desconhecidos; não define relação suficiente entre índice e offsets/nome dos payloads para implementar um parser confiável de V2. Os links QuickBMS dessa página são um script `netease_mpk.bms` e um `mpk.bms`; o segundo link histórico de ZenHAX retornou 404 nesta consulta.

O parser Rust público acima não fecha essa lacuna: o código aborta para qualquer versão diferente de 1. Não se deve confundir o layout V1 do parser Rust/trecho QuickBMS com a tabela V2 simplificada da wiki.

## V3 / Where Winds Meet: relato de script, sem código legível nesta consulta

No tópico [ResHax: recursos de Where Winds Meet](https://reshax.com/topic/1498-has-anyone-know-how-to-get-audio-resources-in-netease-new-game-where-winds-meet/), o autor da pergunta relata MPK versão 3 e que `mpkinfo` seria obsoleto para alguns dados. `wq223` publicou que seu anexo `mpk.py` (7.72 kB) parseia arquivos de patch de Where Winds Meet; o arquivo aparece na página, mas o link de anexo retornou 404 quando aberto. Comentários posteriores descrevem `Resource*.mpk`/`Patch*.mpk`, índices em `mpkinfo/mpkdb` com FileID/Size/Offset/MpkIndex, substituição por FileID e vários esquemas de compressão, mas são posts de fórum e não código legível acessível nesta consulta. Eles não devem ser tratados como especificação completa ou universal.

Logo, a evidência pública consultada indica pelo menos três contextos incompatíveis ou diferentes: parser Rust V1, wiki V2 com campos incertos e relatos de WWM V3 com `mpkdb` para alguns dados. O anexo V3 não foi obtido nem executado. Não há, neste conjunto de fontes, código legível e validado para V2/V3.

## Compatibilidade e resposta para Blood Strike

Nenhuma fonte acima identifica Blood Strike, Steam build 25981220, patch 126 ou o SHA-256 alvo como caso testado. A implementação Rust declara foco primário em Diablo Immortal; o script QuickBMS declara Ace Racer; os relatos de V3 são sobre Where Winds Meet. A wiki lista jogos distintos. Assim, são referências para reconhecer famílias/formas do container em outros títulos, não prova de compatibilidade com recursos de Blood Strike.

Para reconhecimento offline, o apoio mais sólido aqui é o layout V1 explícito do parser Rust e a confirmação textual do formato V1 no post de Ace Racer. V2 continua parcialmente desconhecida; V3 tem menções de comunidade sem código textual inspecionável. Não é justificável inferir versão, nomes, offsets ou compressão do conjunto local apenas pela extensão `.mpk`/`.mpkinfo` ou pelo fato de o motor ser chamado Messiah.

## URLs diretas consultadas

- [Repositório GitHub](https://github.com/fangfang1984/netease-messiah-tools) — público; descreve foco Diablo Immortal.
- [Código `mpk/src/lib.rs`](https://raw.githubusercontent.com/fangfang1984/netease-messiah-tools/main/mpk/src/lib.rs) — texto aberto; implementa V1.
- [CLI `mpk/src/main.rs`](https://raw.githubusercontent.com/fangfang1984/netease-messiah-tools/main/mpk/src/main.rs) — texto aberto; recebe `.mpkinfo` e diretório de saída.
- [Manifesto `mpk/Cargo.toml`](https://raw.githubusercontent.com/fangfang1984/netease-messiah-tools/main/mpk/Cargo.toml) — texto aberto; crate `messiah-mpk` versão 0.1.0.
- [Mirror: índice QuickBMS](https://mirror.aluigi.org/quickbms_list.php) — lista `netease_mpk.bms` versão 0.2 e tipos de compressão suportados.
- [QuickBMS direto](https://mirror.aluigi.org/bms/netease_mpk.bms) — tentou abrir; MIME binário bloqueado pela interface; código não inspecionado.
- [ResHax: Ace Racer](https://reshax.com/topic/9208-netease-ace-racer-mpk-archive-unpack-help/) — trecho textual V1 e discussão de validação em APK 1.1.5.
- [XeNTaXWiki: descrição V2](https://wiki.xentax.spektr.name/index.php/NetEase_MPK_MPKINFO) — documentação comunitária parcial, campos desconhecidos.
- [ResHax: WWM V3 e `mpk.py`](https://reshax.com/topic/1498-has-anyone-know-how-to-get-audio-resources-in-netease-new-game-where-winds-meet/) — menciona V3/mpkdb e anexo; link do código retornou 404.
- [GitHub xforce antigo](https://github.com/xforce/netease-messiah-tools) — 404; a discussão ResHax diz que o projeto foi removido. O fork atualmente aberto é o de `fangfang1984` listado acima.
