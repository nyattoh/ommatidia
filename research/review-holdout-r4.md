fail research/hand_over_holdout_r4.md:71 exposes case-linked expected outcomes; research/EVALUATION_SPEC.md:99 requires domain and availableSources, both absent from all 24 candidate public packets.

# heldout_r4_candidate 独立監査

監査日: 2026-10-15（UTC）。Reviewer: OpenAI Codex、gpt-6.1-sol、reasoning effort high。候補作者は handover 記載によれば Google gemini-3.8-flash-high / Antigravity。異なるベンダーによるレビューであり、ベンチマーク順位・費用・トークン数の実測は主張しない。

**勧告: 現状の候補を新しい事前登録リリースとして承認しない。** 公開部分の構造とハッシュは概ね整合するが、期待判定の露出、凍結仕様との不一致、出典の検証不足がある。以下は公開資料の監査であり、解答キーの内容監査・候補評価・実験ではない。

## 閲覧境界と実施内容

- 新旧の `gold/`、すべての `cases/`、結合ケースファイル、`unblinding_key.json` は開かず、解析・検索・評価・内容のハッシュ計算を行わなかった。禁止領域は名前、個数、サイズ、更新時刻だけを扱った。
- 候補の `public_packets/`、`evidence/`、パス・ハッシュを記したマニフェスト、protocol/spec、handover、関連する実装の読取り、公開一次資料の確認を行った。
- Python によるデータ検証には `builtins.open`、`io.open`、`os.open` に禁止パスを拒否するガードを付けた。`load_dataset_partition`、gold loader、候補 evaluator、研究用モデル呼出しは実行していない。
- 実行したデータローダーは、先に実装を確認した `load_public_packets(Path("research/datasets/heldout_r4_candidate"), verify_hashes=True)` のみ。公開パケットの型検証と `check_public_payload`、公開ファイルの SHA-256/サイズ照合を行った。
- 許可された handover の §3.3 には期待判定を含むメタデータがあり、このレビュー文脈に入った。その対応関係・値は本報告に再掲しない。「gold ファイル未閲覧」と「期待判定情報にも一切接していない」は区別する。
- 作者の「101 tests pass」「gold schema 検証済み」「私有ファイルを含む102件のハッシュ一致」は作者の申告。今回のレビューでは試験一式を再実行しておらず、独立確認済みとは扱わない。

## 確認できた構造と結び付き

1. ファイル名の棚卸しは public_packets 24、gold 24、cases 24、evidence 30。候補 manifest の102エントリと、manifest 自身を除く実ファイル名集合は一致し、未登録・欠落名は0。
2. 公開24パケットは24種類の一意な taskId を持ち、ID/パスによる領域分布は Software Engineering / Workflow Automation / Document Research が各8件。開発用 public_packets のファイル名とのID交差は0。問題内容の独立性や解答分布はこれでは確認できない。
3. 公開パケット24件と証拠文書30件、計54ファイルの SHA-256 と sizeBytes が候補 manifest と一致。禁止された残り48ファイルの内容ハッシュは再計算していない。
4. 公開ローダーの型検証と再帰的な `check_public_payload` は24件とも成功した。これは公開フィールド・参照先に関する検査で、解答文字列との照合ではない。
5. 30証拠文書の先頭行すべてに fictional test dataset の表示がある。一方、24個の inline evidence passage には表示が引き継がれず、24パケットとも公開一次資料のURLを含まない。作問上の架空資料と実在する規格の根拠は、handover を通じて初めて結び付く。
6. `research/datasets/heldout_r4_candidate/manifest.json` の SHA-256 は `fa5b60526ec72d6af74f45e1197a3f61cb0e08a058524176e5283733f7718df9`、サイズ16802 bytesで、上位候補 manifest の記載と一致。
7. 上位候補 manifest が指す protocol、evaluation spec、conditions.py、types.py、evaluator.py のハッシュ・サイズは現物と一致。記録された8つのプロンプトハッシュも一致。現在の runtime files は R3 freeze の files mapping と一致した。
8. 上位候補 manifest の H4 集合は12個の異なる公開IDを指定している。各ケースがその分析分類に内容上適合するかは解答キーに触れずには認定しない。
9. `research/holdout_manifest_r4_candidate.json:3` は `candidate_rebuild`。`research/runtime_freeze_r3.json:59` は `blocked_rebuild_required`。現物は候補を承認済みの実行用 freeze に昇格させていない。

