# Load LoRA

`models/loras` から 1 つ選んだ LoRA を MODEL と CLIP に適用します。

`NONE`、`null`、空の値は未適用として扱われ、入力の model と clip をそのまま返します。LoRA 適用あり・なしを比較する用途に使えます。

## 入力

- **model**, **clip**: 変更する MODEL と CLIP。
- **lora_name**: LoRA ファイル名。初期値は `NONE`。
- **strength_model**: MODEL 用の LoRA strength。
- **strength_clip**: CLIP 用の LoRA strength。

## 出力

- **model**, **clip**: 適用後の値。`NONE` では入力値。
- **applied lora**: 適用 LoRA のトークン。`NONE` では空文字列。
