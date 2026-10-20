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

## 監査結果（2026-10-16）

- r6 公開パッケージの独立監査（監査者: antigravity / gemini-3.8-flash-medium、PM: claudeAgent / claude-opus-5-5）は、判定 needs_review。公開側の欠陥は見つからなかった。
- 非公開側の照合は未完了。
  - sealedPrivateManifestSha256 は、`cases/private_manifest.json` のハッシュ（`9924a137…23fa`）と一致することを確認済み（中身は未読）。
  - 反例 12 件のタグは、オーナーが `cases/validate_private.py` で確認する。
- 公開マニフェストの改行コードは LF に固定した（ハッシュ `5e8f…160f`）。
- `research/datasets/heldout/manifest.json` は `.gitignore` に追加した。封印の検証には影響しない。ただし、ignore されたファイルは release 検査の dirty 判定に含まれない。
- 監査者が許可外のファイル（`harness.py`、`validate_public.py` の実行、`hand_over_holdout_r6.md`、`.gitattributes`）に触れたことは、オーナーの判断で容認した。書き込みはアーカイブに残っていない。

## 非公開側の照合（2026-10-16、オーナー実行）

- `cases/validate_private.py` を実行し、`PRIVATE VALIDATION PASS checks=181 records=24`。
- 評価用 24 件（ドメインごとに 8 件）、反例 12 件（タグと一致）、非公開マニフェストのハッシュ（公開側の `sealedPrivateManifestSha256` と一致）を確認。
- このスクリプトはプロジェクト内の整合性検査であり、第三者監査ではない。
- r6 を正式版にするかは未決（オーナーの判断待ち）。
