# Scripts exploratórios preservados

`spatial/` preserva os scripts usados pela pesquisa delegada, sem reescrever seu código após a extração. Eles não são um runner portátil: usam a pasta original da investigação e abrem `work\spatial\scan.py` relativamente ao diretório original do chat. Para reproduzir essa exploração no mesmo ambiente, os originais continuam em `work\spatial\` do chat; fora dele é necessário ajustar esses caminhos ou reconstruir essa árvore. Não executam código do jogo: a reutilização por `exec` é de um prefixo do script de análise local.

A reprodução dos bytes dos artefatos entregues não depende desses caminhos: use `StaticAnalysis/verify_v4.py --sample <executável>`. A seleção central é reproduzida por `audit_v4.py`. Ambos exigem `audit_v2.py`, iced-x86 1.21.0 e Capstone (distribuição local 5.0.9, módulo Python reportando 5.0.7), em Python 3.12.14 x64 neste ambiente. O executável deve ser fornecido separadamente e ter o SHA-256 fixado no relatório.

Os scripts exploratórios podem produzir JSONs parciais ou usar decodificação linear de regiões unwind; não substituem as conclusões limitadas dos relatórios nem a verificação posterior. Não execute os runners V2/V3 para verificar esta entrega, pois eles podem regravar o baseline: use o verificador específico da V4.
