#!/usr/bin/env bash
# local-demo-seed.sh — Seed a local demo environment for the workflow builder
#
# Usage: bash scripts/local-demo-seed.sh
#
# This script creates a sample workspace, uploads a demo document,
# configures the fake provider, and creates a demo workflow.
# No cloud API keys are required.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=== Local Demo Seed Script ==="
echo ""

# 1. Check if the CLI is installed
if ! python -c "from decision_system import __version__" 2>/dev/null; then
    echo "Installing package..."
    python -m pip install -e ".[dev]" -q
fi

# 2. Initialize data directory
echo "[1/5] Initializing data directory..."
mkdir -p .decision_system/workspaces
mkdir -p .decision_system/providers

# 3. Create a demo workspace
echo "[2/5] Creating demo workspace..."
python -c "
from decision_system.storage.workspace_store import WorkspaceStore
store = WorkspaceStore()
# Try to create workspace, or find existing
workspaces = store.list()
demo = [w for w in workspaces if w.name == 'Demo Workspace']
if demo:
    print(f'  Workspace already exists: {demo[0].id}')
else:
    ws = store.create(name='Demo Workspace', description='Local demo workspace for workflow builder')
    store.activate(ws.id)
    print(f'  Created workspace: {ws.id}')
" 2>&1 || echo "  (workspace store not available, continuing...)"

# 4. Create sample demo document
echo "[3/5] Creating sample demo document..."
mkdir -p company_docs
DEMO_DOC="company_docs/demo-company-overview.md"
if [ ! -f "$DEMO_DOC" ]; then
    cat > "$DEMO_DOC" << 'DOCEOF'
# Demo Company Overview

## Business Context

DemoCorp is a mid-size enterprise software company with $50M annual revenue.
The company has 200 employees across three offices (New York, London, Tokyo).

## Current Situation

DemoCorp is evaluating a migration from their current billing system to a
new cloud-native platform. The current system handles 10,000 invoices per
month with a 2% error rate. The proposed migration would:

- Reduce error rate to 0.5%
- Increase invoice capacity to 50,000 per month
- Require 6 months of development time
- Cost approximately $500,000

## Key Risks

1. Customer data migration may cause temporary billing disruptions
2. Staff retraining needed for new system
3. Legacy system decommissioning timeline overlaps with peak billing period

## Financial Data

- Annual Revenue: $50,000,000
- Monthly Invoices: 10,000
- Current Error Rate: 2%
- Average Invoice Value: $4,200
- Customer Count: 1,500

DOCEOF
    echo "  Created $DEMO_DOC"
else
    echo "  Demo document already exists"
fi

# 5. Configure fake provider
echo "[4/5] Configuring fake provider..."
python -c "
from decision_system.providers.store import create_provider, list_providers
from decision_system.providers.models import ProviderCreateRequest, ProviderType

existing = list_providers()
fake_providers = [p for p in existing if p.provider_type.value == 'fake' or p.name.lower() == 'fake']
if fake_providers:
    print(f'  Fake provider already configured: {fake_providers[0].name}')
else:
    req = ProviderCreateRequest(
        name='Fake Demo Provider',
        provider_type=ProviderType('fake'),
        default_model='fake-model'
    )
    config = create_provider(req)
    print(f'  Created fake provider: {config.provider_id}')
" 2>&1 || echo "  (provider store not available, continuing...)"

# 6. Index demo documents
echo "[5/5] Indexing demo documents..."
python -c "
from decision_system.index import index_documents
try:
    result = index_documents(directory='company_docs')
    print(f'  Indexed {result} documents')
except Exception as e:
    print(f'  Index command: decision-system index')
" 2>&1 || echo "  Run 'decision-system index' separately if needed"

echo ""
echo "=== Demo seed complete! ==="
echo ""
echo "Next steps:"
echo "  1. Start the API:     decision-system serve-api"
echo "  2. Open the UI:       http://localhost:3000"
echo "  3. Load a template:   Click 'Templates' → 'Local Evidence Search'"
echo "  4. Run the workflow:  Click 'Execute'"
echo "  5. Generate report:   Open Trust Dashboard"
echo ""
echo "Or use Docker:"
echo "  docker compose up"
echo "  Open http://localhost:3000"
