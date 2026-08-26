# Amazon 売れ筋データ化ツール (SP-API + 任意でKeepa連携)

指定したASINの**現在のランキング・価格**をAmazon公式 **Selling Partner API (SP-API)** で取得し、
実行するたびに履歴を蓄積することで、Keepaのような「価格・売れ筋ランキングの推移」データを
一覧CSVとして手元に作るツールです。

## できること

- CSV/Excelで管理するASINウォッチリストを一括チェック
- Catalog Items API でタイトル・ブランド・カテゴリ内ランキング・画像URLを取得
- Product Pricing API で現在の最安価格(送料込み)を取得
- 実行のたびに `history/snapshot_log.jsonl` に追記し、**前回チェック時からの
  ランキング変動・価格変動(delta)**を一覧CSVに出力
- 任意で `KEEPA_API_KEY` を設定すると、Keepa APIから過去N日間の平均価格・
  平均ランキングも取得して一覧に追加(Keepaは公式の有料データサービスであり、
  非公式スクレイピングではありません)
- `--dry-run`(デフォルト)で、実際にAPIを呼ばずに前回までの履歴だけ確認可能

## できないこと / 注意(重要)

- **Amazonの「売れ筋ランキング(Best Sellers)」ページ自体を自動取得する機能はありません。**
  SP-APIにもPA-API(Product Advertising API)にも、カテゴリのTOP N商品一覧を返す
  公式エンドポイントは現在存在しないため、非公式スクレイピングをしない限り実現できません。
  本ツールは代わりに、**あなたが指定したASINそれぞれ**について現在のランキング・価格を
  取得する方式です(売れ筋ページを見て気になった商品のASINをウォッチリストに追加する運用を想定)。
- 過去の価格・ランキングの推移(Keepaのグラフのようなもの)は、Amazon公式APIからは
  取得できません。本ツールを**定期的に実行し続けることで**、`history/` 以下に自分自身の
  履歴として蓄積されます。今すぐ過去半年分のグラフが欲しい場合は、Keepa連携
  (`KEEPA_API_KEY`)を使ってください(Keepa自身が長期間クロールした履歴を持っています)。
- 本ツールはAmazon公式SP-APIとKeepa公式APIのみを利用し、非公式スクレイピングは一切行いません。

## セットアップ

```bash
cd amazon_bestseller_tracker
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

`.env` にSP-API認証情報を設定してください(取得方法は次章)。Keepa連携を使う場合は
`pip install -e ".[keepa]"` で `keepa` パッケージも入れ、`KEEPA_API_KEY` を設定してください。

## SP-API 認証情報の取得手順

1. **Amazon Seller Central にログイン**し、対象マーケットプレイス(例: JP)のアカウントを用意する。
2. Seller Central 右上メニュー → **[アプリを開発する] (Develop apps)** を開く。
   URL例: `https://sellercentral.amazon.co.jp/apps/manage`
3. 「新しいアプリを追加」から **自己承認アプリ(self-authorized app)** を作成する。
   - アプリ名は任意(例: `bestseller-tracker`)
   - 必要なロールとして最低限 **Product Listing**(カタログ参照権限を含む)を選択する
4. 作成すると **LWA Client ID (`LWA_APP_ID`)** と **LWA Client Secret (`LWA_CLIENT_SECRET`)** が発行されます。
5. アプリの詳細画面から「認証」を行い、自分のセラーアカウントに対する **Refresh Token (`SP_API_REFRESH_TOKEN`)** を取得します。
6. 2023年以降に作成した自己承認アプリは通常 AWS IAM ロールは不要です。
   古い形式のアプリの場合のみ `SP_API_AWS_ACCESS_KEY` / `SP_API_AWS_SECRET_KEY` / `SP_API_ROLE_ARN` を設定してください。
7. 本ツールが使うCatalog Items / Product Pricing APIの読み取りには `SP_API_SELLER_ID` は
   不要です(`amazon_auto_listing` の出品APIとは異なります)。

参考: [Amazon SP-API公式ドキュメント - Register as a developer](https://developer-docs.amazon.com/sp-api/docs/registering-your-application)

## Keepa API キーの取得(任意)

過去の推移データも一覧に含めたい場合のみ設定してください。

1. [Keepa](https://keepa.com/) でアカウントを作成し、API利用プラン(有料)に加入する。
2. アカウント設定からAPIキーを取得し、`.env` の `KEEPA_API_KEY` に設定する。
3. `KEEPA_DOMAIN` はマーケットプレイス(例: `JP`, `US`)。

## ウォッチリスト形式 (`data/sample_watchlist.csv` 参照)

| カラム | 必須 | 説明 |
|---|---|---|
| `asin` | ○ | 追跡したいASIN(10文字) |
| `memo` | - | 自分用メモ(商品名など、API送信には使いません) |
| `category_hint` | - | 自分用メモ(どのカテゴリのランキングを見たいか。APIの絞り込みには使いません) |

## 使い方

### 1. まずドライランで確認(APIは呼ばれません)

```bash
python -m amazon_bestseller_tracker.cli snapshot --csv data/sample_watchlist.csv --dry-run
```

### 2. 認証情報設定後、実際にランキング・価格を取得

```bash
python -m amazon_bestseller_tracker.cli snapshot --csv data/sample_watchlist.csv --no-dry-run
```

`output/bestseller_data_<timestamp>.csv` に一覧が出力されます。
主なカラム: `asin, title, brand, category, current_rank, previous_rank, rank_delta,
current_price, previous_price, price_delta, currency, keepa_avg_price, keepa_avg_rank`

同時に `history/snapshot_log.jsonl` に今回の結果が追記されます。次回以降の実行では
この履歴と比較して `rank_delta` / `price_delta` が埋まります。

### 3. 定期実行して推移データを蓄積する

cron等で1日1回実行すると、`history/snapshot_log.jsonl` に日次のランキング・価格の
記録が溜まっていきます(自分専用の簡易Keepa)。

```bash
0 9 * * * cd /path/to/amazon_bestseller_tracker && .venv/bin/python -m amazon_bestseller_tracker.cli snapshot --csv data/watchlist.csv --no-dry-run
```

### 4. 単発でASINを確認したいだけの場合

```bash
python -m amazon_bestseller_tracker.cli lookup --asin B0EXAMPLE1
```

## テスト

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

ネットワークアクセスやSP-API/Keepa認証情報なしで、CSV読み込み・履歴の蓄積/差分計算・
レスポンス解析ロジック・実行フローを検証できます(SP-API/Keepaクライアントはテスト内で
モック化しています)。

## 開発方針・免責

- 本ツールはAmazon公式SP-APIとKeepa公式APIのみを利用し、非公式スクレイピング等は行いません。
- SP-API/Keepa APIともレート制限・利用規約は変更される可能性があります。実運用前に必ず
  公式ドキュメントの最新情報を確認してください。
- 取得したランキング・価格情報の転用(再配布・再販売等)は、それぞれの利用規約に従ってください。
