# TOMBO 検査レポート

目的: Audit Ommatidia empirical paper, research protocol, evaluation specification, and related work claims against evidence and operational standards.

判定: 必須の確認が残り、停止している

停止理由: capability\_limit

## 証拠で確かめたこと

- PROTOCOL.md specifies 720 runs by pooling 24 dev and 24 held-out cases; the held-out denominator must be corrected to 24 cases, with minimum recommended pilot 120 and held-out 120. (支持)。範囲: research/PROTOCOL.md
- EVALUATION\_SPEC.md asserts double-blind evaluation and treats repeated trials as independent; agents observe condition prompts, so blinding applies only to assessors, and repeated trials are clustered. (支持)。範囲: research/EVALUATION\_SPEC.md
- Section 5 of manuscript remains pending; no empirical execution or gold labels exist before freeze. (支持)。範囲: paper/manuscript-ja.md
- Related work descriptions of Adaptive-RAG (cannot adapt), Reflexion (strictly scalar oracle), and STORM (static/no trajectory) overstate absence of capability compared to primary sources. (支持)。範囲: references/RELATED\_WORK.md

## 目的に影響する未確認事項

- Are empirical evaluation results, full monetary costs, and open-web generalisation measured and validated? Empirical metrics, monetary costs, and generalisation cannot be resolved prior to authorised experiment execution.

## 次に行う確認

実行可能な次の検査は選ばれていない。

## 前回から変わった箇所

- claim-protocol-count: unverified → supported。Evidence assessment proposal
- claim-eval-blinding: unverified → supported。Evidence assessment proposal
- claim-manuscript-status: unverified → supported。Evidence assessment proposal
- claim-lit-accuracy: unverified → supported。Evidence assessment proposal
- gap-heldout-denominator: open → resolved。Evidence assessment proposal
- gap-eval-blinding: open → resolved。Evidence assessment proposal
- gap-lit-accuracy: open → resolved。Evidence assessment proposal

## 適用範囲と利用量

判定は今回の目的、登録された証拠、明示された適用範囲に限る。外部操作の承認を代行しない。

- 追加ラウンド: 1
- モデル呼出し: 2
- ツール呼出し: 3
- 経過時間: 37226ms
- 合計トークン: 未取得
- 費用: 未取得

会話内モード。ヘルパーによる追加API呼出しは0件。SDKのモデル呼出し数はローカル提案適用回数で、会話側の生成トークン数・費用・生成時間は別途不明である。
