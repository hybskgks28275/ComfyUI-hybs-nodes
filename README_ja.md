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
  - 生成されたリスト内で seed 値は重複しません。
  - キュー実行ごとに再実行され、新しいリストを生成します。

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

### Load LoRA

- カテゴリ: `HYBS/LoRA`
- 入力:
  - `model` (MODEL)
  - `clip` (CLIP)
  - `lora_name` (COMBO, 初期値 `NONE`)
  - `strength_model` (FLOAT, 初期値 `1.0`)
  - `strength_clip` (FLOAT, 初期値 `1.0`)
- 出力:
  - `model` (MODEL)
  - `clip` (CLIP)
  - `applied lora` (STRING)
- 動作:
  - `models/loras` フォルダの内容をプルダウンで選択します。
  - `NONE` が初期値で、LoRA 未適用を意味します。
  - `null`、空値、`NONE` の場合は入力 `model` / `clip` をそのまま返します。

### Diffusion Model List

- カテゴリ: `HYBS/Model`
- 入力:
  - `model` (COMBO, 自動追加)
- 出力:
  - `model names` (LIST)
  - `count` (INT)
- 動作:
  - `models/unet` フォルダの内容をプルダウンで選択します。
  - 最初は 1 つだけ表示され、モデルを選ぶごとに次の選択欄が追加されます。
  - 選択した UNet ファイル名を list で返します。
  - `count` は実際にモデル名が選択された項目だけを数えます。
  - `model names` は表示されているプルダウン順のまま返します。
  - ComfyLab の `XY Plot` では、ラベル用途に `model names` を使い、必要に応じて標準の diffusion model ノードと組み合わせてください。

### LoRA List

- カテゴリ: `HYBS/LoRA`
- 入力:
  - `lora 1`, `lora 2`, ... (COMBO, 自動追加)
- 出力:
  - `lora names` (LIST)
  - `count` (INT)
- 動作:
  - `models/loras` フォルダの内容をプルダウンで選択します。
  - 最初は 1 つだけ表示され、LoRA を選ぶごとに次の選択欄が追加されます。
  - `NONE` は 1 行目だけ選択可能です。未適用の baseline を比較に含めたい場合に使えます。
  - 初期値は `null` です。`NONE` を選ぶと `null` として返します。
  - LoRA ファイル名を表示行の順番で返します。

### Double List

- カテゴリ: `HYBS/List`
- 入力:
  - `value 1`, `value 2`, ... (FLOAT, 手動追加/削除)
- 出力:
  - `double list` (LIST)
  - `count` (INT)
- 動作:
  - 編集可能な小数値を list で返します。
  - 初期値は 1 つで、`1.0` です。
  - `LoRA List` と組み合わせて LoRA strength list を別ノードとして扱う場合などに使えます。

### Int List

- カテゴリ: `HYBS/List`
- 入力:
  - `value 1`, `value 2`, ... (INT, 手動追加/削除)
- 出力:
  - `int list` (LIST)
  - `count` (INT)
- 動作:
  - 編集可能な整数値を list で返します。
  - 初期値は 1 つで、`1` です。

### Load Image Prompt Metadata

- カテゴリ: `HYBS/LoadImage`
- 入力:
  - `image` (COMBO/upload): ComfyUI の input フォルダ内の画像
  - `positive_node_id` (STRING): positive prompt として読むノード ID
  - `negative_node_id` (STRING): negative prompt として読むノード ID
- 出力:
  - `IMAGE`
  - `positive` (STRING)
  - `negative` (STRING)
- 動作:
  - 選択した画像を Load Image ノード相当で読み込みます。
  - 画像内に ComfyUI workflow メタデータがある場合に読み取ります。
  - img2img / i2i などで、元画像に埋め込まれたプロンプトを再利用したい場合に使えます。
  - `id` が一致するノードを探し、そのノードの `widgets_values` 内で最初に見つかった文字列を返します。
  - 実行用の `prompt` メタデータ形式もノード ID で読み、`inputs.text` がある場合はそれを返します。
  - ノード ID は意図的に空欄がデフォルトです。元ワークフロー上の positive/negative prompt ノード ID を入力してください。
  - `82:78` のようなサブグラフ ID にも対応します。
  - workflow/prompt メタデータがない場合や、指定 ID からプロンプト文字列を取得できない場合はエラーになります。
- サンプル:
  - `workflow/LoadImagePromptMetadata.json` を開いてください。
  - サンプル元画像として `workflow/LoadImageSample.png` を使用します。
  - サンプル画像には、ノード ID で読み取れるプロンプトメタデータが埋め込まれています。

### Load Image Prompt Metadata Advance

- カテゴリ: `HYBS/LoadImage`
- 入力:
  - `image` (COMBO/upload): ComfyUI の input フォルダ内の画像
  - `node id 1`, `node id 2`, ...: 取得したいプロンプトのノード ID。初期は 1 行で、入力すると追加できます。
- 出力:
  - `IMAGE`
  - `prompt_1`, `prompt_2`, ... (STRING): ノード ID 行に合わせて増える個別プロンプト出力
- 動作:
  - img2img / i2i で、元画像メタデータから positive/negative 以外も含めて複数のプロンプトを読みたい場合に使えます。
  - 各ノード ID は `Load Image Prompt Metadata` と同じ方法で解決します。
  - 空欄行は無視され、次のノード ID を追加するための空欄と `prompt_#` 出力が末尾に 1 つ残ります。
  - 最大 20 個のプロンプトノード ID を指定できます。
  - ノード ID が 1 つもない場合、メタデータがない場合、または指定 ID のいずれかからプロンプト文字列を取得できない場合はエラーになります。

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

以下のいずれかの方法でインストールしてください。

### 方法1: ComfyUI Manager（Registry）

1. ComfyUI Manager を開きます。
2. Custom Nodes Manager で `ComfyUI-hybs-nodes` を検索します。
3. インストールします。
4. ComfyUI を再起動します。

### 方法2: 手動インストール

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
