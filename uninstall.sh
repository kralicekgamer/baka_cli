#!/bin/bash
set -e

echo "Odinstalace baka_cli..."

BIN="$HOME/.local/bin/baka_cli"
INSTALL_DIR="$HOME/.local/share/baka_cli"

# 1) Smazat binárku
if [ -f "$BIN" ]; then
    echo "Mazání $BIN"
    rm "$BIN"
else
    echo "Binárka baka_cli nebyla nalezena v ~/.local/bin"
fi

if [ -d "$INSTALL_DIR" ]; then
    echo "Mazání adresáře $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
else
    echo "Instalační adresář nebyl nalezen"
fi

echo "Odinstalace dokončena."