# OpenRouter Free Models Tracker

Monitorização semanal dos modelos **free** do OpenRouter com GitHub Actions.

O projeto gera snapshots automáticos da lista de modelos free e calcula as diferenças entre execuções, para ser fácil detetar:
- Modelos adicionados.
- Modelos removidos.
- Total atual de modelos free.

## Objetivo

Este repositório existe para:
1. Obter semanalmente a lista de modelos do OpenRouter.
2. Filtrar os modelos free.
3. Guardar o estado atual e o estado anterior.
4. Gerar um ficheiro de diff para análise manual ou leitura pelo Perplexity.

## Estrutura

```text
.
├─ .github/
│  └─ workflows/
│     └─ openrouter-free.yml
├─ scripts/
│  └─ update_openrouter_free.py
├─ data/
│  ├─ .gitkeep
│  ├─ current.json
│  ├─ previous.json
│  └─ diff.json
└─ README.md
