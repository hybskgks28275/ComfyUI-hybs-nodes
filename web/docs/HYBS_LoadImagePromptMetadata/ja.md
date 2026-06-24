# Load Image Prompt Metadata

Load Image 相当の画像読み込みを行い、埋め込まれた ComfyUI の `workflow` または `prompt` メタデータから positive / negative prompt を取得します。

元画像の prompt を再利用する img2img / i2i ワークフロー用のノードです。**positive_node_id** と **negative_node_id** に元ワークフローのノード ID を入力します。初期値は空欄で、`82:78` のようなサブグラフ ID にも対応します。

メタデータがない場合、または指定 ID から prompt を取得できない場合はエラーになります。`workflow/LoadImagePromptMetadata.json` と `workflow/LoadImageSample.png` をサンプルとして参照してください。

## 出力

- **IMAGE**: 読み込んだ画像。
- **positive**, **negative**: 指定したノード ID の prompt 文字列。
