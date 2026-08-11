# Amazon ASIN 自動出品ツール

既存のAmazonカタログASINに対して、あなたのSKU・価格・在庫数を **相乗り出品** するCLIツールです。
Amazon公式の **Selling Partner API (SP-API)** の Listings Items API のみを使用し、
スクレイピングや非公式アクセスは一切行いません。

## できること

- CSV/Excelシートに `sku, asin, price, quantity` などを並べて一括投入
- `--dry-run`(デフォルト)で、実際にAPIを呼ばずに送信予定のリクエスト内容を確認・検証
- カテゴリ(product_type)ごとの属性テンプレートをJSONでカスタマイズ可能
- レート制限対策の待機・リトライ(429/5xx時に指数バックオフ)
- 結果を `output/results_<timestamp>.csv` にレポート出力

## できないこと / 注意

- 新規ASIN(カタログにまだ存在しない商品)の新規作成には未対応です。あくまで既存ASINへの相乗り出品用です。
- Amazonはカテゴリ(product_type)ごとに必須属性が異なります。`templates/generic.json` は汎用的な最小構成であり、
  カテゴリによっては追加属性が必要でAPIにrejectされる場合があります。`inspect-schema` コマンドで実際のスキーマを
  確認し、`templates/<PRODUCT_TYPE>.json` として複製・拡張してください。
- 相乗り出品はAmazonの規約・ブランド許諾によっては制限される場合があります(ブランド登録商品、Amazon限定商品など)。

## セットアップ

```bash
cd amazon_auto_listing
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

`.env` にSP-API認証情報を設定してください(取得方法は次章)。

## SP-API 認証情報の取得手順

1. **Amazon Seller Central にログイン**し、対象マーケットプレイス(例: JP)の出品用アカウントを用意する。
2. Seller Central 右上メニュー → **[アプリを開発する] (Develop apps)** を開く。
   URL例: `https://sellercentral.amazon.co.jp/apps/manage`
3. 「新しいアプリを追加」から **自己承認アプリ(self-authorized app)** を作成する。
   - アプリ名は任意(例: `asin-auto-listing`)
   - 必要なロール(権限区分)として最低限 **Product Listing** を選択する
4. 作成すると **LWA Client ID (`LWA_APP_ID`)** と **LWA Client Secret (`LWA_CLIENT_SECRET`)** が発行されます。
5. アプリの詳細画面から「認証」を行い、自分のセラーアカウントに対する **Refresh Token (`SP_API_REFRESH_TOKEN`)** を取得します。
6. **Seller ID (`SP_API_SELLER_ID`)** は Seller Central → 設定 → アカウント情報 の「マーチャントトークン」欄で確認できます。
7. 2023年以降に作成した自己承認アプリは通常 AWS IAM ロール(`SP_API_ROLE_ARN` 等)が不要です。
   古い形式のアプリの場合のみ、AWS IAMユーザーを作成してSP-APIロールにアクセス許可を付与し、
   `SP_API_AWS_ACCESS_KEY` / `SP_API_AWS_SECRET_KEY` / `SP_API_ROLE_ARN` を設定してください。

参考: [Amazon SP-API公式ドキュメント - Register as a developer](https://developer-docs.amazon.com/sp-api/docs/registering-your-application)

## 入力シート形式 (`data/sample_listings.csv` 参照)

| カラム | 必須 | 説明 |
|---|---|---|
| `sku` | ○ | 自社の出品SKU(一意) |
| `asin` | ○ | 出品先の既存ASIN(10文字) |
| `price` | ○ | 販売価格(数値のみ) |
| `quantity` | ○ | 出品数量 |
| `condition_type` | - | 商品状態。既定値 `new_new`。中古は `used_like_new` 等 |
| `product_type` | - | Amazonカテゴリの product_type コード。既定値 `PRODUCT` |
| `currency` | - | 通貨コード。既定値 `JPY` |
| `fulfillment_channel` | - | `DEFAULT`(自己発送)など。既定値 `DEFAULT` |

`product_type` が分からない場合は以下で候補を取得できます:

```bash
python -m amazon_auto_listing.cli lookup-product-type --asin B0EXAMPLE1
```

## 使い方

### 1. まずドライランで内容確認(APIは呼ばれません)

```bash
python -m amazon_auto_listing.cli list --csv data/sample_listings.csv --dry-run
```

生成されるリクエストボディがログとレポートCSVに出力されるので、内容を確認してください。

### 2. 認証情報設定後、実行

```bash
python -m amazon_auto_listing.cli list --csv data/sample_listings.csv --no-dry-run
```

### 3. カテゴリ別の属性スキーマを確認してテンプレートを拡張

```bash
python -m amazon_auto_listing.cli inspect-schema --product-type LUGGAGE
```

出力されたJSON Schemaの必須項目を見ながら、`src/amazon_auto_listing/templates/LUGGAGE.json` を
`generic.json` をコピーして作成・編集してください(`$asin` `$price` 等のプレースホルダはそのまま使えます)。

## テスト

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

ネットワークアクセスやSP-API認証情報なしで、CSV読み込み・属性ビルド・実行ロジックを検証できます
(SP-APIクライアントはテスト内でモック化しています)。

## 開発方針・免責

- 本ツールはAmazon公式SP-APIのみを利用し、非公式スクレイピング等は行いません。
- レート制限・利用規約はAmazon側の仕様変更により変わる可能性があります。実運用前に必ず
  Sandboxやテストアカウントでの検証、公式ドキュメントの最新情報の確認を行ってください。
