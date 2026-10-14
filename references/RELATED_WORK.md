# 関連研究台帳 (Related Work Register)

最終確認: 2026-10-14T11:01:56Z から 11:03:04Z（UTC）。
確認者: 原稿復旧サブエージェント（`claudeAgent` / `claude-opus-5-5`）。
確認方法: 各論文の公式版（ICLR proceedings、ACL Anthology、NeurIPS proceedings）の PDF と BibTeX を取得し、`pdftotext` で抽出した本文を `grep` で照合した。各記述の根拠は [verification-ledger.json](verification-ledger.json) の claim ID で示す。

記述は2種類に分ける。

- **支持**: 論文の該当箇所を言い換えた記述。台帳に原文の抜粋がある。
- **推論**: 読んだ節に記載がないという本稿の読み。網羅的な文献調査に基づく不在の主張ではない。

確認範囲は以下の4論文に限る。Ommatidia の機構の組み合わせが他の文献に存在しないとは主張しない。

---

## 1. Self-RAG

- 書誌: Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, Hannaneh Hajishirzi. Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. ICLR 2024, pp. 9112–9141. arXiv:2310.11511.
- 公式版: <https://proceedings.iclr.cc/paper_files/paper/2024/hash/25f7be9694d7b32d5cc670927b8091e1-Abstract-Conference.html>
- 備考: openreview.net は HTTP 403 を返したため、ICLR proceedings 版を使った。

| ID | 種別 | 記述 | 箇所 |
| :--- | :--- | :--- | :--- |
| selfrag-1 | 支持 | Retrieve、IsRel、IsSup、IsUse の4種の反省トークンを語彙に加える。 | §3.1, Table 1 |
| selfrag-2 | 支持 | 批評モデルが反省トークンを学習データへオフラインで挿入し、生成モデルを通常の言語モデル目的関数で学習する。 | §3.2 |
| selfrag-3 | 支持 | 生成モデルは Llama2 7B と 13B である。実験では1文を1セグメントとして扱う。 | §3.1, §4.3 |
| selfrag-4 | 支持 | 推論はセグメント単位のビームサーチで、反省トークン確率の重み付き線形和をスコアとし、ソフト制約またはハード制約を課す。 | §1, §3.3 |
| selfrag-5 | 支持 | 著者は、引用で十分に支持されない出力を生成しうると述べている。 | Ethical Concerns |
| selfrag-6 | 推論 | 生成モデルの学習を前提とするため、重みを学習できないホスト型モデルには公開された手法をそのまま適用できない。 | §3.2 から導出 |
| selfrag-7 | 推論 | §3.1 から §3.3 には、主張・仮説・未確認事項をタスク全体で保持する外部記録の記述がない。 | §3.1–§3.3 |

Ommatidia との差は設計上のものであり、効果は検証していない。Ommatidia はモデルを学習せず、タスク単位の主張と未確認事項を外部の理解状態に記録する。

---

## 2. Adaptive-RAG

- 書誌: Soyeong Jeong, Jinheon Baek, Sukmin Cho, Sung Ju Hwang, Jong C. Park. Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity. NAACL 2024 (Volume 1: Long Papers), pp. 7036–7050. arXiv:2403.14403.
- 公式版: <https://aclanthology.org/2024.naacl-long.389/>

| ID | 種別 | 記述 | 箇所 |
| :--- | :--- | :--- | :--- |
| adaptiverag-1 | 支持 | 非検索・単一段階・複数段階の戦略を、解答を始める前に質問の複雑度を分類して選ぶ。 | §3.2, p. 7040 |
| adaptiverag-2 | 支持 | 複数段階戦略では、各段階の検索が先行文書と中間回答からなる文脈 $c_i$ を入力に取る。後段の検索は前段で得た内容に応じて変わる。 | §3.1, 脚注1, p. 7039 |
| adaptiverag-3 | 支持 | 複雑度分類器は T5-Large を学習したものである。 | §4.4, p. 7041 |
| adaptiverag-4 | 支持 | 分類器の学習ラベルは、3戦略の解答結果とデータセットの帰納バイアスから自動で作る。著者は誤ラベルの可能性と、理想的な分類器との性能差を認めている。 | §3.2, p. 7040; Limitations, p. 7044 |
| adaptiverag-5 | 推論 | 取得した証拠が矛盾したときに、選んだ戦略を途中で切り替える手順は記述されていない。 | §3.1–§3.2 |
| adaptiverag-6 | 推論 | 取得文書を共通の一次出所でまとめる手順は記述されていない。 | §3–§4 |

