#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  baseball_processor/__init__.py \
  baseball_processor/main.py \
  baseball_processor/audit.py \
  baseball_processor/normalization.py \
  baseball_processor/pipeline.py \
  baseball_processor/sources.py \
  baseball_processor/engines/milestone_engine.py \
  baseball_processor/processors/milestones.py \
  baseball_processor/utils/player_ids.py \
  baseball_processor/website/generator.py \
  baseball_processor/website/parity.py \
  baseball_processor/website/serializers.py

python3 -m pytest
python3 scripts/audit_data_integrity.py

if [ -d web ]; then
  npm run lint --prefix web
  npm run build --prefix web
fi
