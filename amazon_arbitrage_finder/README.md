# Amazon せどりリサーチツール(楽天市場・Yahoo!ショッピング → Amazon)

楽天市場とYahoo!ショッピング(ビックカメラ・ヤマダデンキ・Joshin・コジマなど家電量販店のストアを含む)で商品を検索し、
**Amazonで売ると利益が出る商品**を探すCLIツールです。見つかった商品は、
[`amazon_auto_listing`](../amazon_auto_listing) にそのまま渡せる出品用CSVとして出力します。

使うのは各社の**公式API**(楽天ウェブサービス、Yahoo!ショッピングAPI、Amazon SP-API)だけで、スクレイピングは行いません。

## 処理の流れ

```
検索条件CSV ─┬─ 楽天市場 商品検索API ─┐
             └─ Yahoo!ショッピングAPI ─┼─▶ JANで重複をまとめる(一番安い仕入れ先を残す)
手入力CSV(公式サイト等) ───────────────┘            │
                                                     ▼
            SP-API searchCatalogItems(20件ずつ)でJAN → ASIN を照合
                                                     ▼
          ランキング・除外ブランド → getItemOffers(カート価格・最安値)
                                                     ▼
          手数料前の利益で足切り → getMyFeesEstimate(手数料) → 利益・ROI判定
                                                     ▼
          getListingsRestrictions(出品制限チェック) → レポートCSV + 出品用CSV
```

時間のかかるAPI(getItemOffersは0.5回/秒)は、安い判定をすべて通過した商品にだけ使うよう順番を組んでいます。

## ⚠ 使う前に必ず読んでください

- **無在庫転売(他サイトで注文して購入者に直送)はAmazonの規約で禁止されています。** アカウント停止の典型的な原因です。
  このツールは「仕入れ候補を探す」ためのものです。**実際に購入して在庫を確保してから出品してください。**
  そのため出品用CSVの `quantity` は既定で `0` になっています。仕入れ後に数量を書き換えてから出品してください。
- 転売を目的として継続的に仕入れる場合、**古物商許可**が必要になることがあります(新品でも該当する場合があります)。
- 家電はメーカーの**出品規制・ブランド制限**が多いカテゴリです。`check_restrictions: true` で出品制限を事前に確認しますが、
  最終的な判断はSeller Centralで確認してください。真贋調査に備えて、**仕入れ先の納品書・領収書は必ず保管**してください。
- ヨドバシ.comなど**公開APIが無いサイトへのスクレイピングは、多くのサイトで利用規約により禁止されています。**
  そうしたサイトの商品は、後述の「手入力CSV」で取り込んでください。

## 新品として出品する場合

このツールは**新品の出品**を前提にしています(`condition_type: "new_new"`)。

### ツール側で自動的に行う処理

- Yahoo!ショッピングは `condition=new` を指定して**新品だけを検索**します。念のため、商品状態が `used` の結果も `中古` として除外します。
- 楽天市場のAPIには商品状態の項目がありません。そのため `exclude_title_keywords` に含まれる語
  (中古・展示品・開封品・未使用品・箱潰れ・アウトレット・リファービッシュ等)が商品名にあれば除外します。
  漏れが見つかったら設定ファイルに語を追加してください。
- Amazon側は**新品の出品**(`getItemOffers` の `New`)の価格で利益を計算し、出品制限も `new_new` で確認します。
- `condition_type` を `new_new` 以外にすると、実行時に警告が表示されます。

### 出品前に自分で確認すること

- Amazonの「新品」は、**メーカーの保証が有効で、元のパッケージのまま未開封**である必要があります。
  「未使用品」(個人から買った未開封品など)は新品として出品できないため、除外対象にしています。
- **家電はメーカー保証が重要です。** 仕入れ先が保証書に販売店印・購入日を記入する場合、購入者に保証が引き継がれるかを確認してください。
- 一部のメーカー・ブランドは、正規代理店以外からの新品出品を制限しています。`出品制限` で除外されなかった場合でも、
  Seller Centralの「出品制限の確認」で最終確認してください。
- 真贋調査や「新品なのに中古品が届いた」というクレームに備え、**仕入れ先の納品書・領収書は必ず保管**してください。