Adaptive-RAG は質問ごとに戦略を事前に選び、複数段階戦略の中では検索文脈を更新する。したがって「Adaptive-RAG には動的な適応がない」とは書かない。Ommatidia は、調査の途中で記録された未確認事項から次の探索役を組み立てる設計である。

---

## 3. STORM

- 書誌: Yijia Shao, Yucheng Jiang, Theodore A. Kanell, Peter Xu, Omar Khattab, Monica S. Lam. Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models. NAACL 2024 (Volume 1: Long Papers), pp. 6252–6278. arXiv:2402.14207.
- 公式版: <https://aclanthology.org/2024.naacl-long.347/>

| ID | 種別 | 記述 | 箇所 |
| :--- | :--- | :--- | :--- |
| storm-1 | 支持 | 関連トピックの Wikipedia 記事の目次から $N$ 個の観点を生成し、基本事実を扱う固定の観点を1つ加える。 | §3.1, p. 6255; Algorithm 1 |
| storm-2 | 支持 | 観点集合は対話の開始前に生成し、各観点が並列に質問生成を導く。 | §3.1; Algorithm 1 |
| storm-3 | 支持 | 各観点で、執筆者役と検索に基づく専門家役が最大 $M$ ラウンドの多ターン対話を行う。執筆者の次の質問は対話履歴に依存するため、追質問は前の回答に応じて変わる。 | §3.2, p. 6255 |
| storm-4 | 支持 | 専門家役は質問を検索クエリに分解し、Wikipedia の指針に沿う規則ベースのフィルタで信頼できない情報源を除く。 | §3.2, pp. 6255–6256 |
| storm-5 | 支持 | 著者は、収集情報がインターネット上の支配的な情報源に偏り、宣伝的な内容を含みうること、生成記事が無関係な事実を結び付けることを報告している。 | §6; Limitations, p. 6260 |
| storm-7 | 支持 | DSPy 上のゼロショットプロンプトで構築され、モデルの学習は行わない。 | §4.4; Appendix B |
| storm-6 | 推論 | 同じ原記事の転載をまとめる手順は手法記述にない。規則ベースのフィルタは信頼性を対象とし、出所の共有は対象としない。 | §3 |

STORM は解説記事の作成を目的とし、各対話の中では追質問が前の回答に応じて変わる。観点集合は対話の前に決まる。したがって「STORM は適応しない」「探索の軌跡を持たない」とは書かない。Ommatidia は主張の成否を判定する目的で、調査途中の未確認事項から探索役を作る設計である。

---

## 4. Reflexion

- 書誌: Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao. Reflexion: Language Agents with Verbal Reinforcement Learning. Advances in Neural Information Processing Systems 36 (NeurIPS 2023), pp. 8634–8652. arXiv:2303.11366.
- 公式版: <https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html>
- 備考: NeurIPS proceedings の PDF と BibTeX は著者を5名とする。arXiv の現行の要旨ページは Edward Berman を加えた6名を挙げる。

| ID | 種別 | 記述 | 箇所 |
| :--- | :--- | :--- | :--- |
| reflexion-1 | 支持 | Actor、Evaluator、Self-Reflection の3モデルと、反省文を保持するメモリ（上限は通常1から3件）からなる。 | §3 |
| reflexion-2 | 支持 | 自己反省モデルは、二値またはスカラーの評価信号と軌跡から自然言語のフィードバックを作り、次の試行の文脈に加える。 | §1; §3 |
| reflexion-3 | 支持 | 枠組みは、スカラー値と自由形式の言語のどちらのフィードバックも、外部または内部で模擬した情報源から受け取れる。 | Abstract |
| reflexion-4 | 支持 | 実験の評価信号は、推論課題では完全一致採点、意思決定課題では事前定義のヒューリスティックまたは LLM による分類、プログラミング課題では自作の単体テストである。 | §1; §3; §4.1–§4.3 |
| reflexion-5 | 支持 | 反省は試行と試行の間に作られ、次の試行へ渡される。試行は評価器が正解と判定するまで、最大試行数の範囲で繰り返す。 | §3; Algorithm 1; §4.2 |
| reflexion-6 | 支持 | 著者は、LLM の自己評価（またはヒューリスティック）への依存、成功の形式的保証がないこと、局所最適に陥る可能性を挙げる。 | §1; §5 |
| reflexion-8 | 支持 | モデルの重みを更新せず、言語的フィードバックでエージェントを強化する。 | Abstract |
| reflexion-7 | 推論 | 主張を証拠と出所に対応づける構造化記録や、重複した情報源を除く手順は記述されていない。 | §3–§4 |

