# Simulador de Fila Simples (G/G/c/K)

Trabalho do módulo **M4 — Desenvolvimento de Simulador para uma Fila**
(Simulação e Métodos Analíticos — PUCRS).

Simulador de eventos discretos para uma fila com `c` servidores e capacidade `K`,
com gerador de números pseudoaleatórios próprio (Método Congruente Linear).

## Como executar

```bash
python3 simulador.py
```

Sem dependências externas (apenas biblioteca padrão do Python 3).

## Estrutura

| Etapa | Onde está |
|---|---|
| 1. Gerador pseudoaleatório (MCL) | `NextRandom()` / `uniforme()` |
| 2. Loop principal | `simula()` |
| 3. Eventos de chegada e saída | `trata_chegada()` / `trata_saida()` |
| 4. Tempos acumulados e probabilidades | `contabiliza()` |
| 5. Análise dos resultados | `imprime()` |

## Parâmetros do gerador

`X(i+1) = (a * X(i) + c) mod M`

- a = 1664525
- c = 1013904223
- M = 2^32
- semente = 8
- 100.000 números pseudoaleatórios por simulação (critério de parada)

## Cenários simulados

Fila iniciada vazia, primeiro cliente chegando em t = 3,0.

- G/G/1/5 — chegadas 2...5, atendimento 3...5
- G/G/2/5 — chegadas 2...5, atendimento 3...5
- G/G/1/5 — chegadas 3...5, atendimento 4...5
- G/G/2/5 — chegadas 3...5, atendimento 4...5

A saída completa está em `resultados.txt`.