## セットアップ

```bash
cd amazon_arbitrage_finder
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
cp config/research_settings.example.json config/research_settings.json
```

### 楽天ウェブサービス

1. [楽天ウェブサービス](https://webservice.rakuten.co.jp/)でアプリを登録します。
2. **アプリID(`RAKUTEN_APPLICATION_ID`)とアクセスキー(`RAKUTEN_ACCESS_KEY`)の両方**を `.env` に設定します。
3. アプリ登録時に「許可されたWebサイト」として登録したURLを `RAKUTEN_REFERER` に設定します(Refererヘッダとして送信されます)。

> 楽天ウェブサービスは2026年に仕組みが刷新され、エンドポイントが `openapi.rakuten.co.jp` に変わり、アクセスキーが必須になりました。
> 旧 `app.rakuten.co.jp` 時代のアプリIDはそのままでは使えないため、再登録が必要です。
> APIバージョン(URL末尾の日付)が更新された場合は、`.env` の `RAKUTEN_ENDPOINT` を差し替えてください。

### Yahoo!ショッピング

[Yahoo!デベロッパーネットワーク](https://e.developer.yahoo.co.jp/)でアプリを登録し、Client IDを `YAHOO_CLIENT_ID` に設定します。
Yahoo!のAPIは **JANコードを直接返す**ため、Amazonとの照合精度が高くなります。

### Amazon SP-API

`amazon_auto_listing` と同じ認証情報を使えます(取得手順は [amazon_auto_listing/README.md](../amazon_auto_listing/README.md) を参照)。
アプリのロールには **Product Listing** と **Pricing** が必要です。

## 検索条件シート(`data/sample_queries.csv`)

| カラム | 必須 | 説明 |
|---|---|---|
| `source` | ○ | `rakuten` または `yahoo` |
| `keyword` | △ | 検索キーワード。yahooでは必須。rakutenでは `shop` を指定すれば空欄でも可(ショップの全商品が対象) |
| `shop` | - | 対象ストア。楽天は `shopCode`、Yahoo!は `seller_id` |
| `min_price` / `max_price` | - | 価格帯(税込・円) |
| `pages` | - | 取得するページ数(楽天は1ページ30件、Yahoo!は1ページ50件) |
| `sort` | - | 並び順。各APIの書式のまま指定(例: 楽天 `-reviewCount`、Yahoo! `-review_count`) |

### 家電量販店ストアの指定

`shop` 列に、各ストアURLの店舗コード部分を指定します。

| ストア | source | shop | URL |
|---|---|---|---|
| 楽天ビック(ビックカメラ) | rakuten | `biccamera` | https://biccamera.rakuten.co.jp/ |
| ヤマダデンキ Yahoo!店 | yahoo | `yamada-denki` | https://store.shopping.yahoo.co.jp/yamada-denki/ |
| Joshin web(Yahoo!) | yahoo | `joshin` | https://store.shopping.yahoo.co.jp/joshin/ |
| コジマYahoo!店 | yahoo | `y-kojima` | https://store.shopping.yahoo.co.jp/y-kojima/ |

上の表にないストアは、次の場所を見て店舗コードを確認してください。

- 楽天:ストアのURL `https://www.rakuten.co.jp/<店舗コード>/`、または商品URL `https://item.rakuten.co.jp/<店舗コード>/...`
- Yahoo!:`https://store.shopping.yahoo.co.jp/<店舗コード>/`

店舗コードは変わる可能性があるため、使う前に一度ブラウザで開いて確認してください。

## 手入力の仕入れ商品シート(`data/sample_manual_items.csv`)

APIが無いサイト(家電量販店の自社ECサイトやチラシ価格など)で見つけた商品を取り込みます。

| カラム | 必須 | 説明 |
|---|---|---|
| `jan` | ○ | 13桁のJANコード(チェックディジットも検証します) |
| `price` | ○ | 仕入れ価格(税込) |
| `title` / `shop_name` / `url` | - | レポートに表示するための情報 |
| `shipping_cost` | - | 送料(空欄は0) |
| `points` | - | 付与ポイント数 |

## 使い方

```bash
# 1. まずAmazon照合なしで、仕入れ先の検索がうまく動くか・JANが取れているかを確認
python -m amazon_arbitrage_finder.cli research --queries data/sample_queries.csv --skip-amazon

# 2. Amazonと照合して利益計算(楽天/Yahoo!の検索結果 + 手入力CSV)
python -m amazon_arbitrage_finder.cli research \
    --queries data/sample_queries.csv \
    --manual-items data/sample_manual_items.csv \
    --settings config/research_settings.json

# 3. 出力された出品用CSVを確認し、実際に仕入れてから quantity を設定して出品
cd ../amazon_auto_listing
python -m amazon_auto_listing.cli list --csv ../amazon_arbitrage_finder/output/listing_candidates_<日時>.csv --dry-run
```

### 出力ファイル

- `output/research_report_<日時>.csv`:すべての商品の判定結果です。`status` が `OK` の行が先頭に、利益の大きい順で並びます。
  それ以外の行も `status` と `reasons` に除外理由(`JANなし` / `Amazonなし` / `利益不足` / `出品制限` など)が残ります。
- `output/listing_candidates_<日時>.csv`:`OK` の商品だけを `amazon_auto_listing` の入力形式で出力したものです。

## 利益計算

```
仕入れコスト = 仕入れ価格 + 送料 − ポイント × point_value_rate + 納品送料 + 梱包費 + その他
利益         = Amazon販売想定価格 − Amazon手数料(SP-APIの見積もり) − 仕入れコスト
ROI          = 利益 ÷ 仕入れコスト
```

- **Amazon販売想定価格**:`price_basis` に応じてカート価格(`buybox`)または新品最安値(`lowest`)を使い、そこから `undercut_yen` 円を引いた額です。
- **楽天のポイント**:APIの `pointRate`(倍率)から「税抜価格 × 倍率 × 1%」で計算します。SPUやキャンペーンなど、
  自分に付く追加ポイントは `extra_point_rate`(仕入れ価格に対する率)で指定します。
- **Yahoo!のポイント**:APIが返すストア付与ポイント数を使います。PayPayのキャンペーン分などは `extra_point_rate` で指定します。
- **送料**:楽天の「送料別」、Yahoo!の「送料設定なし/条件付き送料無料」は金額が分からないため、`unknown_shipping_cost` を仮定します。

### 設定(`config/research_settings.example.json`)

| キー | 説明 |
|---|---|
| `price_basis` / `undercut_yen` | 販売価格の基準(`buybox`/`lowest`)と、そこから下げる額 |
| `is_fba` | 手数料見積もりをFBA前提にするか |
| `point_value_rate` / `extra_point_rate` | ポイントの円換算率 / 追加で付くポイントの率 |
| `unknown_shipping_cost` | 送料が不明なときに仮定する送料 |
| `inbound_shipping_per_unit` / `packaging_per_unit` / `other_cost_per_unit` | 1個あたりの追加コスト |
| `min_profit` / `min_roi` | 最低利益(円) / 最低ROI(小数) |
| `max_sales_rank` / `max_offer_count` | ランキングの上限 / 出品者数の上限(0で無効) |
| `exclude_brands` / `exclude_title_keywords` | 除外するブランド / 仕入れ先の商品名に含まれていたら除外する語 |
| `check_restrictions` | 出品制限を確認するか |
| `sku_prefix` / `listing_quantity` / `condition_type` / `fulfillment_channel` | 出品用CSVに入れる値 |

## 制限事項・注意

- 楽天の商品検索APIには**JAN専用の項目がありません**。そのため商品名・商品説明から抽出しています。
  「JAN」の表記がある、または13桁のコードが1つだけある場合にのみ採用し、判断できない場合は `JANなし` として除外します
  (誤ったJANで照合するよりも安全なためです)。
- 1つのJANに複数のASINが見つかった場合(セット品など)は、ASINごとに評価し、`reasons` に「数量・セット内容を要確認」と記録します。
- 手数料はSP-APIの見積もりです。実際の手数料は商品サイズの登録状況などで変わることがあります。
- Amazonで売れる速さは、ランキング(`max_sales_rank`)でしか判断していません。価格推移などは
  Keepaなどで別途確認することをおすすめします。

## テスト

```bash
pytest
```
