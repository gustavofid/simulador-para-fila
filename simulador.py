# -*- coding: utf-8 -*-
"""
SIMULACAO E METODOS ANALITICOS - M4
Simulador de fila simples (G/G/c/K) baseado em eventos discretos.

Etapas implementadas:
  1) Gerador de numeros pseudoaleatorios (Metodo Congruente Linear) - NextRandom()
  2) Loop principal da simulacao (escalonador + eventos CHEGADA / SAIDA)
  3) Tratamento dos eventos de chegada e saida
  4) Calculo dos tempos acumulados e da distribuicao de probabilidades
  5) Impressao dos resultados para analise
"""

import heapq

# =====================================================================
# ETAPA 1 - Gerador de numeros pseudoaleatorios (Metodo Congruente Linear)
# =====================================================================
# X(i+1) = (a * X(i) + c) mod M      /  retorno normalizado em [0,1)
a = 1664525            # multiplicador
c = 1013904223         # incremento
M = 2 ** 32            # modulo (periodo completo, pois M=2^32, c impar e a=1+4k)
seed = 8               # semente inicial

previous = seed        # ultimo numero gerado da sequencia
usados = 0             # quantos aleatorios ja foram consumidos
MAX_ALEATORIOS = 100000

def NextRandom():
    """Retorna o proximo pseudoaleatorio normalizado entre 0 e 1."""
    global previous, usados
    previous = ((a * previous) + c) % M
    usados += 1
    return previous / M

def uniforme(A, B):
    """Numero uniformemente distribuido no intervalo [A, B]."""
    return A + (B - A) * NextRandom()

# =====================================================================
# Escalonador de eventos
# =====================================================================
CHEGADA = 0
SAIDA = 1

escalonador = []       # heap de (tempo, tipo, ordem)
ordem = 0              # desempate estavel entre eventos de mesmo tempo

def agenda(tempo, tipo):
    global ordem
    ordem += 1
    heapq.heappush(escalonador, (tempo, tipo, ordem))

def NextEvent():
    """Retira do escalonador o evento com o menor tempo de simulacao."""
    tempo, tipo, _ = heapq.heappop(escalonador)
    return tempo, tipo

# =====================================================================
# Estado da fila
# =====================================================================
fila = 0               # numero de clientes no sistema
tempoGlobal = 0.0      # relogio da simulacao
times = []             # tempos acumulados em cada estado
perdas = 0             # clientes perdidos (fila cheia)

def contabiliza(tempo):
    """ETAPA 4 - acumula o tempo decorrido no estado atual da fila."""
    global tempoGlobal
    times[fila] += tempo - tempoGlobal
    tempoGlobal = tempo

# =====================================================================
# ETAPA 3 - Tratamento dos eventos
# =====================================================================
def trata_chegada(tempo, servidores, K, chegada_min, chegada_max,
                  atend_min, atend_max):
    global fila, perdas
    contabiliza(tempo)
    if fila < K:                                   # ha espaco na fila
        fila += 1
        if fila <= servidores:                     # ha servidor livre
            agenda(tempo + uniforme(atend_min, atend_max), SAIDA)
    else:
        perdas += 1                                # cliente perdido
    agenda(tempo + uniforme(chegada_min, chegada_max), CHEGADA)

def trata_saida(tempo, servidores, atend_min, atend_max):
    global fila
    contabiliza(tempo)
    fila -= 1
    if fila >= servidores:                         # ainda ha cliente esperando
        agenda(tempo + uniforme(atend_min, atend_max), SAIDA)

# =====================================================================
# ETAPA 2 - Loop principal da simulacao
# =====================================================================
def simula(servidores, K, chegada_min, chegada_max, atend_min, atend_max,
           primeira_chegada=3.0, rotulo=""):
    global previous, usados, escalonador, ordem, fila, tempoGlobal, times, perdas

    # reinicializacao completa (cada simulacao usa a mesma semente)
    previous = seed
    usados = 0
    escalonador = []
    ordem = 0
    fila = 0
    tempoGlobal = 0.0
    times = [0.0] * (K + 1)
    perdas = 0

    agenda(primeira_chegada, CHEGADA)              # fila vazia, 1o cliente em 3,0

    while usados < MAX_ALEATORIOS:
        tempo, tipo = NextEvent()
        if tipo == CHEGADA:
            trata_chegada(tempo, servidores, K, chegada_min, chegada_max,
                          atend_min, atend_max)
        elif tipo == SAIDA:
            trata_saida(tempo, servidores, atend_min, atend_max)

    imprime(servidores, K, chegada_min, chegada_max, atend_min, atend_max, rotulo)

# =====================================================================
# ETAPA 5 - Impressao / analise dos resultados
# =====================================================================
def imprime(servidores, K, chegada_min, chegada_max, atend_min, atend_max, rotulo):
    print("=" * 62)
    print("  SIMULACAO: G/G/{}/{}   {}".format(servidores, K, rotulo))
    print("  Chegadas entre {}...{} | Atendimento entre {}...{}".format(
        chegada_min, chegada_max, atend_min, atend_max))
    print("  Gerador: a={}, c={}, M={}, seed={}".format(a, c, M, seed))
    print("  Aleatorios utilizados: {}".format(usados))
    print("=" * 62)
    print("{:>7} {:>18} {:>14}".format("ESTADO", "TEMPO ACUMULADO", "PROBABILIDADE"))
    print("-" * 62)
    for i in range(K + 1):
        print("{:>7} {:>18.4f} {:>13.2f}%".format(
            i, times[i], (times[i] / tempoGlobal) * 100))
    print("-" * 62)
    print("Tempo global da simulacao ....: {:.4f}".format(tempoGlobal))
    print("Numero de perdas de clientes .: {}".format(perdas))
    print()

# =====================================================================
def main():
    # Cenarios do arquivo modelo
    simula(1, 5, 2, 5, 3, 5, rotulo="(arquivo modelo)")
    simula(2, 5, 2, 5, 3, 5, rotulo="(arquivo modelo)")
    # Cenarios do enunciado do modulo
    simula(1, 5, 3, 5, 4, 5, rotulo="(enunciado do modulo)")
    simula(2, 5, 3, 5, 4, 5, rotulo="(enunciado do modulo)")

if __name__ == "__main__":
    main()
