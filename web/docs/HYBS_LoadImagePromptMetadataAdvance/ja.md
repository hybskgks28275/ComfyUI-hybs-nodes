# Load Image Prompt Metadata Advance

画像を読み込み、元ワークフローの任意数のノード ID から prompt 文字列を取得します。

positive / negative 以外も再利用したい img2img / i2i ワークフロー向けです。ノード ID の入力欄は 1 つから始まり、入力に応じて増えます。空欄は無視され、最大 20 個まで指定できます。

ノード ID がない場合、メタデータがない場合、または指定 ID のいずれかから prompt を取得できない場合はエラーになります。

## 出力

- **IMAGE**: 読み込んだ画像。
- **prompt_1** から **prompt_20**: 指定 ID 順の prompt。未使用出力は空文字列。
