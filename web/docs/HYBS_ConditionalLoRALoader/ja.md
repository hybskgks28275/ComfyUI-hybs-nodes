# Conditional LoRA Loader

選択した TOML の `[[lora]]` 定義について、`trigger` 正規表現が `positive` prompt に一致する LoRA をすべて適用します。一致した LoRA はファイル記載順に適用されます。

出力した `model` と `clip` を下流へ接続してください。変更済み CLIP を使うため、Text Encode はこのノードの後に配置します。

## 入力

- **model**, **clip**: 元になる MODEL と CLIP。
- **positive**: 各 `trigger` と照合する prompt。
- **config_toml**: `config/` に置いた TOML ファイル。

`[[lora]]` には `trigger`、`name`、`strength_model`、`strength_clip` を指定します。照合には Python の `re.search` を使用します。

## 設定

TOML ファイルを `config/` に置きます。`\\s` や `\\b` など、TOML 文字列内のバックスラッシュはエスケープしてください。

```toml
[[lora]]
trigger = "(?i)red\\s+dress"
name = "characters/wardrobe/red_dress_lora.safetensors"
strength_model = 1.0
strength_clip = 1.0
```

## 出力

- **model**, **clip**: 一致した LoRA をすべて適用した値。
- **applied loras**: `<lora:name:model_strength:clip_strength>` 形式の空白区切り文字列。
