# ComfyUI-hybs-nodes 移行計画書

## 目的
- ComfyUI 最新系での **V3 Schema** と **Nodes 2.0 (Vue Node UI)** 互換を確保する。
- 既存ノードの挙動（入力・出力・カテゴリ・処理結果）を維持したまま、登録方式・メタ情報・JS UI 互換を強化する。

## 参照根拠
- `reference_v3/core/comfy_api_latest__io.py`
- `reference_v3/core/comfy_api_latest__init__.py`
- `reference_v3/rules/v1_to_v3_checklist.md`
- `reference_v3/rules/v1_to_v3_mapping.json`
- `reference_nodes2/core/object_info_contract.md`
- `reference_nodes2/core/migration_v1_to_v2.ts`
- `reference_nodes2/rules/nodes2_ui_checklist.md`
- `reference_js_nodes2/rules/js_nodes2_checklist.md`
- `reference_js_nodes2/core/compat_patterns.md`
- `reference_js_nodes2/core/js_nodes2_triage_workflow.md`

## 現状診断（2026-03-01）
- V3ベース (`ComfyNode`, `define_schema`, `comfy_entrypoint`) は導入済み。
- `comfy_api.latest` 固定 import で、推奨される `comfy_api` フォールバック未実装。
- Nodes 2.0 高影響項目（`display_name`, `description`, `category`）は概ね実装済み。
- Nodes 2.0 中影響項目（`search_aliases`, `essentials_category`）は未整備。
- JS 側は `inputEl` 依存や `LGraphCanvas.prototype` パッチは見当たらない。
- ただし `onDrawForeground` 依存更新があり、Vueノード環境での更新経路を再設計すべき。

## 対象
- Python:
  - `__init__.py`
  - `nodes/hybs_resolution_selector.py`
  - `nodes/hybs_random_resolution_selector.py`
  - `nodes/hybs_seed_list_generator.py`
  - `nodes/hybs_conditional_lora_loader.py`
  - `nodes/hybs_group_bypasser_nodes.py`
- JavaScript:
  - `web/js/hybs_group_bypasser_linked.js`
- 文書:
  - `README.md`（必要に応じて `README_ja.md` も）

---

## Phase 0: ベースライン固定
### 実施内容
- 現状ノード一覧、カテゴリ、入出力、既存ワークフローの挙動を記録する。
- GroupBypasser の UI 操作（トグル、カスケード、並び替え、サブグラフ）を確認する。

### 検証
- `/object_info` 取得結果を記録（比較用）。
- 主要ノードの出力同等性を記録。

### 完了条件
- 後続Phaseで回帰判定できる比較ベースが揃っている。

---

## Phase 1: V3スキーマ互換ハードニング
### 実施内容
- `comfy_api.latest` import 失敗時に `comfy_api` へフォールバック。
- フォールバック時に簡潔なログを出し、原因追跡可能にする。
- `comfy_entrypoint` / `ComfyExtension.get_node_list()` の登録経路を安定化。

### 検証
- `latest` が使える環境で起動成功。
- `latest` が使えない想定（フォールバック）でも import/登録成功。
- ノード欠落なし。

### 完了条件
- どちらの import 経路でも全ノードが読み込まれる。

---

## Phase 2: Nodes 2.0 メタ情報補完
### 実施内容
- 全 `Schema` に対し、必要なメタ情報を補完。
- 優先順位:
  1. 必須: `display_name`, `description`, `category`（再確認）
  2. 推奨: `search_aliases`, `essentials_category`
  3. 任意: `price_badge`, `is_api_node`（必要時のみ）
- 既存の入出力・処理ロジックは変更しない。

### 検証
- `/object_info` に補完内容が反映される。
- Nodes 2.0 上の検索・分類が改善される。

### 完了条件
- `nodes2_ui_checklist.md` の高影響は満たし、中影響も意図的に対応済み。

---

## Phase 3: JS Nodes 2.0 互換化（GroupBypasser）
### 実施内容
- `onDrawForeground` 依存の状態同期を最小化し、widget/state ベースに寄せる。
- `node.properties` は保存状態として扱い、表示更新経路を明示化。
- `document.body` overlay 利用は cleanup と再入防止を明確化。
- triage 観点を表で管理（pattern/risk/priority/difficulty/minimal_validation）。

### 検証（最小ケース）
- Vueノード表示でトグル状態が同期される。
- グループ追加・削除時にパネル再構築が破綻しない。
- カスケードON/OFFが親子グループに正しく反映される。
- モーダルが確実に閉じ、リークしない。

### 完了条件
- `js_nodes2_checklist.md` の高影響項目を満たす。

---

## Phase 4: 統合回帰とドキュメント反映
### 実施内容
- 4系統ノード（Resolution/Random/SeedList/ConditionalLoRA）の回帰確認。
- GroupBypasser の操作回帰確認。
- READMEに互換範囲と制限事項を明記。

### 検証
- 既存サンプルワークフローでエラーなし。
- 旧挙動との差分が仕様として説明可能。

### 完了条件
- リリース可能な状態（機能・UI・説明が一致）になっている。

---

## Phaseゲート運用ルール
- 各Phaseは `PASS / FAIL / BLOCKED` で判定。
- `FAIL/BLOCKED` は原因・影響・対処案を記録し、再試行後に次へ進む。
- ゲートを通過しない限り次Phaseに進まない。

## 実施順序（推奨）
1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4

## 変更ポリシー
- 入出力型・ノードID・カテゴリ・処理意味は維持。
- 互換性改善は「登録/メタ情報/UI同期」に限定し、仕様変更は行わない。
- 例外ケースや非対応事項は README に明記する。
