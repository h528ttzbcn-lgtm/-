"""CLI entry point.

Usage:
    python -m amazon_arbitrage_finder.cli research --queries data/sample_queries.csv \
        --settings config/research_settings.example.json
    python -m amazon_arbitrage_finder.cli research --manual-items data/sample_manual_items.csv
    python -m amazon_arbitrage_finder.cli research --queries data/sample_queries.csv --skip-amazon
"""
from __future__ import annotations

import logging
from datetime import datetime

import click

from .amazon_client import AmazonClient
from .config import load_config
from .csv_loader import SheetValidationError, load_manual_items, load_queries
from .reporter import write_listing_sheet, write_report
from .research_service import prefilter, research
from .settings import load_settings
from .sources.rakuten_client import RakutenApiError, RakutenClient
from .sources.yahoo_client import YahooApiError, YahooClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Amazon せどりリサーチツール (楽天市場 / Yahoo!ショッピング → Amazon)"""


@cli.command("research")
@click.option("--queries", "queries_path", type=click.Path(exists=True), help="検索条件シート (CSV/Excel)")
@click.option("--manual-items", "manual_path", type=click.Path(exists=True), help="手入力の仕入れ商品シート (CSV/Excel)")
@click.option("--settings", "settings_path", type=click.Path(exists=True), help="リサーチ設定JSON (省略時は既定値)")
@click.option("--env-file", default=None, type=click.Path(exists=True), help=".env ファイルのパス")
@click.option("--skip-amazon", is_flag=True, help="Amazon照合をせず、仕入れ先の検索結果(JAN付き)だけ出力する")
@click.option("--throttle", default=1.0, help="楽天/Yahoo! APIのページ間の待機秒数")
@click.option("--output-dir", default="output", help="出力先ディレクトリ")
def research_command(queries_path, manual_path, settings_path, env_file, skip_amazon, throttle, output_dir):
    """仕入れ先を検索し、Amazonで利益が出る商品を洗い出す。"""
    if not queries_path and not manual_path:
        raise click.UsageError("--queries と --manual-items の少なくとも一方を指定してください。")

    config = load_config(env_file)
    try:
        settings = load_settings(settings_path)
    except ValueError as exc:
        raise click.ClickException(str(exc))
    for msg in settings.warnings():
        click.echo(f"[設定の警告] {msg}", err=True)

    try:
        queries = load_queries(queries_path) if queries_path else []
        items = load_manual_items(manual_path) if manual_path else []
    except SheetValidationError as exc:
        raise click.ClickException(str(exc))

    clients = {
        "rakuten": RakutenClient(config.rakuten, throttle_seconds=throttle),
        "yahoo": YahooClient(config.yahoo, throttle_seconds=throttle),
    }
    for query in queries:
        try:
            items.extend(clients[query.source].search(query))
        except (RakutenApiError, YahooApiError) as exc:
            raise click.ClickException(str(exc))
    click.echo(f"仕入れ先の商品 {len(items)} 件を取得しました。")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if skip_amazon:
        kept, rejected = prefilter(items, settings)
        for c in kept:
            c.status = "未照合"
        report = write_report(kept + rejected, output_dir, timestamp)
        click.echo(f"JAN付きの照合対象 {len(kept)} 件。レポート={report}")
        return

    if not config.sp_api.is_complete():
        raise click.ClickException(
            "SP-API 認証情報が未設定です。.env を設定するか、--skip-amazon で仕入れ先の検索だけ実行してください。"
        )

    candidates = research(items, AmazonClient(config.sp_api), settings)
    report = write_report(candidates, output_dir, timestamp)
    listing = write_listing_sheet(candidates, settings, output_dir, timestamp)

    ok = sum(1 for c in candidates if c.is_ok)
    click.echo(f"完了: 利益候補={ok}件 / 全{len(candidates)}件 レポート={report}")
    if listing:
        click.echo(
            f"出品用CSV={listing}\n"
            "  ※ 仕入れて在庫を確保してから quantity を設定し、amazon_auto_listing で出品してください。"
        )


if __name__ == "__main__":
    cli()
