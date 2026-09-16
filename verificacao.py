# -*- coding: utf-8 -*-
"""
Verificacao do simulador.

1) Reimplementa a rede do M6 de forma totalmente independente (codigo
   direto, sem classes) e compara os resultados com os do simulador.
2) Confere leis de conservacao que precisam valer em qualquer simulacao
   correta: conservacao de fluxo entre as filas e a Lei de Little
   (ocupacao media dos servidores = vazao x tempo medio de atendimento).

Uso:
    python3 verificacao.py
"""

import heapq
import json
import importlib.util


# ---------------------------------------------------------------- #
# 1) implementacao independente da rede do M6
# ---------------------------------------------------------------- #
def referencia():
    a, c, M, seed = 1664525, 1013904223, 2 ** 32, 8
    estado = {"prev": seed, "usados": 0}

    def R():
        estado["prev"] = (a * estado["prev"] + c) % M
        estado["usados"] += 1
        return estado["prev"] / M

    def U(x, y):
        return x + (y - x) * R()

    c1, K1, c2, K2 = 2, 3, 1, 5
    n1 = n2 = 0
    perd1 = perd2 = 0
    t1 = [0.0] * (K1 + 1)
    t2 = [0.0] * (K2 + 1)
    TG = 0.0
    ev = []
    seq = [0]

    def push(tm, tp):
        seq[0] += 1
        heapq.heappush(ev, (tm, seq[0], tp))

    push(2.5, "CH")
    while estado["usados"] < 100000:
        tm, _, tp = heapq.heappop(ev)
        d = tm - TG
        t1[n1] += d
        t2[n2] += d
        TG = tm
        if tp == "CH":
            if n1 < K1:
                n1 += 1
                if n1 <= c1:
                    push(tm + U(4, 5), "PA")
            else:
                perd1 += 1
            push(tm + U(1, 5), "CH")
        elif tp == "PA":
            n1 -= 1
            if n1 >= c1:
                push(tm + U(4, 5), "PA")
            if n2 < K2:
                n2 += 1
                if n2 <= c2:
                    push(tm + U(1, 3), "SA")
            else:
                perd2 += 1
        else:
            n2 -= 1
            if n2 >= c2:
                push(tm + U(1, 3), "SA")

    return {"TG": TG, "t1": t1, "t2": t2, "perd1": perd1, "perd2": perd2}


# ---------------------------------------------------------------- #
def main():
    spec = importlib.util.spec_from_file_location("sim", "simulador.py")
    sim_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sim_mod)

    modelo = json.load(open("modelos/m6_tandem.json", encoding="utf-8"))
    sim = sim_mod.Simulador(modelo)

    passagens = [0]
    orig = sim.trata_passagem

    def conta(ev):
        passagens[0] += 1
        orig(ev)

    sim.trata_passagem = conta
    sim.executa()

    f1, f2 = sim.ordem_filas
    ref = referencia()
    tol = 1e-9
    ok = True

    print("1) Comparacao com implementacao independente")
    testes = [
        ("tempo global", sim.tempoGlobal, ref["TG"]),
        ("perdas Fila 1", f1.perdas, ref["perd1"]),
        ("perdas Fila 2", f2.perdas, ref["perd2"]),
    ]
    for k in sorted(f1.tempos):
        testes.append(("tempo F1 estado %d" % k, f1.tempos[k], ref["t1"][k]))
    for k in sorted(f2.tempos):
        testes.append(("tempo F2 estado %d" % k, f2.tempos[k], ref["t2"][k]))

    for nome, got, esp in testes:
        bate = abs(got - esp) < tol
        ok &= bate
        print("   [{}] {:<22} {:>16.4f}  ref {:>16.4f}".format(
            "OK" if bate else "!!", nome, got, esp))

    print()
    print("2) Leis de conservacao")
    TG = sim.tempoGlobal
    X = passagens[0] / TG                       # vazao da Fila 1
    ocup1 = sum(min(k, f1.servidores) * t / TG for k, t in f1.tempos.items())
    ocup2 = sum(min(k, f2.servidores) * t / TG for k, t in f2.tempos.items())
    checks = [
        ("ocupacao servidores F1", ocup1, X * (4 + 5) / 2),
        ("ocupacao servidor F2", ocup2, X * (1 + 3) / 2),
    ]
    for nome, got, esp in checks:
        bate = abs(got - esp) / esp < 1e-3
        ok &= bate
        print("   [{}] {:<22} {:>10.4f}  esperado {:>10.4f}".format(
            "OK" if bate else "!!", nome, got, esp))

    soma1 = sum(f1.tempos.values()) / TG
    soma2 = sum(f2.tempos.values()) / TG
    for nome, s in (("soma probs F1", soma1), ("soma probs F2", soma2)):
        bate = abs(s - 1.0) < 1e-9
        ok &= bate
        print("   [{}] {:<22} {:>10.6f}  esperado {:>10.6f}".format(
            "OK" if bate else "!!", nome, s, 1.0))

    print()
    print("RESULTADO:", "TODOS OS TESTES PASSARAM" if ok else "FALHOU")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
