"""CLI entry point.

Usage:
    python -m amazon_auto_listing.cli list --csv data/sample_listings.csv --dry-run
    python -m amazon_auto_listing.cli list --csv data/sample_listings.csv --no-dry-run
    python -m amazon_auto_listing.cli lookup-product-type --asin B0EXAMPLE1
    python -m amazon_auto_listing.cli inspect-schema --product-type LUGGAGE
"""
from __future__ import annotations

import logging

import click

from .config import load_config
from .csv_loader import SheetValidationError, load_listing_sheet
from .listing_service import run_listings
from .reporter import write_report
from .sp_client import SpApiClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Amazon ASIN 自動出品ツール (SP-API 版)"""


@cli.command("list")
@click.option("--csv", "csv_path", required=True, type=click.Path(exists=True), help="出品リストのCSV/Excelファイル")
@click.option("--env-file", default=None, type=click.Path(exists=True), help=".env ファイルのパス (省略時はカレントの .env)")
@click.option("--dry-run/--no-dry-run", default=True, help="実際にはAPIを呼ばず、送信予定のリクエスト内容だけ表示・レポート出力する (デフォルト: on)")
@click.option("--throttle", default=1.0, help="各リクエスト間の待機秒数 (レート制限対策)")
@click.option("--output-dir", default="output", help="結果レポートCSVの出力先ディレクトリ")
def list_command(csv_path, env_file, dry_run, throttle, output_dir):
    """CSV/Excelを読み込み、各行をASINに対する出品としてSP-APIに送信する。"""
    config = load_config(env_file)

    try:
        items = load_listing_sheet(csv_path)
    except SheetValidationError as exc:
        raise click.ClickException(str(exc))

    click.echo(f"{len(items)} 件の出品リクエストを読み込みました。dry_run={dry_run}")

    if not dry_run and not config.is_complete():
        raise click.ClickException(
            "SP-API 認証情報が未設定です。.env を設定するか --dry-run で実行してください。"
        )

    results = run_listings(items, config, dry_run=dry_run, throttle_seconds=throttle)

    report_path = write_report(results, output_dir=output_dir)
    ok = sum(1 for r in results if r.status in ("success", "dry-run", "ACCEPTED"))
    err = sum(1 for r in results if r.status == "error")
    click.echo(f"完了: 成功/受理={ok} 失敗={err} レポート={report_path}")


@cli.command("lookup-product-type")
@click.option("--asin", required=True, help="対象ASIN")
@click.option("--env-file", default=None, type=click.Path(exists=True))
def lookup_product_type(asin, env_file):
    """指定ASINの候補 product_type をCatalog Items APIから取得する。
    入力シートの product_type 列を埋めるための補助コマンド。実credentialsが必要。
    """
    config = load_config(env_file)
    client = SpApiClient(config)
    product_types = client.get_catalog_item_product_types(asin)
    if not product_types:
        click.echo("productType が見つかりませんでした。ASINやマーケットプレイスを確認してください。")
        return
    for pt in product_types:
        click.echo(pt)


@cli.command("inspect-schema")
@click.option("--product-type", required=True, help="Amazon product type コード (例: LUGGAGE, PRODUCT)")
@click.option("--env-file", default=None, type=click.Path(exists=True))
def inspect_schema(product_type, env_file):
    """指定product_typeの必須属性スキーマ定義を取得する(実credentialsが必要)。
    結果を見ながら templates/<PRODUCT_TYPE>.json をカスタマイズしてください。
    """
    config = load_config(env_file)
    client = SpApiClient(config)
    schema = client.get_product_type_schema(product_type)
    click.echo(schema)


if __name__ == "__main__":
    cli()
