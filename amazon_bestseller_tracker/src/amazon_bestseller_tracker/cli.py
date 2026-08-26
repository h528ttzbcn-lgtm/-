"""CLI entry point.

Usage:
    python -m amazon_bestseller_tracker.cli snapshot --csv data/sample_watchlist.csv --dry-run
    python -m amazon_bestseller_tracker.cli snapshot --csv data/sample_watchlist.csv --no-dry-run
    python -m amazon_bestseller_tracker.cli lookup --asin B0EXAMPLE1
"""
from __future__ import annotations

import logging

import click

from .config import load_config
from .csv_loader import SheetValidationError, load_watchlist
from .reporter import write_report
from .snapshot_service import run_snapshot
from .sp_client import SpApiClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Amazon 売れ筋(ランキング・価格)データ化ツール (SP-API + 任意でKeepa連携)"""


@cli.command("snapshot")
@click.option("--csv", "csv_path", required=True, type=click.Path(exists=True), help="追跡対象ASINのCSV/Excel")
@click.option("--env-file", default=None, type=click.Path(exists=True), help=".env ファイルのパス (省略時はカレントの .env)")
@click.option("--dry-run/--no-dry-run", default=True, help="実際にはAPIを呼ばず、前回までの履歴だけ表示する (デフォルト: on)")
@click.option("--history-file", default="history/snapshot_log.jsonl", help="時系列データの蓄積先(JSON Lines)")
@click.option("--output-dir", default="output", help="一覧CSVの出力先ディレクトリ")
@click.option("--keepa-days", default=30, help="Keepa連携時に集計する期間(日数)")
def snapshot(csv_path, env_file, dry_run, history_file, output_dir, keepa_days):
    """ウォッチリストの各ASINについて、現在のランキング・価格(KEEPA_API_KEY設定時は
    過去平均も)を取得し、Keepa風の一覧CSVに出力する。実行するたびに history-file に
    追記されるので、cron等で定期実行するとKeepaのような推移データが自分の手元に蓄積される。
    """
    config = load_config(env_file)

    try:
        items = load_watchlist(csv_path)
    except SheetValidationError as exc:
        raise click.ClickException(str(exc))

    click.echo(
        f"{len(items)} 件の追跡対象を読み込みました。"
        f" dry_run={dry_run} keepa連携={'有効' if config.keepa_api_key else '無効'}"
    )

    rows = run_snapshot(items, config, history_path=history_file, dry_run=dry_run, keepa_stats_days=keepa_days)

    report_path = write_report(rows, output_dir=output_dir)
    ok = sum(1 for r in rows if r.status == "ok")
    dry_run_count = sum(1 for r in rows if r.status == "dry-run")
    errors = sum(1 for r in rows if r.status == "error")
    click.echo(f"完了: 取得成功={ok} dry-run={dry_run_count} 失敗={errors} レポート={report_path}")


@cli.command("lookup")
@click.option("--asin", required=True, help="対象ASIN")
@click.option("--env-file", default=None, type=click.Path(exists=True))
def lookup(asin, env_file):
    """単一ASINのカタログ情報(タイトル・ブランド・ランキング・価格)を即座に
    確認する(実credentialsが必要。疎通確認・単発チェック用)。
    """
    config = load_config(env_file)
    client = SpApiClient(config)
    snapshot_data = client.get_catalog_snapshot(asin)
    price, currency = client.get_current_price(asin)
    click.echo(snapshot_data)
    click.echo(f"price: {price} {currency}")


if __name__ == "__main__":
    cli()
