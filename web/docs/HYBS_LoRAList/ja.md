# LoRA List

`models/loras` から選択した LoRA ファイル名の LIST を作成します。

1 行目では未適用の比較用 baseline として `NONE` を選べ、出力時は `null` になります。**add lora** で行を増やします。2 行目以降で `NONE` を選ぶとその行は削除されます。複数 LoRA の比較では、strength 用リストを Double List などの別ノードで用意してください。

## 出力

- **lora names**: 行順の LoRA 名。先頭の `NONE` は `null`。
- **count**: baseline を含む要素数。