## 指摘

### F1 — P1: handover が期待判定情報を設計・レビュー文脈へ露出する

**根拠:** `research/hand_over_holdout_r4.md:71`（§3.3）はケースと期待判定を結び付けて記載する。`research/PROTOCOL.md:142` は開発・プロンプト改良・単体試験中の held-out 解答閲覧を禁じる。公開パケットに私有フィールドがないことだけでは、この別経路の露出を防げない。

**影響:** この文書を読む後続の設計・実装者に対して「解答情報を見ずに凍結した」とは主張できない。今回のレビューも answer-bearing metadata に接したため、その境界を明示した。

**最小対応案:** 現在の候補と記録を履歴として保全し、通常の開発者・実験者向け handover からケース別の期待判定を隔離する。既に露出した情報は削除で未閲覧には戻らない。閲覧した主体・時点と以後の設計変更を確認し、同一候補を維持できる根拠がなければ、新たな隔離作問文脈で別版を作成する。本レビューでは判定対応を伝達せず、実装タスクも発行していない。

### F2 — P1: 24パケットすべてが凍結された入力仕様の必須項目を欠く

**根拠:** `research/EVALUATION_SPEC.md:99` の required は `domain` と `availableSources` を含む。候補の `public_packets/*.json` 24件は両方を欠く。例: `public_packets/heldout_r4_se_01.json`。現在の `src/ommatidia/types.py:671` の TaskPacket 型はこれらを要求しないので、作者の型検証成功と凍結仕様適合は同義ではない。

**影響:** `availableSources` が規定する sourceGroup / description / entryLocator の一覧が与えられない。30文書中6文書はどのパケットの evidence locator にも登場せず、仕様にある情報探索の入口を再現できない。例は `evidence/software_engineering/git_commitgraph_v2_rfc.md`、`evidence/workflow_automation/openapi_v31_directive.yaml`、`evidence/document_research/gov_procurement_wcag_aa.md`。これは文書が実行時に絶対取得できないという認定ではなく、パケットに規定の入口がないという指摘。

**最小対応案:** 作問側で仕様に合う公開ソース一覧を与えるか、新しい事前登録で実装と仕様の入力対応・資料発見範囲を明記する。現行仕様への完全適合として承認しない。

### F3 — P2: negative control の割当説明が凍結 protocol と異なる

**根拠:** `research/PROTOCOL.md:133` は領域ごとに benchmark 全体で4件、その内訳を Dev 2 / Held-Out 2 と定める。一方 `research/hand_over_holdout_r4.md:71` は候補の各領域に4種類の control を含むと説明する。文書上の held-out 割当は、protocol の各領域2件と候補説明の各領域4件で一致しない。

**影響:** N=24 や領域各8件だけが合っていても、control 構成を含む事前登録適合は認定できない。私有分類の実際の割当は検証していない。

**最小対応案:** 新版の事前登録で割当数・選定手順を明記し、作者側の隔離した検証で確認する。本報告はケース別の分類や期待判定を示さない。

### F4 — P1: NIST の旧版引用を current として扱う

**根拠:** `research/hand_over_holdout_r4.md:116` は旧 `800-63-3/sp800-63b.html#memsecret` と旧節番号を Verified とする。`public_packets/heldout_r4_dr_07.json:27` の版は `800-63B`、同じ evidence の validity は current で、対象時点を旧版へ限定していない。

