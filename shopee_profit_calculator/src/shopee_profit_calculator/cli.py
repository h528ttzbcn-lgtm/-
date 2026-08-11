"""CLI entry point.

Usage:
    python -m shopee_profit_calculator.cli calc \
        --csv data/sample_products.csv \
        --fee-profile config/fee_profile.json
"""
from __future__ import annotations

import logging

import click

from .calculator import DEFAULT_PRICE_TOLERANCE_PCT, calculate_all
from .csv_loader import SheetValidationError, load_product_sheet
from .fee_profile import load_fee_profile
from .reporter import write_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Shopee 利益計算ツール"""


@cli.command("calc")
@click.option("--csv", "csv_path", required=True, type=click.Path(exists=True), help="商品名/仕入原価/想定販売価格を含むCSV or Excel")
@click.option(
    "--fee-profile",
    "fee_profile_path",
    required=True,
    type=click.Path(exists=True),
    help="Shopee手数料設定JSON (config/fee_profile.example.json をコピーして値を入力したもの)",
)
@click.option("--output-dir", default="output", help="結果CSVの出力先ディレクトリ")
@click.option(
    "--price-tolerance-pct",
    default=DEFAULT_PRICE_TOLERANCE_PCT,
    help=f"推奨価格が現在価格の何%以内なら「維持」とみなすか (既定 {DEFAULT_PRICE_TOLERANCE_PCT * 100:.0f}%)",
)
def calc(csv_path, fee_profile_path, output_dir, price_tolerance_pct):
    """商品ごとの利益・利益率・損益分岐価格に加え、目標利益率を満たす推奨価格と
    値上げ/値下げ判定を一括計算する。
    """
    fee_profile = load_fee_profile(fee_profile_path)

    for w in fee_profile.warnings():
        click.secho(f"[警告] {w}", fg="yellow")

    try:
        products = load_product_sheet(csv_path)
    except SheetValidationError as exc:
        raise click.ClickException(str(exc))

    click.echo(f"{len(products)} 件の商品を読み込みました。")

    results = calculate_all(products, fee_profile, price_tolerance_pct=price_tolerance_pct)

    profitable = sum(1 for r in results if r.is_profitable)
    click.echo(f"黒字見込み: {profitable} / {len(results)} 件")

    reprice = [r for r in results if r.price_action in ("値上げ推奨", "値下げ推奨")]
    if reprice:
        click.echo(f"価格見直し推奨: {len(reprice)} 件")
        for r in reprice:
            click.echo(
                f"  [{r.price_action}] {r.product_name}: "
                f"現在価格={r.selling_price:.2f} 推奨価格={r.recommended_price:.2f} "
                f"差={r.price_diff:+.2f}"
            )

    for r in sorted(results, key=lambda r: r.margin_rate if r.margin_rate is not None else float("-inf"))[:5]:
        margin_pct = f"{r.margin_rate * 100:.1f}%" if r.margin_rate is not None else "N/A"
        click.echo(f"  [利益率最低] {r.product_name}: 利益/個={r.profit_per_unit:.2f} 利益率={margin_pct}")

    report_path = write_report(results, output_dir=output_dir)
    click.echo(f"レポート出力: {report_path}")


if __name__ == "__main__":
    cli()
