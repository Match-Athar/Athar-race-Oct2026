#!/usr/bin/env bash
# Daily: put today's Odoo export in data/pos.xlsx (and the month's target in data/target.xlsx), then run:
#   bash update_board.sh
# Builds the public board and publishes it to https://ibraq-athar.github.io/athar-race/
set -e
cd "$(dirname "$0")"
python3 run.py --pos data/pos.xlsx --target data/target.xlsx --public-only --out site
python3 publish_github.py --token-file github-token.txt --page site/index.html --repo athar-race
