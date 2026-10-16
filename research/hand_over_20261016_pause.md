# 引き継ぎ（2026-10-16）: 実行時凍結の後回しと held-out の状態

## 現在の状態

- 論文は protocol 段階。評価用24件の結果はなく、実験は開始していない。
- 封印（`research/seal_manifest.json`）:
  - protocol・`EVALUATION_SPEC.md`・dev manifest・held-out manifest は、すべて検証が通る。
  - `scripts/verify_seals.py verify` の全体は、runtime freeze の不一致（`codeHash`）で失敗する。
- runtime freeze（`research/runtime_freeze_r4.json`）は古いまま。**意図的な後回し**。コードが確定してから 1 回だけ作成する。作成前に検証を通すために凍結を作り直さないこと。

## held-out

- 封印されている held-out manifest（`research/datasets/heldout/manifest.json`）は、作業ツリーに未追跡のコピーとして戻してある。残りのデータ（cases・gold・evidence など）はアーカイブ `D:\archive\2026\ommatidia-heldout-untracked\` にある。
- 候補は 3 つあり、いずれも正式版として未承認。
  - `heldout_r4_candidate`（candidate_rebuild）
  - `heldout_r5_candidate`（candidate）
  - `heldout_r6_candidate`（独立した公開のみの監査が必要と明記）
- 正式版の決定、作成者、監査は未了。監査は公開パッケージ（`public_packets` など）のみを対象とし、gold と盲検解除キー（`unblinding_key.json`）は読まない。

## 再開時の注意

1. held-out の未追跡ファイルは、コミットしない。
2. release 検査は、作業ツリーが clean かつ承認済みの評価パッケージを要求する。現時点では満たさないため、実験は開始できない。
3. 実 T3 ホストの費用上限、予算の強制、独立監査が揃うまで、実験は行わない。