Reflexion の反省は試行間の言語的フィードバックであり、評価器の信号を契機とする。その信号は外部の正解に限らず、自作テストや LLM による判定も含む。したがって「Reflexion はスカラー報酬だけに依存する」「外部の正解判定器を必須とする」とは書かない。Ommatidia は1回の試行の中で未確認事項の記録を更新する設計である。

---

## 5. 比較表

先行研究の列は上記の claim ID に基づく。「記述なし」は推論の行を指す。Ommatidia の列は [PROTOCOL.md](../research/PROTOCOL.md) の設計であり、効果は検証していない。

| 項目 | Self-RAG | Adaptive-RAG | STORM | Reflexion | Ommatidia（設計、未検証） |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 目的 | 検索・生成・自己批評を1モデルで行う | 質問の複雑度に応じた検索戦略の選択 | Wikipedia 型記事の事前調査と執筆 | 試行の繰り返しによる行動の改善 | 主張の成否を判定するための調査 |
| 状態の置き場所 | 生成文脈と反省トークン | 検索文脈 $c_i$（文書と中間回答） | 観点ごとの対話履歴と参照集合 | 反省文のメモリ（通常1から3件） | 外部の理解状態（目的・主張・仮説・証拠・未確認事項・検査履歴） |
| 観点や役割が決まる時点 | 単一モデル | 質問ごと、解答の前 | 対話の開始前に観点集合を生成 | 3モデルの固定構成 | 調査途中の未確認事項から生成 |
| 途中での適応 | セグメントごとの検索要否の判定 | 複数段階戦略の中で検索文脈を更新 | 対話内の追質問 | 試行間の言語的反省 | 理解状態の更新後に次の探索役を選ぶ |
| 出所の扱い | IsSup による支持度の判定 | 記述なし | 規則ベースの信頼性フィルタ。転載の集約は記述なし | 記述なし | 本文ハッシュによる同一文の重複排除と範囲照合 |
| 学習の要否 | 生成モデルと批評モデルを学習 | 分類器（T5-Large）を学習 | 学習なし（ゼロショットプロンプト） | 重みの更新なし | 学習なし |

---

## 6. 本提案の主張の範囲

1. Ommatidia は、外部の理解状態、未確認事項から作る探索役、出所の照合、複合予算内での停止を組み合わせる設計である。
2. 4論文以外の文献を網羅的に調べていないため、この組み合わせが新しいとは主張しない。
3. 実モデルによる比較試行は0件である。効果や優位性は主張しない。検証は [PROTOCOL.md](../research/PROTOCOL.md) と [EVALUATION_SPEC.md](../research/EVALUATION_SPEC.md) の計画（開発24ケース × 5条件 = 120試行、評価24ケース × 5条件 = 120試行）に従う。
4. プロトコルが定める本文ハッシュの重複排除は、同一の文しか検出しない。言い換えを伴う転載はこの手順の対象外である。

---

## 7. 改訂履歴

- 2026-10-14（前版、調査サブエージェント）: 4論文の初版の記述と比較表を作成した。
- 2026-10-14（本版、原稿復旧サブエージェント）: 公式版で再照合した。Adaptive-RAG、STORM、Reflexion の記述を一次資料の範囲に限定した。Adaptive-RAG 節で「単一段階検索」の語が無関係な文字列に置き換わっていた箇所を直した。根拠のない比較表の行（資源予算の管理、停止条件）を削除した。原稿の参考文献にあった頁番号と著者の誤りは [verification-ledger.json](verification-ledger.json) の `manuscript_corrections` に記録した。
