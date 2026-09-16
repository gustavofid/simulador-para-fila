# -*- coding: utf-8 -*-
"""
Simulador de eventos discretos para REDE DE FILAS (G/G/c/K).

Simulacao e Metodos Analiticos - PUCRS
M4 | Simulador para uma fila      (fila unica)
M6 | Simulador para filas em tandem (duas ou mais filas interligadas)

A rede e descrita por um arquivo de modelo (JSON). O simulador nao tem
nenhuma topologia fixa no codigo: le as filas, os servidores, as
capacidades e as probabilidades de roteamento do modelo.

Uso:
    python3 simulador.py modelos/m6_tandem.json

Etapas implementadas:
  1) Gerador de numeros pseudoaleatorios (Metodo Congruente Linear)
  2) Escalonador de eventos (fila de prioridade por tempo)
  3) Tratamento dos eventos CHEGADA, SAIDA e PASSAGEM
  4) Acumulo de tempo em TODAS as filas + distribuicao de probabilidades
  5) Impressao dos resultados por fila
"""

import heapq
import json
import sys

# =====================================================================
# ETAPA 1 - Gerador de numeros pseudoaleatorios (Metodo Congruente Linear)
# =====================================================================
class Esgotado(Exception):
    """Sinaliza que o ultimo pseudoaleatorio permitido ja foi consumido."""


class Gerador:
    """X(i+1) = (a * X(i) + c) mod M, normalizado em [0,1)."""

    def __init__(self, a=1664525, c=1013904223, M=2 ** 32, semente=8, maximo=100000):
        self.a = a
        self.c = c
        self.M = M
        self.semente = semente
        self.previous = semente
        self.maximo = maximo
        self.usados = 0

    def NextRandom(self):
        # criterio de parada: ao utilizar o ultimo aleatorio a simulacao
        # encerra imediatamente, sem consumir nenhum numero a mais.
        if self.usados >= self.maximo:
            raise Esgotado()
        self.previous = ((self.a * self.previous) + self.c) % self.M
        self.usados += 1
        return self.previous / self.M

    def uniforme(self, A, B):
        """Numero uniformemente distribuido no intervalo [A, B]."""
        return A + (B - A) * self.NextRandom()

    def esgotado(self):
        return self.usados >= self.maximo


# =====================================================================
# ETAPA 2 - Evento e Escalonador
# =====================================================================
CHEGADA = "CHEGADA"
SAIDA = "SAIDA"
PASSAGEM = "PASSAGEM"


class Evento:
    """Tipo do evento, tempo em que ocorre e as filas envolvidas."""

    __slots__ = ("tipo", "tempo", "origem", "destino")

    def __init__(self, tipo, tempo, origem=None, destino=None):
        self.tipo = tipo
        self.tempo = tempo
        self.origem = origem      # fila de onde o cliente sai  (SAIDA / PASSAGEM)
        self.destino = destino    # fila onde o cliente entra   (CHEGADA / PASSAGEM)

    def __lt__(self, outro):
        return self.tempo < outro.tempo

    def __repr__(self):
        return "{}@{:.4f}".format(self.tipo, self.tempo)


class Escalonador:
    """Fila de prioridade: devolve sempre o evento de menor tempo."""

    def __init__(self):
        self._heap = []
        self._ordem = 0           # desempate estavel entre eventos de mesmo tempo

    def agenda(self, evento):
        self._ordem += 1
        heapq.heappush(self._heap, (evento.tempo, self._ordem, evento))

    def proximo(self):
        return heapq.heappop(self._heap)[2]

    def vazio(self):
        return not self._heap


# =====================================================================
# Entidade Fila
# =====================================================================
class Fila:
    """Uma fila G/G/c/K da rede."""

    def __init__(self, nome, servidores, capacidade,
                 atendimento, chegada=None, roteamento=None):
        self.nome = nome
        self.servidores = servidores
        self.capacidade = capacidade              # None = capacidade infinita
        self.atendimento = tuple(atendimento)     # (min, max)
        self.chegada = tuple(chegada) if chegada else None
        self.roteamento = roteamento or []        # [(Fila, probabilidade), ...]

        self.status = 0                           # clientes no sistema
        self.perdas = 0
        # estado -> tempo acumulado (todos os estados 0..K sao reportados)
        if self.capacidade is None:
            self.tempos = {0: 0.0}
        else:
            self.tempos = {k: 0.0 for k in range(self.capacidade + 1)}

    # --- propriedades ------------------------------------------------
    def tem_espaco(self):
        return self.capacidade is None or self.status < self.capacidade

    def servidor_livre(self):
        return self.status <= self.servidores

    def ha_cliente_esperando(self):
        return self.status >= self.servidores

    def notacao(self):
        K = "inf" if self.capacidade is None else self.capacidade
        return "G/G/{}/{}".format(self.servidores, K)

    # --- estado ------------------------------------------------------
    def acumula(self, delta):
        self.tempos[self.status] = self.tempos.get(self.status, 0.0) + delta

    def entra(self):
        self.status += 1

    def sai(self):
        self.status -= 1


