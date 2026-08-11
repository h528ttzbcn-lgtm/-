# Shopee 在庫変動確認・自動出品停止ツール

Amazon.co.jp側の在庫状況を**自分で確認して入力**すると、前回チェック時との差分を検知し、
新しく「在庫切れ」になった商品のShopee出品を**Shopee公式Open Platform APIで自動的に出品停止(unlist)**
するツールです。

## このツールの範囲

- ✅ Amazon.co.jp在庫が切れた商品を検知したら、Shopee側の出品を自動停止(公式API)
- ✅ 在庫が復活したら自動で出品再開(`--auto-relist`、既定はオフ)
- ✅ 前回チェックとの差分管理(すでに停止済みの商品に重複アクションしない)
- ❌ Amazon.co.jpの在庫を自動で取得する機能は含みません(スクレイピングが必要になるため)
- ❌ Amazon.co.jpでの自動購入は含みません(Amazonの利用規約で禁止されている自動購入ボットに該当するため)

**運用イメージ:** 自分でAmazon.co.jpの商品ページを定期的に確認し、`data/watchlist.csv` の
`current_status` 列を `in_stock` / `out_of_stock` に更新してから `check` コマンドを実行します。
ツールはその入力をもとに、Shopee側の出品停止/再開だけを自動化します。

## リスクについて(重要)

Amazonで仕入れてShopeeで無在庫販売する場合、以下のリスクは本ツールでは解消できません。ご認識の上でご利用ください:

- Amazon仕入れが個人購入目的での利用規約に反しないか(転売・自動大量購入は規約上のリスクがあります)
- Shopee側のドロップシッピングに関するポリシー(国・プログラムにより異なります)
- 受注〜Amazon仕入れの間にタイムラグがあり、その間に価格変動・在庫切れが起きるリスクは本ツールの
  「検知後の出品停止」だけでは完全には防げません(検知が早いほど被害は減らせます)

## セットアップ

```bash
cd shopee_stock_watcher
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Shopee API 認証情報の取得手順

1. [Shopee Open Platform](https://open.shopee.com/) で開発者登録し、**アプリを作成**する
   (Live/本番か、まずはSandbox/test-stableで試すか選べます)。
2. アプリ作成後に発行される **Partner ID** と **Partner Key** を `.env` の
   `SHOPEE_PARTNER_ID` / `SHOPEE_PARTNER_KEY` に設定します。
3. アプリの「Redirect URL」設定に、`.env` の `SHOPEE_REDIRECT_URL`(既定
   `http://localhost:8765/callback`)と同じ値を登録します。
4. ショップ認証(OAuth)を行います:
   ```bash
   python -m shopee_stock_watcher.cli auth-url
   ```
   表示されたURLをブラウザで開き、対象のShopeeショップアカウントでログイン・認証します。
   認証後、リダイレクト先URLに `code` と `shop_id` が付与されます(ブラウザには接続先が
   無くエラー画面になりますが、アドレスバーのURLからパラメータだけ取得すればOKです)。
5. 取得した `code` / `shop_id` を渡してトークンを発行します:
   ```bash
   python -m shopee_stock_watcher.cli exchange-token --code XXXX --shop-id 123456
   ```
   出力された `access_token` / `refresh_token` を `.env` の
   `SHOPEE_ACCESS_TOKEN` / `SHOPEE_REFRESH_TOKEN` に、`shop_id` を `SHOPEE_SHOP_ID` に設定します。
6. `access_token` は数時間で失効します。失効したら:
   ```bash
   python -m shopee_stock_watcher.cli refresh-token
   ```

※ Shopee Open Platform APIの仕様(エンドポイント名・パラメータ)は変更されることがあります。
実行前に [公式ドキュメント](https://open.shopee.com/documents) と `src/shopee_stock_watcher/shopee_client.py`
の内容を照らし合わせて確認してください。

## ウォッチリスト形式 (`data/sample_watchlist.csv` 参照)

| カラム | 必須 | 説明 |
|---|---|---|
| `shopee_item_id` | ○ | Shopee出品の item_id(数値) |
| `product_name` | ○ | 商品名(ログ・レポート表示用) |
| `current_status` | ○ | `in_stock` または `out_of_stock`。**毎回、Amazon側を確認して手動更新** |
| `shopee_sku` | - | 自社SKU(任意、記録用) |
| `source_asin` | - | 仕入れ元AmazonのASIN(任意、記録用) |
| `source_price` | - | 仕入れ値(任意、記録用。将来的な利益計算連携に利用可) |

## 使い方

### 1. まずドライランで動作確認(Shopee APIは呼ばれません)

```bash
python -m shopee_stock_watcher.cli check --csv data/sample_watchlist.csv --dry-run
```

### 2. 認証情報設定後、実際に出品停止を実行

```bash
python -m shopee_stock_watcher.cli check --csv data/watchlist.csv --no-dry-run
```

- 前回実行時から新しく `out_of_stock` になった商品だけが出品停止されます
  (`state/last_status.json` に前回状態を保存し、重複実行を防止)。
- 在庫復活時に自動で出品を再開したい場合は `--auto-relist` を付けてください(既定はオフ)。

### 3. 結果確認

`output/stock_watch_<timestamp>.csv` に、商品ごとの状態遷移・実行結果が出力されます。

## テスト

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

ネットワークやShopee認証情報なしで、差分検知ロジック・署名生成・実行フローを検証できます
(Shopee APIクライアントはテスト内でモック化/署名は純粋関数として検証しています)。

## 今後の拡張候補

- `shopee_profit_calculator` の `source_price` と連携し、仕入れ値が上がった場合に警告する
- 複数のウォッチリスト(マーケットプレイス別)をまとめて処理する
- Slack/メール通知の追加(現状はCSVレポートのみ)
