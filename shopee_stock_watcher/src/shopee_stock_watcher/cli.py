"""CLI entry point.

Typical flow:
    1. (once) python -m shopee_stock_watcher.cli auth-url
       -> open the printed URL in a browser, authorize your shop
       -> copy `code` and `shop_id` from the redirect URL
    2. (once) python -m shopee_stock_watcher.cli exchange-token --code XXX --shop-id 123
       -> paste the printed access_token/refresh_token into .env
    3. each time you've checked Amazon stock and updated data/watchlist.csv:
       python -m shopee_stock_watcher.cli check --csv data/watchlist.csv --dry-run
       python -m shopee_stock_watcher.cli check --csv data/watchlist.csv --no-dry-run
"""
from __future__ import annotations

import logging

import click

from .config import load_config
from .csv_loader import SheetValidationError, load_watchlist
from .reporter import write_report
from .shopee_client import ShopeeApiError, ShopeeClient
from .watcher_service import run_watch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Shopee 在庫変動確認・自動出品停止ツール"""


@cli.command("check")
@click.option("--csv", "csv_path", required=True, type=click.Path(exists=True), help="ウォッチリストCSV/Excel")
@click.option("--env-file", default=None, type=click.Path(exists=True))
@click.option("--state-file", default="state/last_status.json", help="前回状態の保存先")
@click.option("--dry-run/--no-dry-run", default=True, help="実際にはShopee APIを呼ばず、何が起きるかだけ表示する (デフォルト: on)")
@click.option("--auto-relist/--no-auto-relist", default=False, help="在庫復活時に自動で出品再開するか (デフォルト: off、在庫切れ停止のみ)")
@click.option("--output-dir", default="output", help="結果レポートCSVの出力先ディレクトリ")
def check(csv_path, env_file, state_file, dry_run, auto_relist, output_dir):
    """ウォッチリストのcurrent_statusを前回と比較し、在庫切れに新しくなった商品を
    Shopeeで出品停止(unlist)する。auto-relist有効時は在庫復活で出品再開もする。
    """
    config = load_config(env_file)

    try:
        items = load_watchlist(csv_path)
    except SheetValidationError as exc:
        raise click.ClickException(str(exc))

    click.echo(f"{len(items)} 件のウォッチ対象を読み込みました。dry_run={dry_run} auto_relist={auto_relist}")

    results = run_watch(items, config, state_path=state_file, dry_run=dry_run, auto_relist=auto_relist)

    report_path = write_report(results, output_dir=output_dir)
    delisted = sum(1 for r in results if "delist" in r.action and r.result == "ok")
    relisted = sum(1 for r in results if "relist" in r.action and r.result == "ok")
    errors = sum(1 for r in results if r.result == "error")
    click.echo(f"完了: 出品停止={delisted} 出品再開={relisted} エラー={errors} レポート={report_path}")


@cli.command("auth-url")
@click.option("--env-file", default=None, type=click.Path(exists=True))
def auth_url(env_file):
    """ショップ認証(OAuth)用URLを表示する。ブラウザで開いて認証してください。"""
    config = load_config(env_file)
    if not config.is_app_registered():
        raise click.ClickException("SHOPEE_PARTNER_ID / SHOPEE_PARTNER_KEY が未設定です。")
    client = ShopeeClient(config)
    click.echo(client.build_authorization_url())
    click.echo(
        "\n上記URLをブラウザで開き、対象ショップで認証してください。"
        f"\n認証後 {config.redirect_url} に code と shop_id 付きでリダイレクトされます。"
        "\nそのcode/shop_idを `exchange-token` コマンドに渡してください。"
    )


@cli.command("exchange-token")
@click.option("--code", required=True, help="リダイレクトURLの code パラメータ")
@click.option("--shop-id", required=True, type=int, help="リダイレクトURLの shop_id パラメータ")
@click.option("--env-file", default=None, type=click.Path(exists=True))
def exchange_token(code, shop_id, env_file):
    """認証コードを access_token / refresh_token に交換する。"""
    config = load_config(env_file)
    client = ShopeeClient(config)
    try:
        data = client.exchange_token(code, shop_id)
    except ShopeeApiError as exc:
        raise click.ClickException(str(exc))
    click.echo(data)
    click.echo(
        "\n上の access_token / refresh_token を .env の "
        "SHOPEE_ACCESS_TOKEN / SHOPEE_REFRESH_TOKEN と、"
        f"SHOPEE_SHOP_ID={shop_id} に設定してください。"
    )


@cli.command("refresh-token")
@click.option("--env-file", default=None, type=click.Path(exists=True))
def refresh_token(env_file):
    """refresh_tokenを使ってaccess_tokenを更新する(access_tokenは短時間で失効します)。"""
    config = load_config(env_file)
    if not config.refresh_token:
        raise click.ClickException("SHOPEE_REFRESH_TOKEN が未設定です。先に exchange-token を実行してください。")
    client = ShopeeClient(config)
    try:
        data = client.refresh_access_token()
    except ShopeeApiError as exc:
        raise click.ClickException(str(exc))
    click.echo(data)
    click.echo("\n新しい access_token / refresh_token を .env に反映してください。")


if __name__ == "__main__":
    cli()
