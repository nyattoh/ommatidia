# 夜間作業の引き継ぎ（2026-10-15）

## 現在の状態

- ブランチ `main`。origin と同期済み（push 完了）。
- 最新リモートコミット: `7232cc0`
- 作者情報は `anonymous <nyattoh@users.noreply.github.com>`（ユーザー指定）。
- ランタイムの残件 1〜8 はすべて実装・修正済み。単体テストは 41 件すべて通過。
- 封印マニフェスト（`research/seal_manifest.json`）の整合性確認済み。

## 完了事項（ランタイム全残件 8 件の解決）

1. **残件 1: 使用量の集計で未知のコストとトークンを保持**
   - `Usage.add` および `_accumulate_step_usage` で `None` を `0` に強制変換せず、未知（`None`）を維持。実行開始時は 0 を明示。
2. **残件 2: 条件 A・B・C の予算チェック**
   - `ConditionARunner`、`ConditionBRunner`、`ConditionCRunner` でステップ実行後に `state.usage.exceeds(task.budget)` をチェックし、超過時は `state.decision = Decision.BLOCKED`、`state.stop_reason = "budget_exhausted"` と `FinalJudgement` の合成を実施。
   - `Budget.max_input_chars` のチェックを `Usage.exceeds` に反映。
3. **残件 3: 証拠撤回時の READY 取り消し**
   - `invalidate_evidence` において、必須ギャップ（`REQUIRED`）が再オープンまたは未解決となった場合、もしくは回答クレームが取り消された場合に、`state.decision = Decision.READY_FOR_REQUESTED_STEP` を取り消して `Decision.NEEDS_CHECK` に戻し `stop_reason` をクリア。
4. **残件 4: 古いロックの回収**
   - `RunLedger.acquire_lock` で PID が存在しない（プロセス死亡）場合のみロックを自動回収。PID なしのロックは阻止。
5. **残件 5: `verify_environment` の呼び出しと封印**
   - `ResearchHarness.evaluate_task` および `run_paired_comparison` の実行開始時に必ず `self.verify_environment()` を呼び出し、暗号学的整合性を担保。
   - `research/seal_manifest.json` にプロトコル（`research/PROTOCOL.md`）およびデータセット・仕様書（`research/EVALUATION_SPEC.md`、`research/datasets/dev/manifest.json`）を封印し、`scripts/verify_seals.py verify` で完全一致を確認。
6. **残件 6: Evaluator と Types を `EVALUATION_SPEC.md` に整合**
   - `FinalJudgement`、`CitedEvidenceItem`、`FinalJudgementResourceUsage` の型および JSON スキーマ定義・バリデーションを追加。
   - `conditions.py` に標準化システムプロンプト（`PROMPT_CONDITION_A` 〜 `PROMPT_CONDITION_E`）を埋め込み。
   - `evaluator.py` において、`FDA`（Final Decision Accuracy）、`Recall_crit`（Critical Item Recall）、`FAR`（False Alarm Rate）、`DSC`（Disjoint Source Coverage）、`WAR`（Warranted Abstention Rate）、`UAR`（Unwarranted Abstention Rate）、`efficiency_tool`、`efficiency_time` を数式仕様どおり実装。
7. **残件 7: 分散ゼロ・小標本時の信頼区間と検定**
   - 一致ペア差分で標本分散が 0.0 の場合、誤解を招く `[0.0, 0.0]` を出力せず、`ci95 = None` および小標本の不確実性に関する注記（`ciNote`）を出力するよう修正。
   - 比率の信頼区間として Newcombe (1998) の連続補正付き Wilson スコア区間（`wilson_score_interval_cc`）を実装。
   - `EVALUATION_SPEC.md` §5.2 の事前宣言どおり、ペア Wilcoxon 符号付き順位検定（`compute_wilcoxon_signed_rank`）を実装（差分 0 のペア除外、同順位タイは平均順位、連続補正なし正規近似、非ゼロ差分 6 未満は計算不可・inconclusive 判定）。
8. **残件 8: T3 Code 委任アダプタの配線**
   - `src/ommatidia/t3_adapter.py` を新設し、T3 Code の子タスク委任（`delegate_task` / ACP CLI フォールバック）への接続インターフェース（`T3DelegationAdapter`, `create_t3_executor`）を整備。
   - `scripts/run_harness.py` に `--executor {synthetic, t3}` および `--manifest` 引数を追加。
9. **テスト**: `python -m pytest -v` で 41 件全件通過。

## 保留（承認・指示待ち）

- **評価用 24 件の作成**: held-out 24 件（反例 12 件のタグ付けを含む）の作成者決定と作成作業。
- **実験の実行**: 最大 1,920 回のモデル呼び出しがかかるため、予算上限の承認と実行指示。

## 再開手順

1. `python -m pytest -q` を実行し、41 件が通過することを確認する。
2. `python scripts/verify_seals.py verify --manifest research/seal_manifest.json` で封印の整合性を確認する。
3. `python scripts/run_harness.py --mode mechanism_check` で動作確認を行う。
4. ユーザー承認後、評価用 held-out 24 件の作成と、予算を設定したベンチマーク実行に進む。
