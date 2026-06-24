# Random Resolution Selector

`seed % 候補数` を使って `config/resolution_combos.json` から解像度を選びます。

同じ seed と設定では同じ結果になります。JSON は実行ごとに再読み込みされ、設定の変更は次回実行に反映されます。

## 入力

- **seed**: 解像度の選択に使う 0 以上の値。

## 出力

- **width**: 選択した幅。
- **height**: 選択した高さ。
