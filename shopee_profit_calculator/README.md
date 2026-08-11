# Shopee 利益計算ツール

商品名・仕入原価・想定販売価格を入力すると、Shopeeで出品した場合の**販売価格→手数料→送料→輸出還付金を
含めた利益・利益率・損益分岐価格**を一括計算し、さらに**目標利益率に対する推奨価格(値上げ/値下げ判定)**
まで出すツールです。

## このツールの範囲

- ✅ 利益計算(手数料・送料・輸出還付金込み)の自動化
- ✅ 目標利益率を満たす推奨価格の算出と、現在価格との比較による値上げ/値下げ判定
- ❌ Shopee上の他セラー商品を商品名で横断検索して価格収集する機能は含みません
  (Shopeeのマーケットプレイス検索結果のスクレイピングが必要になり利用規約に抵触するため未実装)
- ❌ 算出した推奨価格をShopeeに自動反映する機能は含みません(現状はレポート出力のみ。
  自動反映したい場合は `shopee_stock_watcher` と同様にOpen Platform APIの商品更新エンドポイントで
  拡張可能です)

**使い方の想定:** 仕入れ候補の商品について、原価と「いくらで売るつもりか」を自分で入力し、
実際に出品する前に採算が合うかを確認する電卓ツールです。

## 手数料について(重要)

Shopeeの販売手数料(コミッション率・決済手数料・サービス手数料など)は **国(ID/TH/VN/PH/MY/SG/TW/BR等)・
出品者プログラム・カテゴリーによって異なり、Shopee側の改定も頻繁** です。

そのため本ツールは実際の手数料率を一切ハードコードしていません。`config/fee_profile.example.json` を
コピーし、**ご自身のShopeeセラーセンター内の手数料ページで確認した実数値**を入力してから使ってください。
全ての率が0のまま実行すると警告が表示されます。

```bash
cp config/fee_profile.example.json config/fee_profile.json
# config/fee_profile.json を編集し、marketplace / currency / 各手数料率を実数値に置き換える
```

`config/fee_profile.sample_for_testing.json` は動作確認用のダミー数値であり、実際のShopee手数料では
ありません(コメントにもその旨を明記しています)。本番の利益判断には使わないでください。

## 輸出還付金について(重要)

`export_tax_refund` は、日本国内で仕入れた商品を輸出する際に還付される消費税相当額などを想定した項目です。
ただし適用可否・金額は**課税事業者かどうか・インボイス制度への対応・輸出許可通知書等の証憑の有無**などの
条件に依存し、本ツールでは一切判定しません。必ず税理士等の専門家に確認した金額を入力してください。
未確認の金額を入力すると、実際には得られない利益を見込んでしまうリスクがあります。

## セットアップ

```bash
cd shopee_profit_calculator
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## 入力シート形式 (`data/sample_products.csv` 参照)

| カラム | 必須 | 説明 |
|---|---|---|
| `product_name` | ○ | 商品名 |
| `cost_price` | ○ | 仕入原価(1個あたり) |
| `selling_price` | ○ | 想定Shopee販売価格 |
| `quantity` | - | 出品数量。既定値 1(利益総額の計算に使用) |
| `category` | - | カテゴリー名。`fee_profile.json` の `commission_rate_by_category` に一致すればその率を優先使用 |
| `shipping_cost` | - | 出品者負担分の送料。既定値 0 |
| `other_fixed_cost` | - | 梱包費・広告費按分など、その他固定費。既定値 0 |
| `export_tax_refund` | - | 輸出還付金など、販売に伴い戻ってくる金額(1個あたり)。既定値 0。要専門家確認 |
| `target_margin_rate` | - | この商品個別の目標利益率(0〜1の小数、例 0.2 = 20%)。空欄なら `fee_profile.json` の `default_target_margin_rate` を使用 |

## 使い方

```bash
python -m shopee_profit_calculator.cli calc \
  --csv data/sample_products.csv \
  --fee-profile config/fee_profile.json
```

価格の見直し判定の許容幅(推奨価格が現在価格の何%以内なら「維持」とするか)は既定2%で、
`--price-tolerance-pct 0.05` のように変更できます。

`output/profit_report_<timestamp>.csv` に、利益率が低い順に並んだ結果が出力されます。

出力項目:

- `commission_fee` / `transaction_fee` / `service_fee` / `fixed_fee`: 各種手数料の内訳
- `export_tax_refund`: 輸出還付金など(手入力)
- `profit_per_unit` / `profit_total`: 1個あたり利益・出品数量ぶんの合計利益
- `margin_rate_pct`: 利益率(利益 ÷ 販売価格)
- `roi_pct`: 投資利益率(利益 ÷ 仕入原価)
- `break_even_price`: 損益分岐となる最低販売価格(これを下回ると赤字)
- `target_margin_rate_pct`: 適用された目標利益率(行指定 or fee_profileの既定値)
- `recommended_price`: 目標利益率を満たすための推奨販売価格
- `price_diff`: 推奨価格 − 現在価格(プラスなら値上げ方向、マイナスなら値下げ方向)
- `price_action`: `値上げ推奨` / `値下げ推奨` / `維持` / `目標未設定` / `目標利益率が達成不可(手数料率が高すぎます)`
- `is_profitable`: 黒字なら True

## テスト

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

## 今後の拡張候補

- Shopee公式Open Platform APIと連携し、自社ショップの既存出品価格を自動取得して原価と突き合わせる
  (要 Partner ID / API Key。前回作成した `amazon_auto_listing` と同様の認証設定パターンを流用可能)
- 複数マーケットプレイス(TH/VN/PH等)向けに `fee_profile` を切り替えて一括比較
