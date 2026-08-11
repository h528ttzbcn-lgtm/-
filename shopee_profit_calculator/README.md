# Shopee 利益計算ツール

商品名・仕入原価・想定販売価格を入力すると、Shopeeで出品した場合の**手数料込みの利益・利益率・損益分岐価格**を
一括計算するツールです。

## このツールの範囲

- ✅ 利益計算(手数料計算・利益率・損益分岐価格)の自動化
- ❌ Shopee上の他セラー商品を商品名で横断検索して価格収集する機能は含みません
  (Shopeeのマーケットプレイス検索結果のスクレイピングが必要になり利用規約に抵触するため未実装)

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

## 使い方

```bash
python -m shopee_profit_calculator.cli calc \
  --csv data/sample_products.csv \
  --fee-profile config/fee_profile.json
```

`output/profit_report_<timestamp>.csv` に、利益率が低い順に並んだ結果が出力されます。

出力項目:

- `commission_fee` / `transaction_fee` / `service_fee` / `fixed_fee`: 各種手数料の内訳
- `profit_per_unit` / `profit_total`: 1個あたり利益・出品数量ぶんの合計利益
- `margin_rate_pct`: 利益率(利益 ÷ 販売価格)
- `roi_pct`: 投資利益率(利益 ÷ 仕入原価)
- `break_even_price`: 損益分岐となる最低販売価格(これを下回ると赤字)
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