**一次資料:** [NIST CSRC SP 800-63B-4 Final](https://csrc.nist.gov/pubs/sp/800/63/b/4/final) の Document History は **2025-07-31 Final**、Supersedes は SP 800-63B（2020-03-02）。2026-10-15 時点の引用を旧版のまま最新版として認定できない。

**最小対応案:** freeze 前に B-4 とその対応節を参照するか、旧版に基づく歴史的監査であることと適用時点を明記する。章番号を機械的に置換せず、作問側が公開証拠の範囲を再確認する。内部監査結果や解答キーの妥当性は判定していない。

### F5 — needs_review / P1: ISO の概要URLでは A.8.1 の具体的義務を確認できない

**根拠:** `research/hand_over_holdout_r4.md:111` は ISO 概要ページだけで A.8.1 の検証を Verified とする。`evidence/document_research/iso27001_endpoint_policy_excerpt.md:5` および対応する公開パケットは自動 session lock と inactivity timeout を同 control の規範的義務として扱う。

**一次資料の確認範囲:** [ISO/IEC 27001:2022 公式概要](https://www.iso.org/standard/27001) は規格の版・主題を確認できるが、取得できた本文に当該 control の詳細やその義務の根拠がない。概要だけでこの文言が正しいとも誤りとも断定しない。

**最小対応案:** 正規に利用可能な該当条文と節・版を示して独立検証する。それができなければ、架空の社内 endpoint policy と ISO 規格本文を分け、未確認の規範的主張を Verified のまま凍結しない。gold 内容の監査を要求するものではない。

### F6 — P2: 出典種別・節番号・参照範囲の記録が不正確

- **C11:** `research/hand_over_holdout_r4.md:96` の cppreference は二次資料。代替の一次資料 [WG14 N1570 committee draft](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf) は取得でき、§7.17.3（印刷頁275）と §5.1.2.4 を参照できる。「C11 最終規格そのもの」ではなく、2011-04-12 の委員会草案と明記して置き換える。
- **Retry-After:** `research/hand_over_holdout_r4.md:95` と `evidence/software_engineering/http_retry_after_spec.md:5` は RFC 9110 §10.2.7 を挙げる。実際の節は [RFC 9110 §10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3)。本文の整数秒 / HTTP-date の主題は確認できるが、節番号は修正が必要。
- **UK GDPR:** handover の Data Protection Act 2018 目次URLから Article 17 自体を検証したとはいえない。取得できた一次条文は [UK GDPR Article 17(3)(b)](https://www.legislation.gov.uk/eur/2016/679/article/17/data.html)。国内法上の法的義務という範囲を、この条文へ直接結び付ける。
- **SEC:** `research/hand_over_holdout_r4.md:117` の旧URLはこの取得では実質的な release 本文を返さなかったが、[SEC Release 33-7881 公式本文](https://www.sec.gov/files/rules/final/33-7881.htm) は取得できた。主題は Regulation FD と Rules 10b5-1 / 10b5-2。§II.B.2 は materiality を文脈依存の基準として説明し、earnings forecasts も論じるため、関連する一次資料ではある。ただし Rule 10b-5 全文や特定の架空 forecast の materiality を直接認定する資料ではない。具体的な参照節と主張範囲を記録する。
- **POSIX:** 指定された POSIX.1-2017 URL と edition 固定URLは取得エラー。取得できた [POSIX.1-2024 fork 公式本文](https://pubs.opengroup.org/onlinepubs/9799919799/functions/fork.html) を、2017版の検証済み根拠へ無断で読み替えない。候補の2017版に対する検証状態は **needs_review**。

**影響:** `research/hand_over_holdout_r4.md:88` の「全技術シナリオが verified public specifications に基づく」という一括認定を支持しない。公開ソースごとの確認日時・版・節・検証範囲を更新する必要がある。

### F7 — P2: 架空証拠が実在規格の条件を落として断定する

以下は公開証拠文の出典対応の問題であり、ケースの採点や期待判定は示さない。

- `evidence/software_engineering/async_taskgroup_spec.md:5` は any child exception と全例外の ExceptionGroup 化を断定する。[Python 3.11 の TaskGroup 公式仕様](https://docs.python.org/3.11/library/asyncio-task.html#task-groups) は CancelledError を区別し、KeyboardInterrupt / SystemExit は別扱い。対象例外を明記する必要がある。handover の可変 `/3/` URL は現在3.15文書へ解決したので、パケットに記す3.11に合わせた版固定も必要。
- `evidence/workflow_automation/openapi_v31_directive.yaml:4` は `nullable` を禁止し、null の表現を特定の type 配列に限定する。[OpenAPI 3.1.0 Schema Object](https://spec.openapis.org/oas/v3.1.0#schema-object) は任意のプロパティを許容する。`nullable` に旧版の null 許容の意味がないことと、そのキー自体を禁止することは異なる。社内 validator の追加制限なら、規格の禁止規定と分ける。
- `evidence/workflow_automation/oauth_token_rotation_spec.md:5` は再利用検知で grant の全 token を必ず revoke すると記す。[RFC 6749 §10.4](https://www.rfc-editor.org/rfc/rfc6749#section-10.4) だけではその義務を裏付けられず、更新元の [RFC 9700 §4.14.2](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14.2) が説明する rotation/replay 検知では active refresh token の失効を述べる。access token も含む全 token の必須失効へ拡張しない。
- `evidence/document_research/eu_ai_act_article5_excerpt.md:5` は Article 5(1)(c) の社会的評価について、後続する適用条件を省略する。[EUR-Lex 公式条文](https://eur-lex.europa.eu/legal-content/EN-FR/TXT/?uri=CELEX%3A32024R1689) の同号は、評価結果が所定の不利益取扱いにつながる条件を含む。今回その条件は公式検索結果本文で確認できたが、単一言語の本文URLは bot challenge を返した。無条件の禁止へ拡張せず、条件を含む出典対応を確認してから freeze する。

**最小対応案:** 作問側が適用条件を公開文書に明示し、架空の追加方針と実在規格の規定を区別する。修正時に解答情報を設計者へ渡さない。

### F8 — P2: 二つの passage は locator の文書に逐語的に存在しない

**根拠:** `public_packets/heldout_r4_se_03.json:21` と `public_packets/heldout_r4_wa_03.json:21` の passage は、各 locator の `c11_atomic_barrier_spec.c` / `webhook_signature_audit.py` にそのままの部分文字列として存在しない。ソースのコメント接頭辞やインデントが除かれ、コメントとコードが連結されている。passage 自体の SHA-256 は24件すべて contentHash と一致する。

**影響:** passage の自己ハッシュ一致は、参照文書から同じ文字列を再取得できる証明にはならない。引用の正規化方式・抽出範囲が記録されていないため、独立した再取得の同一性確認が曖昧になる。

**最小対応案:** 逐語的に引用するか、コメント除去・空白処理・抽出行の規則と原文範囲を版固定する。架空表示も inline evidence まで引き継ぐ方法を定める。引用内容の解答キーとの一致は確認していない。

## その他の一次資料確認

確認日は2026-10-15。以下の「確認」は公開規格の主題・適用範囲についてであり、個別ケースや解答キーの正しさを認定しない。

- SE-05: [SQLite WAL 公式文書](https://www.sqlite.org/wal.html) は concurrency と single writer の説明を確認。
- SE-06: [Git commit-graph](https://git-scm.com/docs/commit-graph) および [commit-graph-format](https://git-scm.com/docs/commit-graph-format) は世代データの説明を確認。架空の社内 mirror 方針の優先順位までは規定しない。
- SE-07: [Linux epoll(7)](https://man7.org/linux/man-pages/man7/epoll.7.html) は edge-triggered / EAGAIN の説明を確認。架空 telemetry の実態は確認不能。
- SE-08: [PEP 484 variance](https://peps.python.org/pep-0484/#covariance-and-contravariance) の mutable/read-only collections の区別を確認。
- WA-02: [RFC 7519 §4.1.4](https://www.rfc-editor.org/rfc/rfc7519#section-4.1.4) を確認。小さな clock skew の許容余地と exp claim 自体が任意である点を含む。候補の zero-skew 設定は架空のローカル方針として区別する。
- WA-03: [MITRE CWE-208](https://cwe.mitre.org/data/definitions/208.html) の名称と timing discrepancy の説明を確認。個別 Python primitive の根拠が必要なら、Python の公式API文書も別に必要。
- WA-04: 元の AWS URL は取得失敗。代替の公式 [message deduplication ID](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/using-messagededuplicationid-property.html) と [outage recovery](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/designing-for-outage-recovery-scenarios.html) で5分の範囲を確認。
- WA-05: 元の Kafka URL は現行文書への redirect 案内。版を限定した [Kafka 3.5.2 KafkaConsumer](https://kafka.apache.org/35/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html) で offset/commit と処理保証の注意を確認。架空ログは実測ではなく、具体的な revoke 時の commit 不成立をこの一般説明だけで実証したとは扱わない。
- WA-07: [GitHub failed deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries) は自動再配送しないと明記。[GitHub best practices](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks#use-the-x-github-delivery-header) は再配送でも同じ delivery GUID を使うと明記。欠落した架空の処理記録をこれで補完しない。
- WA-08: Stripe CLI 1.53.1 の `stripe docs /api/idempotent_requests` で [公式API文書](https://docs.stripe.com/api/idempotent_requests) を取得。API v1 の同時実行競合では実行開始前の結果を保存しない旨を確認。公式文書は現在 v1/v2 を区別するため、候補にも対象API系列の明示が必要。
- DR-04: [Apache License 2.0 §4(d)](https://www.apache.org/licenses/LICENSE-2.0) の条件付きの帰属表示保持を確認。NOTICE という同名ファイルを常にそのまま残す義務へ狭めず、本文の代替掲載方法も区別する。
- DR-05: [MIT License](https://opensource.org/license/mit) の notices に関する条件を確認。架空の SaaS 展開がどのコピー・配布に該当するかはこの一般条項だけでは認定しない。
- DR-06: [WCAG 2.2 2024-12-12 Recommendation](https://www.w3.org/TR/2024/REC-WCAG22-20241212/) は §2.5.8 AA と §2.5.5 AAA の区別および両方の例外を確認。架空の社内方針の追加要件・優先順位を W3C が決めるわけではない。

## 歴史資料の保全確認と限界

`research/runtime_freeze_r3.json:43` が記録する旧 `research/holdout_manifest.json` と `research/seal_manifest.json` のハッシュは現物と一致した。旧上位 manifest が束縛する `research/datasets/heldout/manifest.json` のハッシュも一致した。

旧 dataset manifest の102パスは存在し、ファイル属性のサイズは全件 sizeBytes と一致。最も新しい記録対象ファイルの更新時刻は **2026-10-14T16:56:25.186Z** で、候補の createdAt **2026-10-15T05:47:00Z** より前だった。この範囲は作者の履歴保全申告と整合する。

ただし、これは既存マニフェストの不変と現在の属性の整合である。私有ファイル本体のハッシュは再計算しておらず、同じサイズ・更新時刻だけでは byte-for-byte 不変を証明できない。また過去の「一度も読んでいない」という行動は属性やハッシュだけでは証明できない。したがって **歴史 manifest の不変は確認、禁止ファイル本体の byte-for-byte 保全と作者の非閲覧履歴は未確認** とする。禁止内容を読んでこの限界を解消しようとはしなかった。

handover §6.3 は生成スクリプトの削除を記載しており、このレビューでは作者の生成・検証操作の完全な追試を行っていない。

## リリースへの条件

- F1の露出範囲を確定し、必要なら別版の隔離作問へ移る。現在の監査文脈からプロンプトや実装の調整を派生させない。
- 入力仕様、control の割当、出典の版・節・適用条件、引用抽出規則を修正・明記した候補を公開部分のみで再監査する。ISO と POSIX.1-2017 の未確認部分を Verified と扱わない。
- 承認された新しい事前登録では candidate manifest、分析用ID集合、protocol/spec、プロンプト・コード、公開資料、対応する実行 freeze の結び付きを明示する。現在の SHA-256 一致だけで release 承認へ読み替えない。
- `research/runtime_freeze_r3.json:59` のゲート、clean committed release、公的資料だけに制限する transport、過去を含む資源会計の監査は別の未完了条件として残る。本監査で実験実行は開始していない。

変更対象は本報告と `research/task-gate-runtime-state.json` のレビュー追記のみ。候補データ、ソースコード、既存 freeze は変更しない。ケース作成と240 trial study の利用者承認を撤回・変更するものではなく、この候補の受入可否を判定した。
