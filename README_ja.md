# ComfyUI-hybs-nodes（日本語）

本リポジトリは、ComfyUI 用のカスタムノード群を提供します。

## ノード一覧

### Resolution Selector

ドロップダウンで解像度を手動選択できるノードです。`config/resolution_combos.json`（またはデフォルト一覧）から選択肢を読み込みます。

* **カテゴリ**: `HYBS/ResolutionSelector`
* **入力**

  * `resolution` (コンボ): `"<width>x<height>"` 形式の文字列
* **出力**

  * `width` (INT)
  * `height` (INT)
* **動作**

  1. 起動時に `config/resolution_combos.json` を読み込み（無い/不正な場合はデフォルトにフォールバック）
  2. `"WxH"` 形式の選択肢をドロップダウンに表示
  3. 予期しない形式が選ばれた場合はランタイムエラーを投げます

---

### Random Resolution Selector

シードに基づいて解像度 `(width, height)` を決定するノードです。**各実行時に** `config/resolution_combos.json` を再読込するため、JSON を保存すれば次実行から即反映されます。

* **カテゴリ**: `HYBS/ResolutionSelector`
* **入力**

  * `seed` (INT): 同じシードは同じ解像度になります
* **出力**

  * `width` (INT)
  * `height` (INT)
* **動作**

  1. 実行毎に `config/resolution_combos.json` を読み込み（無い場合はデフォルトにフォールバック）
  2. JSON が存在して不正な形式の場合は ValueError
  3. `seed % len(combos)` でインデックスを決定

---

### SeedListGenerator

乱数シードのリストを生成します。

* **カテゴリ**: `HYBS/SeedGenerator`
* **入力**

  * `count` (INT): 生成するシード数
* **出力**

  * `seed list` (LIST)
  * `count` (INT)

---

### Conditional LoRA Loader

**positive プロンプト**に対する正規表現マッチで条件分岐し、外部 TOML ファイルに定義された 1 個以上の LoRA を**一致した順にすべて適用**するノードです。

* **カテゴリ**: `HYBS/ConditionalLoRALoader`
* **入力**

  * `model` (MODEL)
  * `clip` (CLIP)
  * `positive` (STRING): `forceInput=True`, 複数行可。必ず**他ノードから入力**してください。
  * `config_toml` (コンボ): `config/` 内の `.toml` を選択
* **出力**

  * `model` (MODEL)
  * `clip`  (CLIP)
  * `applied loras` (STRING)
* **動作**

  1. 実行毎に `config/` から選択された TOML を読み込みます。さらに `IS_CHANGED` が **TOML の更新時刻（mtime）** を監視するため、TOML を保存すれば**次の実行から反映**されます。
  2. 各 `[[lora]]` の `trigger`（Python 互換の正規表現）が **positive** に `re.search` で一致すれば、その LoRA を適用。
  3. 複数一致した場合は**上から順にすべて適用**。
  4. ロードは `comfy.sd.load_lora → nodes.LoraLoader → 低レベルフォールバック` の順で試行。ログには `matched=...` / `Applied LoRA: ...` / エラーが出力されます。
* **配線の注意**

  * **LoRA 適用済みの `clip`** を **CLIP Text Encode** に接続してからテキストエンコードを行ってください。順番が逆だと LoRA が調整に反映されません。

## 設定ファイル

### 解像度リスト（`resolution_combos.json`）

拡張のルート（`nodes/` と同じ階層）の `config/resolution_combos.json` に配置します。内容は**空でない**整数ペア配列である必要があります。

```json
[
  [1024, 1024],
  [1088, 1088],
  [1152, 1152],
  [896, 1152],
  [832, 1216]
]
```

* ファイルが無い場合は、ビルトインのデフォルト一覧（1024–2048 の正方形と代表的な縦横比）を使用します。
* 存在しても形式が不正（空配列や型不一致）の場合はエラーになります。

### Conditional LoRA ルール（TOML）

`custom_nodes/ComfyUI-hybs-nodes/config/*.toml` に配置します。各ファイルは `[[lora]]` 配列でルールを記述します：

* `trigger`: **Python 互換の正規表現**。incoming **positive** に対して `re.search` で評価します。
* `name`: `loras/` からの**相対パス**（サブフォルダ可、拡張子必須）
* `strength_model`, `strength_clip`: LoRA の重み（省略時は `1.0`）
* 複数の `[[lora]]` が一致した場合は**すべて適用**（上から順）

**サンプル（`config/sample.toml`）**

```toml
# Each [[lora]] entry is evaluated against the *positive* prompt using a Python-style regex.
# If multiple entries match, they are applied in order (top to bottom).
# `name` is a path relative to your `loras/` directory.

# Example 1: phrase “red dress” (case-insensitive), allowing one or more spaces
[[lora]]
trigger = "(?i)red\\s+dress"
name = "characters/wardrobe/red_dress_lora.safetensors"
strength_model = 1.0
strength_clip  = 1.0

# Example 2: either “nurse” or “white coat” (case-insensitive)
[[lora]]
trigger = "(?i)(nurse|white\\s*coat)"
name = "characters/nurse/nurse_v5.safetensors"
strength_model = 0.8
strength_clip  = 0.8

# Example 3: whole word “wizard” (case-insensitive)
[[lora]]
trigger = "(?i)\\bwizard\\b"
name = "styles/fantasy/wizard_style_v2.safetensors"
strength_model = 0.7
strength_clip  = 0.7

# Example 4: “short hair” but not “short hair cut” (case-insensitive, negative lookahead)
[[lora]]
trigger = "(?i)short\\s+hair(?!\\s*cut)"
name = "attributes/hair/short_hair_v1.safetensors"
strength_model = 0.6
strength_clip  = 0.6
```

