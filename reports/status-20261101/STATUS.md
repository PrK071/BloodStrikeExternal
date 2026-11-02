# Situação verificada — 01/11/2026

A implementação V7 passa nos 133 testes locais, incluindo nove integrações nativas próprias. Isso não demonstra funcionamento em partida. O loop watch não envia movimentos de mira; a projeção final, a visibilidade e a calibração no jogo continuam pendentes.

A amostra instalada confere com o SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. As evidências estáticas, recursos e manifestos V7 foram reconferidos; veja delivery-verification.json.

Processos BloodStrike observados: 0. Nenhum dump de memória foi produzido. static-offsets.json consolida constantes existentes com arquivo/linha/hash, seções do PE e o contrato de câmera. Trata-se de exportação estática da build existente, não de offsets novos obtidos em runtime.

RVA exige a base efetiva do módulo em execução. Deslocamentos de campos exigem a instância e o subobjeto corretos. HP/facção/estado usam metadados dinâmicos; não há um deslocamento fixo universal demonstrado. Os offsets de terceiros continuam sem validação.
