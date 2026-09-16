# Simulador de Rede de Filas (G/G/c/K)

Trabalho de **Simulação e Métodos Analíticos** — PUCRS, 2026/2.

Simulador de eventos discretos para uma **rede de filas** com topologia genérica.
Cada fila tem `c` servidores, capacidade `K`, intervalos de chegada e de
atendimento próprios, e probabilidades de roteamento para outras filas.
O gerador de números pseudoaleatórios é próprio (Método Congruente Linear).

| Módulo | Escopo |
|---|---|
| **M4** | Simulador para uma fila (`CHEGADA`, `SAIDA`) |
| **M6** | Simulador para filas em tandem (`CHEGADA`, `SAIDA`, `PASSAGEM`) |

A topologia **não está no código**: ela é descrita num arquivo de modelo. O mesmo
executável roda uma fila simples, duas filas em tandem ou uma rede ramificada.

---

## Como executar

Sem dependências externas — apenas a biblioteca padrão do Python 3.

```bash
# cenário de validação do M6 (duas filas em tandem)
python3 simulador.py modelos/m6_tandem.json

# cenários do M4 (fila simples)
python3 simulador.py modelos/m4_gg1_5.json modelos/m4_gg2_5.json

# vários modelos de uma vez
python3 simulador.py modelos/*.json
```

Para conferir que o simulador está correto:

```bash
python3 verificacao.py
```

---

## Sintaxe de entrada

O modelo é um arquivo **JSON**. Exemplo completo (`modelos/m6_tandem.json`):

```json
{
  "nome": "M6 | Duas filas em tandem",
  "semente": 8,
  "aleatorios": 100000,
  "gerador": { "a": 1664525, "c": 1013904223, "M": 4294967296 },

  "chegadas": [
    { "fila": "Fila 1", "tempo": 2.5 }
  ],

  "filas": [
    {
      "nome": "Fila 1",
      "servidores": 2,
      "capacidade": 3,
      "chegada": [1, 5],
      "atendimento": [4, 5],
      "roteamento": [ { "destino": "Fila 2", "probabilidade": 1.0 } ]
    },
    {
      "nome": "Fila 2",
      "servidores": 1,
      "capacidade": 5,
      "atendimento": [1, 3],
      "roteamento": []
    }
  ]
}
```

| Campo | Significado |
|---|---|
| `semente` | valor inicial `X0` do gerador |
| `aleatorios` | critério de parada: quantos pseudoaleatórios consumir |
| `gerador` | parâmetros `a`, `c` e `M` do Método Congruente Linear (opcional) |
| `chegadas` | agendamento das primeiras chegadas vindas do exterior da rede |
| `filas[].servidores` | número de servidores `c` |
| `filas[].capacidade` | capacidade `K` (total, incluindo em atendimento). `null` = infinita |
| `filas[].chegada` | intervalo `[min, max]` entre chegadas externas. Ausente = fila sem chegadas externas |
| `filas[].atendimento` | intervalo `[min, max]` de atendimento |
| `filas[].roteamento` | lista de `{destino, probabilidade}` |

**Roteamento.** As probabilidades de `roteamento` de uma fila devem somar no
máximo 1. O que sobrar é a probabilidade de o cliente **deixar a rede** ao
terminar o atendimento. Uma fila com `"roteamento": []` manda 100% dos clientes
para fora da rede. Assim a mesma sintaxe descreve tandem puro
(`[{destino, 1.0}]`), saída direta (`[]`) e ramificação probabilística
(ver `modelos/exemplo_rede_ramificada.json`).

---

## Estrutura do código

| Etapa | Onde está |
|---|---|
| 1. Gerador pseudoaleatório (MCL) | `Gerador.NextRandom()` / `Gerador.uniforme()` |
| 2. Escalonador de eventos | `Evento`, `Escalonador` |
| 3. Tratamento dos eventos | `trata_chegada()`, `trata_saida()`, `trata_passagem()` |
| 4. Acúmulo de tempo e probabilidades | `Simulador.AcumulaTempo()`, `Fila.acumula()` |
| 5. Análise dos resultados | `Simulador.relatorio()` |

Entidades: **`Fila`** (servidores, capacidade, intervalos, roteamento, estado,
perdas e vetor de tempos acumulados), **`Evento`** (tipo, tempo, fila de origem,
fila de destino) e **`Escalonador`** (fila de prioridade por tempo, com
desempate estável entre eventos de mesmo instante).

### Decisões de implementação

- **`AcumulaTempo` percorre todas as filas.** O tempo decorrido desde o último
  evento é somado ao estado atual de *cada* fila da rede, não só da fila
  envolvida no evento.
- **A passagem é uma saída seguida de uma chegada**, cada metade usando as
  variáveis de controle da sua própria fila. Não há agendamento de nova chegada
  externa no tratamento da passagem.
- **Perda na passagem.** Se a fila de destino estiver cheia, o cliente é perdido
  e a perda é contabilizada na fila de **destino**. A fila de origem libera o
  servidor do mesmo jeito e puxa quem estava esperando.
- **O destino é decidido no momento em que o término é agendado**, para que o
  evento já nasça com o tipo correto (`SAIDA` ou `PASSAGEM`), como no
  pseudocódigo da disciplina.
- **Tandem puro não consome pseudoaleatório extra.** Quando a fila tem um único
  destino com probabilidade 1,0 o roteamento é determinístico e nenhum número é
  sorteado. Só há sorteio quando existe ramificação de verdade. Isso mantém o
  consumo de aleatórios idêntico ao do simulador de referência.

---

## Verificação

`verificacao.py` faz duas coisas:

1. **Reimplementa a rede do M6 de forma independente** (código direto, sem
   classes, escalonador próprio) e compara número a número com o simulador —
   tempos acumulados de cada estado de cada fila, perdas e tempo global.
2. **Confere leis de conservação** que precisam valer em qualquer simulação
   correta: a ocupação média dos servidores de cada fila tem de ser igual à
   vazão vezes o tempo médio de atendimento (Little), e as probabilidades de
   cada fila têm de somar 1.

Os quatro cenários do M4 continuam produzindo exatamente os mesmos números da
entrega anterior, o que garante que a generalização não quebrou nada.

---

## Resultados

- `resultados_m4.txt` — os quatro cenários de fila simples do M4
- `resultados_m6.txt` — a rede em tandem do M6

Cenário de validação do M6: **Fila 1** G/G/2/3 (chegadas 1..5, atendimento 4..5)
→ **Fila 2** G/G/1/5 (atendimento 1..3), filas inicialmente vazias, primeiro
cliente em t = 2,5, parada em 100.000 pseudoaleatórios.
