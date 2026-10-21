import json

with open("reports/results.json", "r", encoding="utf-8") as f:
    res = json.load(f)

print("=== EVALUACION DE CRITERIOS DE ACEPTACION (HOLDOUT 2024-2026) ===")
for key, eval_data in res["acceptance_criteria_evaluation"].items():
    verd = eval_data["verdict"]
    p_adj = eval_data["A1_holm_p_value"]["value"]
    sh_b = eval_data["A2_base_sharpe"]["value"]
    sh_s = eval_data["A3_stress_sharpe"]["value"]
    p_perm = eval_data["A4_permutation_p"]["value"]
    y_frac = eval_data["A6_positive_years_fraction"]["value"] * 100
    p1_pass = eval_data["A1_holm_p_value"]["pass"]
    p2_pass = eval_data["A2_base_sharpe"]["pass"]
    p3_pass = eval_data["A3_stress_sharpe"]["pass"]
    p4_pass = eval_data["A4_permutation_p"]["pass"]
    p6_pass = eval_data["A6_positive_years_fraction"]["pass"]
    print(f"\n{key} -> Veredicto: {verd}")
    print(f"   A1 (Holm adj p <= 0.05):   val={p_adj:.4f}  [Pass: {p1_pass}]")
    print(f"   A2 (Sharpe base >= 0.50):  val={sh_b:.4f}   [Pass: {p2_pass}]")
    print(f"   A3 (Sharpe estres > 0.00): val={sh_s:.4f}   [Pass: {p3_pass}]")
    print(f"   A4 (Permutation p <= 0.05):val={p_perm:.4f}  [Pass: {p4_pass}]")
    print(f"   A6 (Anios positivos >= 50%): val={y_frac:.1f}% [Pass: {p6_pass}]")

print("\n=== METRICAS CLAVE DETALLADAS EN HOLDOUT ===")
for inst in ["ES", "NQ"]:
    inst_d = res["stages"]["final"]["instruments"][inst]
    print(f"\n-- {inst} (n={inst_d['n_sessions']} sesiones) --")
    for hyp in ["H1", "H2", "H3", "H4", "B1", "B3", "E1", "E2", "E3"]:
        h = inst_d["hypotheses"][hyp]
        base = h["base"]
        pnl = base["total_net_pnl_usd"]
        sh = base["sharpe_annualized"]
        wr = base["win_rate"] * 100
        nt = base["n_trades"]
        costs = base["total_costs_usd"]
        gross = base["total_gross_pnl_usd"]
        print(f"  {hyp:2s}: Net PnL = ${pnl:10,.0f} | Gross = ${gross:10,.0f} | Costs = ${costs:7,.0f} | Sharpe = {sh:6.2f} | WinRate = {wr:4.1f}% | Trades = {nt}")

print("\n=== REGRESIONES PREDICTIVAS FINAL HOLDOUT (n=696) ===")
for inst in ["ES", "NQ"]:
    regs = res["stages"]["final"]["instruments"][inst]["predictive_regressions"]
    b1, t1, p1 = regs["r13_on_r1"]["beta"], regs["r13_on_r1"]["t_stat"], regs["r13_on_r1"]["p_value"]
    b12, t12, p12 = regs["r13_on_r12"]["beta"], regs["r13_on_r12"]["t_stat"], regs["r13_on_r12"]["p_value"]
    print(f"{inst} r13 on r1:  beta={b1:.4f}, t={t1:.2f}, p={p1:.4f}")
    print(f"{inst} r13 on r12: beta={b12:.4f}, t={t12:.2f}, p={p12:.4f}")
