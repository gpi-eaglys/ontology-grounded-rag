"""Build causal chain knowledge graph in Neo4j for Exp03 demo.

Extracts and persists the implicit causal chain from RG-50/65 gearbox documents:
ρf=0.38m → high stress concentration → insufficient bending margin
→ startup peak torque exceeded design → tooth root fatigue fracture

@author: Gabor Pinter
"""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7603"
NEO4J_USER = "neo4j"
NEO4J_PASS = "password"


def clear_db(tx) -> None:
    """Delete all nodes and relationships.

    @param tx: Neo4j transaction.
    """
    tx.run("MATCH (n) DETACH DELETE n")


def build_graph(tx) -> None:
    """Create the full causal chain graph.

    Ontology:
      Product -[HAS_PART]-> Part
      Part    -[HAS_PARAM]-> Parameter
      Parameter -[HAS_VALUE]-> Value
      Parameter -[AFFECTS]-> Parameter
      Value   -[CONSTRAINED_BY]-> Constraint
      Failure -[CAUSED_BY]-> ParameterSetting
      ParameterSetting -[INCLUDES]-> Value
      Document -[EVIDENCES]-> (any node)

    @param tx: Neo4j transaction.
    """
    tx.run("""
    // ── PRODUCTS ──────────────────────────────────────────────────────────────
    MERGE (rg50:Product {id:'RG-50'})
      SET rg50.name = 'RG-50 減速機',
          rg50.description = '搬送コンベヤ駆動用 平歯車単段減速機',
          rg50.allowable_torque_Nm = 500,
          rg50.status = 'current'

    MERGE (rg65:Product {id:'RG-65'})
      SET rg65.name = 'RG-65 減速機',
          rg65.description = 'RG-50 同一設計思想・上位フレーム機',
          rg65.status = 'field_failure'

    // ── PARTS ─────────────────────────────────────────────────────────────────
    MERGE (gear_driven:Part {id:'GR-205'})
      SET gear_driven.name = '被動歯車',
          gear_driven.material = 'SCM440 浸炭焼入れ',
          gear_driven.hardness = 'HRC 58〜62',
          gear_driven.teeth = 100,
          gear_driven.module = 3

    MERGE (gear_drive:Part {id:'GR-204'})
      SET gear_drive.name = '駆動歯車',
          gear_drive.material = 'SCM440 浸炭焼入れ',
          gear_drive.teeth = 20,
          gear_drive.module = 3

    // ── PARAMETERS ────────────────────────────────────────────────────────────
    MERGE (p_rho:Parameter {id:'param_rho_f'})
      SET p_rho.name = '歯元すみ肉半径 ρf',
          p_rho.symbol = 'ρf',
          p_rho.unit = 'mm (= coeff × module)',
          p_rho.description = '歯元フィレット半径。小さいほど応力集中が増大する'

    MERGE (p_ys:Parameter {id:'param_Ys'})
      SET p_ys.name = '応力修正係数 Ys',
          p_ys.symbol = 'Ys',
          p_ys.unit = '-',
          p_ys.description = 'ρfに依存。R小→Ys大→歯元応力大'

    MERGE (p_sigF:Parameter {id:'param_sigF'})
      SET p_sigF.name = '歯元曲げ応力 σF',
          p_sigF.symbol = 'σF',
          p_sigF.unit = 'MPa',
          p_sigF.description = '繰返し曲げで亀裂が進展する主要ストレス'

    MERGE (p_peak:Parameter {id:'param_peak_torque'})
      SET p_peak.name = '起動時ピークトルク',
          p_peak.symbol = 'T_peak',
          p_peak.unit = 'N·m',
          p_peak.description = '起動停止サイクルで発生する過渡ピーク。定常値の1.3倍（Ks=1.3）'

    MERGE (p_sf:Parameter {id:'param_SF'})
      SET p_sf.name = '歯元曲げ安全率 SF',
          p_sf.symbol = 'SF',
          p_sf.unit = '-',
          p_sf.description = 'σFlim / σF。余裕が小さいと変動荷重で容易に割れる'

    // ── VALUES ────────────────────────────────────────────────────────────────
    MERGE (v_rho_current:Value {id:'val_rho_0.38m'})
      SET v_rho_current.label = 'ρf = 0.38m（現行標準）',
          v_rho_current.coefficient = 0.38,
          v_rho_current.actual_mm = 1.14,
          v_rho_current.status = 'risky',
          v_rho_current.note = '加工標準工具の下限。強度的には余裕が少ない'

    MERGE (v_rho_improved:Value {id:'val_rho_0.40m'})
      SET v_rho_improved.label = 'ρf = 0.40m（是正後）',
          v_rho_improved.coefficient = 0.40,
          v_rho_improved.actual_mm = 1.20,
          v_rho_improved.status = 'safe',
          v_rho_improved.note = 'QR-2022-114 是正処置。歯元応力を数%低減'

    MERGE (v_peak_exceeded:Value {id:'val_peak_exceeded'})
      SET v_peak_exceeded.label = '起動ピーク > 設計想定',
          v_peak_exceeded.status = 'critical',
          v_peak_exceeded.note = '搬送装置の頻繁な起動停止。Ks=1.3を初版では未考慮'

    MERGE (v_sf_marginal:Value {id:'val_SF_marginal'})
      SET v_sf_marginal.label = 'SF ≈ 1.20（余裕小）',
          v_sf_marginal.value = 1.20,
          v_sf_marginal.status = 'marginal',
          v_sf_marginal.note = '合格だが余裕がない。ピーク荷重で容易に下回る'

    // ── CONSTRAINTS ───────────────────────────────────────────────────────────
    MERGE (c_sigFlim:Constraint {id:'const_sigFlim'})
      SET c_sigFlim.name = '許容歯元曲げ応力 σFlim',
          c_sigFlim.threshold = '340 MPa',
          c_sigFlim.basis = 'SCM440 浸炭焼入れ（安全率込）JIS B 1701',
          c_sigFlim.required_SF = 1.20

    MERGE (c_rho_min:Constraint {id:'const_rho_min'})
      SET c_rho_min.name = '歯元R 設計制約',
          c_rho_min.threshold = 'ρf ≥ 0.38m（標準工具下限）',
          c_rho_min.note = 'トルクアップ時は0.40m以上を推奨（TM-2021-007）'

    // ── PARAMETER SETTINGS (failure conditions) ───────────────────────────────
    MERGE (ps_fail:ParameterSetting {id:'ps_failure_condition'})
      SET ps_fail.name = '破損発生パラメータ組合せ',
          ps_fail.description = 'ρf=0.38m（応力集中大） ＋ 起動時ピークトルク超過想定',
          ps_fail.result = 'SF < 1.20 → 歯元亀裂進展 → 疲労破損'

    MERGE (ps_ecr:ParameterSetting {id:'ps_ecr_risk'})
      SET ps_ecr.name = 'ECRトルクアップ時のリスク条件',
          ps_ecr.description = 'RG-50 にトルク500→650N·m を適用した場合',
          ps_ecr.result = '歯元応力余裕がさらに消失。歯元R再評価が必要（QR横展開）'

    // ── FAILURES ──────────────────────────────────────────────────────────────
    MERGE (f_fracture:Failure {id:'fail_rg65_2022'})
      SET f_fracture.name = '被動歯車 歯元疲労破損',
          f_fracture.product = 'RG-65',
          f_fracture.date = '2022-08-29',
          f_fracture.hours = 9400,
          f_fracture.designed_life_h = 20000,
          f_fracture.life_fraction = 0.47,
          f_fracture.evidence = 'ビーチマーク確認 → 疲労破壊確定'

    MERGE (f_risk:Failure {id:'fail_rg50_ecr_risk'})
      SET f_risk.name = 'RG-50 歯元破損リスク（潜在）',
          f_risk.product = 'RG-50',
          f_risk.status = 'risk_identified',
          f_risk.trigger = 'ECR-2026-018 トルク 500→650 N·m',
          f_risk.note = 'QR-2022-114 横展開対象。未対策のまま増トルクすると顕在化しうる'

    // ── DOCUMENTS ─────────────────────────────────────────────────────────────
    MERGE (doc_tm:Document {id:'TM-2021-007'})
      SET doc_tm.name = '技術メモ TM-2021-007',
          doc_tm.type = '設計ノウハウ',
          doc_tm.author = '兵頭',
          doc_tm.date = '2021-07-14',
          doc_tm.title = '歯元すみ肉R設計の勘所'

    MERGE (doc_qr:Document {id:'QR-2022-114'})
      SET doc_qr.name = '不具合対策書 QR-2022-114',
          doc_qr.type = '是正処置報告書',
          doc_qr.date = '2022-09-12',
          doc_qr.title = 'RG-65 被動歯車 歯元疲労破損'

    MERGE (doc_dr:Document {id:'DR-50-03'})
      SET doc_dr.name = '設計審査議事録 DR-50-03',
          doc_dr.type = 'Design Review',
          doc_dr.date = '2021-06-25',
          doc_dr.title = 'RG-50 第3回詳細設計審査'

    MERGE (doc_ecr:Document {id:'ECR-2026-018'})
      SET doc_ecr.name = '設計変更依頼書 ECR-2026-018',
          doc_ecr.type = 'Engineering Change Request',
          doc_ecr.date = '2026-06-15',
          doc_ecr.title = '出力軸トルク強化 500→650 N·m'

    MERGE (doc_calc:Document {id:'CALC-RG50-021'})
      SET doc_calc.name = '強度計算書 CALC-RG50-021',
          doc_calc.type = '設計計算書',
          doc_calc.date = '2021-06-22',
          doc_calc.title = '歯車歯元曲げ・歯面強さ計算'

    // ── RELATIONSHIPS ─────────────────────────────────────────────────────────

    // Product → Part
    MERGE (rg50)-[:HAS_PART]->(gear_driven)
    MERGE (rg50)-[:HAS_PART]->(gear_drive)
    MERGE (rg65)-[:HAS_PART]->(gear_driven)

    // Part → Parameter
    MERGE (gear_driven)-[:HAS_PARAM]->(p_rho)
    MERGE (gear_driven)-[:HAS_PARAM]->(p_sigF)
    MERGE (gear_driven)-[:HAS_PARAM]->(p_sf)
    MERGE (gear_driven)-[:HAS_PARAM]->(p_peak)

    // Parameter → Value
    MERGE (p_rho)-[:HAS_VALUE]->(v_rho_current)
    MERGE (p_rho)-[:HAS_VALUE]->(v_rho_improved)
    MERGE (p_peak)-[:HAS_VALUE]->(v_peak_exceeded)
    MERGE (p_sf)-[:HAS_VALUE]->(v_sf_marginal)

    // Parameter → Parameter (causal chain)
    MERGE (p_rho)-[:AFFECTS {description: 'R小→応力修正係数Ys増大'}]->(p_ys)
    MERGE (p_ys)-[:AFFECTS {description: 'Ys大→歯元応力σF増大'}]->(p_sigF)
    MERGE (p_peak)-[:AFFECTS {description: 'ピーク荷重が歯元応力を押し上げる'}]->(p_sigF)
    MERGE (p_sigF)-[:AFFECTS {description: 'σF増大→安全率SF低下'}]->(p_sf)

    // Value → Constraint
    MERGE (v_rho_current)-[:CONSTRAINED_BY]->(c_rho_min)
    MERGE (v_sf_marginal)-[:CONSTRAINED_BY]->(c_sigFlim)

    // ParameterSetting → Value
    MERGE (ps_fail)-[:INCLUDES]->(v_rho_current)
    MERGE (ps_fail)-[:INCLUDES]->(v_peak_exceeded)

    // Failure → ParameterSetting
    MERGE (f_fracture)-[:CAUSED_BY]->(ps_fail)
    MERGE (f_risk)-[:CAUSED_BY]->(ps_ecr)

    // ParameterSetting → ParameterSetting (ECR worsens existing risk)
    MERGE (ps_ecr)-[:WORSENS]->(ps_fail)

    // Improved value replaces risky one
    MERGE (v_rho_improved)-[:REPLACES {document: 'QR-2022-114'}]->(v_rho_current)

    // Document evidence
    MERGE (doc_tm)-[:WARNS_ABOUT]->(p_rho)
    MERGE (doc_tm)-[:WARNS_ABOUT]->(ps_fail)
    MERGE (doc_dr)-[:RAISED_CONCERN]->(p_rho)
    MERGE (doc_qr)-[:DOCUMENTS]->(f_fracture)
    MERGE (doc_qr)-[:DOCUMENTS]->(ps_fail)
    MERGE (doc_ecr)-[:TRIGGERS_RISK]->(f_risk)
    MERGE (doc_calc)-[:DOCUMENTS]->(p_sigF)
    MERGE (doc_calc)-[:DOCUMENTS]->(p_sf)
    """)


def main() -> None:
    """Connect to Neo4j, clear database, and build the causal chain graph."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    with driver.session() as session:
        print("Clearing database...")
        session.execute_write(clear_db)
        print("Building causal chain graph...")
        session.execute_write(build_graph)
        counts = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY label"
        )
        print("\nNode counts:")
        for r in counts:
            print(f"  {r['label']:20s} {r['cnt']}")
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()
        print(f"\n  {'Relationships':20s} {rel_count['cnt']}")
    driver.close()
    print("\nDone. Open Neo4j Browser at http://localhost:7403")
    print("Run: MATCH (n) RETURN n")


if __name__ == "__main__":
    main()
