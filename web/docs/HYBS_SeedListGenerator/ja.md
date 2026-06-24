# Seed List Generator

`count` 個のランダムな 32-bit seed を LIST で生成します。1 回のリスト内で値は重複しません。

実行 fingerprint が毎回変わるため、キュー実行ごとに新しいリストを生成します。

## 入力

- **count**: 生成する seed 数。

## 出力

- **seed list**: 生成した seed 値。
- **count**: 生成した要素数。
