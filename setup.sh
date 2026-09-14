cat > setup.sh << 'EOF'
#!/usr/bin/env bash
#
# setup.sh -- per-repo dependency setup. Django/Track-B specific.
# See RCMS Technical Spec v1.9, Section 9.7 for why this exists
# separately from the machine-level bootstrap scripts.
#
# USAGE: ./setup.sh   (run once per machine this repo is cloned onto)
#
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ -d venv ]]; then
  echo "==> venv/ already exists here -- skipping creation."
else
  echo "==> Creating venv/"
  python3 -m venv venv
fi

echo "==> Installing dependencies from requirements.txt"
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet -r requirements.txt

echo ""
echo "==> Done. Activate it yourself now (a script can't do this for your shell):"
echo ""
echo "        source venv/bin/activate"
echo ""
echo "    Then, for a quick local check without a live Postgres connection:"
echo ""
echo "        export DB_ENGINE=sqlite3"
echo "        python manage.py check"
echo "        python manage.py test domain api"
EOF