# =====================================================================
# Simulador
# =====================================================================
class Simulador:

    def __init__(self, modelo):
        g = modelo.get("gerador", {})
        self.gerador = Gerador(
            a=g.get("a", 1664525),
            c=g.get("c", 1013904223),
            M=g.get("M", 2 ** 32),
            semente=modelo.get("semente", 8),
            maximo=modelo.get("aleatorios", 100000),
        )
        self.nome = modelo.get("nome", "rede de filas")
        self.escalonador = Escalonador()
        self.tempoGlobal = 0.0

        # --- filas ---
        self.filas = {}
        self.ordem_filas = []
        for f in modelo["filas"]:
            fila = Fila(
                nome=f["nome"],
                servidores=f["servidores"],
                capacidade=f.get("capacidade"),
                atendimento=f["atendimento"],
                chegada=f.get("chegada"),
            )
            self.filas[fila.nome] = fila
            self.ordem_filas.append(fila)

        # --- roteamento (resolvido depois que todas as filas existem) ---
        for f in modelo["filas"]:
            origem = self.filas[f["nome"]]
            total = 0.0
            for r in f.get("roteamento", []):
                if r["destino"] not in self.filas:
                    raise ValueError(
                        "A fila '{}' roteia para '{}', que nao existe no modelo.".format(
                            f["nome"], r["destino"])
                    )
                destino = self.filas[r["destino"]]
                p = float(r["probabilidade"])
                origem.roteamento.append((destino, p))
                total += p
            if total > 1.0 + 1e-9:
                raise ValueError(
                    "Roteamento da fila '{}' soma {:.4f} (> 1)".format(f["nome"], total)
                )
            origem.prob_saida = 1.0 - total   # probabilidade de deixar a rede

        # --- chegadas externas iniciais ---
        for ch in modelo["chegadas"]:
            if ch["fila"] not in self.filas:
                raise ValueError(
                    "Chegada inicial agendada para a fila '{}', que nao existe no "
                    "modelo.".format(ch["fila"])
                )
            destino = self.filas[ch["fila"]]
            if destino.chegada is None:
                raise ValueError(
                    "A fila '{}' recebe chegada inicial mas nao tem o campo "
                    "'chegada' (intervalo entre chegadas externas) no modelo.".format(
                        destino.nome)
                )
            self.escalonador.agenda(Evento(CHEGADA, float(ch["tempo"]), destino=destino))

    # -----------------------------------------------------------------
    # ETAPA 4 - acumula o tempo decorrido em TODAS as filas da rede
    # -----------------------------------------------------------------
    def AcumulaTempo(self, tempo):
        delta = tempo - self.tempoGlobal
        for fila in self.ordem_filas:
            fila.acumula(delta)
        self.tempoGlobal = tempo

    # -----------------------------------------------------------------
    # Decide o destino de um cliente que termina o atendimento na fila
    # e agenda o evento correspondente (SAIDA ou PASSAGEM).
    #
    # Quando ha um unico destino com probabilidade 1.0 (tandem puro) o
    # destino e deterministico e NAO se consome um pseudoaleatorio, para
    # que o consumo de aleatorios seja identico ao do simulador de
    # referencia. So ha sorteio quando existe ramificacao de verdade.
    # -----------------------------------------------------------------
    def agenda_termino(self, fila, tempo):
        instante = tempo + self.gerador.uniforme(*fila.atendimento)
        destino = self._sorteia_destino(fila)
        if destino is None:
            self.escalonador.agenda(Evento(SAIDA, instante, origem=fila))
        else:
            self.escalonador.agenda(
                Evento(PASSAGEM, instante, origem=fila, destino=destino)
            )

    def _sorteia_destino(self, fila):
        if not fila.roteamento:
            return None
        if len(fila.roteamento) == 1 and abs(fila.roteamento[0][1] - 1.0) < 1e-9:
            return fila.roteamento[0][0]          # tandem puro: sem sorteio
        x = self.gerador.NextRandom()
        acumulado = 0.0
        for destino, p in fila.roteamento:
            acumulado += p
            if x < acumulado:
                return destino
        return None                               # caiu na parcela de saida da rede

    # -----------------------------------------------------------------
    # ETAPA 3 - Tratamento dos eventos
    # -----------------------------------------------------------------
    def trata_chegada(self, ev):
        """Cliente chega do exterior da rede na fila ev.destino."""
        fila = ev.destino
        self.AcumulaTempo(ev.tempo)
        if fila.tem_espaco():
            fila.entra()
            if fila.servidor_livre():
                self.agenda_termino(fila, ev.tempo)
        else:
            fila.perdas += 1
        # agenda a proxima chegada externa nesta mesma fila
        self.escalonador.agenda(
            Evento(CHEGADA, ev.tempo + self.gerador.uniforme(*fila.chegada),
                   destino=fila)
        )

    def trata_saida(self, ev):
        """Cliente termina o atendimento e deixa a rede."""
        fila = ev.origem
        self.AcumulaTempo(ev.tempo)
        fila.sai()
        if fila.ha_cliente_esperando():
            self.agenda_termino(fila, ev.tempo)

    def trata_passagem(self, ev):
        """Cliente sai de ev.origem e entra em ev.destino.

        E a combinacao de uma SAIDA (na origem) com uma CHEGADA (no
        destino), respeitando as variaveis de controle de cada fila.
        Nao ha agendamento de nova chegada externa aqui.
        """
        origem, destino = ev.origem, ev.destino
        self.AcumulaTempo(ev.tempo)

        # --- parte "saida", no contexto da fila de origem ---
        origem.sai()
        if origem.ha_cliente_esperando():
            self.agenda_termino(origem, ev.tempo)

        # --- parte "chegada", no contexto da fila de destino ---
        if destino.tem_espaco():
            destino.entra()
            if destino.servidor_livre():
                self.agenda_termino(destino, ev.tempo)
        else:
            destino.perdas += 1        # perda contabilizada na fila de DESTINO

    # -----------------------------------------------------------------
    # Loop principal
    # -----------------------------------------------------------------
    def executa(self):
        despacho = {
            CHEGADA: self.trata_chegada,
            SAIDA: self.trata_saida,
            PASSAGEM: self.trata_passagem,
        }
        try:
            while not self.gerador.esgotado() and not self.escalonador.vazio():
                ev = self.escalonador.proximo()
                despacho[ev.tipo](ev)
        except Esgotado:
            pass   # o tempo ja foi acumulado no inicio do tratamento do evento

    # -----------------------------------------------------------------
    # ETAPA 5 - Impressao dos resultados
    # -----------------------------------------------------------------
    def relatorio(self):
        L = []
        L.append("=" * 66)
        L.append("  {}".format(self.nome))
        L.append("  Gerador: a={}, c={}, M={}, semente={}".format(
            self.gerador.a, self.gerador.c, self.gerador.M, self.gerador.semente))
        L.append("  Aleatorios utilizados: {}".format(self.gerador.usados))
        L.append("=" * 66)

        for fila in self.ordem_filas:
            rot = ", ".join("{} ({:.0f}%)".format(d.nome, p * 100)
                            for d, p in fila.roteamento)
            if fila.prob_saida > 1e-9:
                rot += (", " if rot else "") + "saida da rede ({:.0f}%)".format(
                    fila.prob_saida * 100)
            L.append("")
            L.append("{}  -  {}".format(fila.nome, fila.notacao()))
            if fila.chegada:
                L.append("  Chegadas externas entre {}...{}".format(*fila.chegada))
            else:
                L.append("  Sem chegadas externas")
            L.append("  Atendimento entre {}...{}".format(*fila.atendimento))
            L.append("  Roteamento: {}".format(rot or "saida da rede (100%)"))
            L.append("  " + "-" * 62)
            L.append("  {:>7} {:>18} {:>14}".format(
                "ESTADO", "TEMPO ACUMULADO", "PROBABILIDADE"))
            L.append("  " + "-" * 62)
            for estado in sorted(fila.tempos):
                t = fila.tempos[estado]
                L.append("  {:>7} {:>18.4f} {:>13.2f}%".format(
                    estado, t, (t / self.tempoGlobal) * 100 if self.tempoGlobal else 0))
            L.append("  " + "-" * 62)
            L.append("  Perda de clientes: {}".format(fila.perdas))

        L.append("")
        L.append("Tempo global da simulacao ....: {:.4f}".format(self.tempoGlobal))
        L.append("Perdas totais da rede ........: {}".format(
            sum(f.perdas for f in self.ordem_filas)))
        L.append("")
        return "\n".join(L)


# =====================================================================
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Modelos disponiveis em modelos/ . Exemplo:")
        print("    python3 simulador.py modelos/m6_tandem.json")
        return 1
    for caminho in sys.argv[1:]:
        with open(caminho, encoding="utf-8") as fp:
            modelo = json.load(fp)
        sim = Simulador(modelo)
        sim.executa()
        print(sim.relatorio())
    return 0


if __name__ == "__main__":
    sys.exit(main())
