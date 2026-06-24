# Resolution Selector

`config/resolution_combos.json` の解像度から 1 つを選び、`width` と `height` を出力します。

設定ファイルがない場合は内蔵の既定値を使用します。

## 入力

- **resolution**: `<width>x<height>` 形式の解像度。

## 出力

- **width**: 選択した幅。
- **height**: 選択した高さ。

## 設定

`config/resolution_combos.json` に、空ではない整数の幅・高さペア配列を指定します。

```json
[
  [1024, 1024],
  [1152, 896],
  [896, 1152]
]
```