**メモ**

* 大文字小文字を無視したいときは、パターンの先頭にインラインフラグ `(?i)` を追加してください。
* TOML 文字列ではバックスラッシュがエスケープされるため、`\s` や `\b` は `\\s` / `\\b` と記述します。
* ルーティングでは **LoRA 適用後の `clip`** を Text Encode に渡してください。

#### Group Bypasser (Panel)

グループのバイパス状態を制御するパネルノードです。

* **カテゴリ**: `HYBS/ConditionalLoRALoader`
* **入力**:  

  *(なし)*
* **出力**:  

  *(なし)*
* **動作**:

  1. 現在のワークフロー内に存在するすべてのグループを一覧表示します。
  2. 各グループごとに ON/OFF トグルで bypass を切り替えできます。
  3. グループ内に **Group Bypass Parent** ノードが存在する場合、そのグループを切り替えると:
     - 親グループ自身を切り替え
     - Parent ノードから接続された **Group Bypass Child** ノードを探索
     - Child ノードを含むすべてのグループも同時に切り替えます
  4. Parent マーカーを含むグループはパネル上で `(cascade)` と表示されます。
  5. グループの表示順を変更できます:
     - `order mode = auto`: ワークフローのデフォルト順
     - `order mode = custom`: `order titles` に指定した順序を使用
  6. `edit order` ボタンでドラッグ＆ドロップによる並び替えダイアログを開きます。

---

#### Group Bypass Parent

カスケードの起点となるマーカーノードです。

* **カテゴリ**: `HYBS/ConditionalLoRALoader`
* **入力**:  

  *(なし)*
* **出力**:

  * `to_children` (ANY)
* **動作**:

  1. カスケードのルート（起点）として機能します。
  2. パネルからこのノードを含むグループを切り替えると、接続された Child グループも同時に切り替わります。
  3. 出力を1つ以上の **Group Bypass Child** ノードへ接続してください。
  4. このノード自身にはトグル機能はありません。切り替えはすべて Panel ノードから行います。

---

#### Group Bypass Child

カスケード対象となるグループを示すマーカーノードです。

* **カテゴリ**: `HYBS/ConditionalLoRALoader`
* **入力**:

  * `from_parent` (ANY)
* **出力**:

  * `to_children` (ANY)
* **動作**:

  1. **Group Bypass Parent** ノードからの接続を受け取ります。
  2. 親グループがパネルから切り替えられた際、このノードを含むグループも同時に切り替わります。
  3. Child ノード同士を接続することで、複数段階のカスケード構造を構築できます。

---

**使用例**

1. カスケードの起点にしたいグループ内に **Group Bypass Parent** ノードを配置します。
2. 連動させたい他のグループ内に **Group Bypass Child** ノードを配置します。
3. Parent ノードの出力を Child ノードの入力へ接続します。
4. ワークフロー内の任意の位置に **Group Bypasser (Panel)** ノードを追加します。
5. Panel から親グループを ON/OFF すると、接続されたすべてのグループが同時に切り替わります。

---

**メモ**

* バイパスは各ノードの execution mode を変更することで実現しています。
* グループIDには依存せず、ノード接続関係を動的に解析してカスケードを判定します。
* Parent / Child ノードはフロントエンド制御用のマーカーであり、バックエンドの処理結果には影響しません。

## インストール

1. ComfyUI の `custom_nodes/` フォルダへクローン

   ```bash
   cd path/to/ComfyUI/extensions
   git clone https://github.com/hybskgks28275/ComfyUI-hybs-nodes.git
   ```

2. ディレクトリ構成の確認

   ```text
   ComfyUI/
   └── custom_nodes/
       └── ComfyUI-hybs-nodes/
           ├── config/
           │   ├── lora_condition.toml.example
           │   └── resolution_combos.json.example
           ├── nodes/
           │   ├── hybs_conditional_lora_loader.py
           │   ├── hybs_group_bypasser_nodes.py
           │   ├── hybs_random_resolution_selector.py
           │   ├── hybs_resolution_selector.py
           │   └── hybs_seed_list_generator.py
           ├── web/
           │   └── js/
           |       └── hybs_group_bypasser_linked.js
           ├── workflow
           |   ├── Conditional_LoRA.json
           |   └── sample_conditional.toml
           ├── hybs_resolution_common.py
           ├── LICENSE
           ├── __init__.py
           ├── pyproject.toml
           ├── README_ja.md
           └── README.md
   ```

3. ComfyUI を再起動

   * `HYBS/ResolutionSelector` 配下に **Resolution Selector**, **Random Resolution Selector**
   * `HYBS/ConditionalLoRALoader` 配下に **Conditional LoRA Loader** が表示されます

## ライセンス

MIT License. 詳細は [LICENSE](LICENSE) を参照してください。
