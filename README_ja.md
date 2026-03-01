# ComfyUI-hybs-nodes（日本語）

ComfyUI 向けのカスタムノード集です。解像度ユーティリティ、条件付き LoRA 適用、グループバイパス制御を提供します。

## 互換性

- バックエンド: V3 スキーマ対応（`ComfyNode`, `Schema`, `ComfyExtension`, `comfy_entrypoint`）
- フロントエンド: Nodes 2.0 メタ情報対応（`display_name`, `description`, `category`, `search_aliases`, `essentials_category`）
- API import フォールバック: `comfy_api.latest` -> `comfy_api`

## ノード一覧

### Resolution Selector

- カテゴリ: `HYBS/ResolutionSelector`
- 入力:
  - `resolution` (COMBO): `"<width>x<height>"`
- 出力:
  - `width` (INT)
  - `height` (INT)
- 動作:
  - `config/resolution_combos.json` から候補を読み込み（ファイルなし時は内蔵デフォルト）。
  - 選択された解像度の width/height を返します。

### Random Resolution Selector

- カテゴリ: `HYBS/ResolutionSelector`
- 入力:
  - `seed` (INT)
- 出力:
  - `width` (INT)
  - `height` (INT)
- 動作:
  - 実行ごとに `config/resolution_combos.json` を再読み込み。
  - `seed % len(combos)` で解像度を選択。
  - Fingerprint に設定ファイルの mtime を含むため、ファイル更新で再実行されます。

### Seed List Generator

- カテゴリ: `HYBS/SeedGenerator`
- 入力:
  - `count` (INT)
- 出力:
  - `seed list` (LIST)
  - `count` (INT)
- 動作:
  - `count` 個の 32bit 乱数シードを生成します。

### Conditional LoRA Loader

- カテゴリ: `HYBS/ConditionalLoRALoader`
- 入力:
  - `model` (MODEL)
  - `clip` (CLIP)
  - `positive` (STRING, 複数行, `forceInput=True`)
  - `config_toml` (COMBO, `config/*.toml` から選択)
- 出力:
  - `model` (MODEL)
  - `clip` (CLIP)
  - `applied loras` (STRING)
- 動作:
  - 実行時に選択した TOML を読み込みます。
  - 条件一致した `[[lora]]` を上から順にすべて適用します。
  - LoRA ローダーは次の順でフォールバック:
    1. `comfy.sd.load_lora`
    2. 組み込み `nodes.LoraLoader`
    3. 低レベル fallback（`comfy.utils`）
- 配線の注意:
  - LoRA 適用後の `model`/`clip` を下流へ接続してください。
  - Text Encode は LoRA 適用後に実行してください。

### Group Bypasser

以下 3 ノードのカテゴリは共通で `HYBS/GroupBypasser` です。

#### Group Bypasser (Panel)

- 入力: なし
- 出力: なし
- 動作:
  - メイングラフとサブグラフのグループを一覧表示。
  - パネルからグループの bypass を切り替え可能。
  - 並び順を `auto` / `custom` で管理し、ドラッグ編集も可能。
  - Parent マーカーがあるグループは Child 接続先へカスケード切り替え可能。

#### Group Bypass Parent

- 入力: なし
- 出力:
  - `to_children` (ANY)
- 動作:
  - カスケード元を示すマーカーノード。
  - バックエンド処理は no-op。

#### Group Bypass Child

- 入力:
  - `from_parent` (ANY)
- 出力:
  - `to_children` (ANY)
- 動作:
  - カスケード先を示すマーカーノード。
  - Child 同士の連結による多段カスケードに対応。
  - バックエンドは入力をそのまま通します。

## 設定ファイル

### `config/resolution_combos.json`

空でない整数ペア配列で指定します。

```json
[
  [1024, 1024],
  [1152, 896],
  [896, 1152]
]
```

### Conditional LoRA 用 `config/*.toml`

```toml
[[lora]]
trigger = "(?i)red\\s+dress"
name = "characters/wardrobe/red_dress_lora.safetensors"
strength_model = 1.0
strength_clip  = 1.0
```

メモ:
- マッチは Python `re.search` で評価されます。
- TOML ではバックスラッシュをエスケープしてください（`\\s`, `\\b` など）。

## インストール

1. `ComfyUI/custom_nodes/` にクローン:

```bash
cd path/to/ComfyUI/custom_nodes
git clone https://github.com/hybskgks28275/ComfyUI-hybs-nodes.git
```

2. Python 依存をインストール:
   - `pip install -r requirements.txt`

3. ComfyUI を再起動。

## ライセンス

MIT。詳細は [LICENSE](LICENSE) を参照してください。
