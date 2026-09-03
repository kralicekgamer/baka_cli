#!/bin/bash
set -e

echo "Instalace baka_cli..."

INSTALL_DIR="$HOME/.local/share/baka_cli"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

git clone https://github.com/kralicekgamer/baka_cli repo
cd repo

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

echo "#!/bin/bash" > baka_cli
echo "\"$INSTALL_DIR/repo/.venv/bin/python3\" \"$INSTALL_DIR/repo/baka_cli.py\" \"\$@\"" >> baka_cli
chmod +x baka_cli

mkdir -p "$HOME/.local/bin"
mv baka_cli "$HOME/.local/bin/baka_cli"

echo "Instalace dokončena."