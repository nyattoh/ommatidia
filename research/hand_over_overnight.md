# 夜間作業の引き継ぎ（2026-10-15）

## 現在の状態

- ブランチ `main`。origin より 3 件先行（未 push）。
- 作者情報は `anonymous <nyattoh@users.noreply.github.com>`（ユーザー指定）。
- 実験は 0 件。held-out 評価用ケースは未作成。実行予算は未承認。
- ランタイム検証の判定は `fail` のまま（`research/task-gate-runtime-state.json`）。

## 今回の完了事項

1. 作者情報の書き換え（未 push の 2 件）。
2. Zenodo 関連をリポジトリから除外。`paper/zenodo/` と `paper/zenodo-ommatidia-20261015/` を `D:\inbox\zenodo-ommatidia-20261015\` に移動（`metadata/`、`archive/`）。GitHub 側には入っていない。
3. ユーザー名入りのパスを `<HOME>` に置換（5 ファイル、10 箇所）。
4. 評価条件を確定（`research/EVALUATION_SPEC.md` §5.2 と原稿）。Wilcoxon の同順位・零差の扱い、H4 の分母 12 件（反例ケース）。
5. ランタイム残件のうち 2 件。
   - 残件 1: 使用量の集計で未知（None）のコストとトークンを 0 扱いしないよう修正。実行開始時は 0 を明示（`src/ommatidia/conditions.py`、`src/ommatidia/state.py`）。
   - 残件 4: 古いロックの回収。PID が存在しない場合のみ回収し、PID のないロックは阻止（`src/ommatidia/ledger.py`）。
6. テスト: `python -m pytest -q` で 29 件通過（新規 5 件を含む）。

## 未完了（ランタイム残件、`research/task-gate-runtime-state.json` 由来）

- 残件 2: 条件 A・B で予算チェックを実装していない。
- 残件 3: 証拠の撤回時に READY 判断を取り消す処理がない。
- 残件 5: `ResearchHarness` の実行経路で `verify_environment` を呼ばず、データ・プロンプト・コードを封印していない。
- 残件 6: Evaluator と Types を `EVALUATION_SPEC.md` に合わせていない（FinalJudgement、FDA、Recall_crit、FAR、DSC）。
- 残件 7: 対応のある比較の信頼区間が、分散ゼロ・少数標本で `[0.0, 0.0]` を返す。
- 残件 8: 合成の委任実行関数を、実際の T3 委任に差し替えていない。

## 保留（承認が必要）

- 実験の実行（最大 1,920 回のモデル呼び出し）と予算上限の設定。
- 評価用 24 件の作成（作成者の決定が必要。反例 12 件のタグ付けを含む）。
- push（権限で拒否されたまま。下記）。

## push について

`git push origin main` は夜間作業中に権限で拒否されました。許可をいただくか、手元で次を実行してください。

```
git -C d:/develop/works/ommatidia push origin main
```

## 画像・動画

今回は GUI もデザイン成果物もないため、画面記録と動画は作っていません。生成した画像・動画はゼロで、容量の消費はテキストだけです。

## 再開手順

1. `git status` と `git log origin/main..main` で、未 push の作業を確認する。
2. `python -m pytest -q` を実行し、29 件が通ることを確認する。
3. 残件 2、3、5、6、7、8 を、この順で（依存のない順に）進める。各項目はテストを追加してから閉じる。
4. 残件がすべて閉じた後、`scripts/task_gate.py` 相当の確認を行い、判定を更新する。
5. 実験には、予算の承認と held-out の作成が前提になる。
