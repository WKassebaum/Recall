#!/bin/bash

echo "📊 Daily Quality Dashboard - $(date +%Y-%m-%d)"
echo "============================================="

# Quick metrics (suppress errors for files that don't exist yet)
echo ""
if [ -d "src/semvecmem" ]; then
    echo "Coverage: $(pytest --cov=src/semvecmem --cov-report=term 2>/dev/null | grep TOTAL | awk '{print $4}' || echo 'N/A')"
    echo "CC Average: $(radon cc src/semvecmem/ -a -s 2>/dev/null | grep 'Average complexity' | awk '{print $3}' || echo 'N/A')"
    echo "MI Average: $(radon mi src/semvecmem/ -s 2>/dev/null | grep 'Average MI' | awk '{print $3}' || echo 'N/A')"

    TEST_COUNT=$(find tests -name "test_*.py" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "Test Files: $TEST_COUNT"

    TYPE_ERRORS=$(mypy src/semvecmem/ 2>&1 | grep -c "error:" || echo 0)
    echo "Type Errors: $TYPE_ERRORS"

    QUALITY_ISSUES=$(ruff check src/semvecmem/ 2>&1 | grep -c "error\|warning" || echo 0)
    echo "Code Quality Issues: $QUALITY_ISSUES"
else
    echo "⚠️  Project not yet initialized"
fi

# Trend (compare with yesterday if exists)
if [ -f "yesterday_metrics.txt" ]; then
    echo ""
    echo "Trend (vs yesterday):"
    diff yesterday_metrics.txt today_metrics.txt 2>/dev/null || echo "No changes or first run"
fi

# Save today's metrics
cat > today_metrics.txt <<EOF
$(date +%Y-%m-%d)
$(pytest --cov=src/semvecmem --cov-report=term 2>/dev/null | grep TOTAL || echo "No coverage data")
$(radon cc src/semvecmem/ -a -s 2>/dev/null | grep 'Average complexity' || echo "No complexity data")
$(radon mi src/semvecmem/ -s 2>/dev/null | grep 'Average MI' || echo "No MI data")
EOF

# Archive yesterday's data
cp today_metrics.txt yesterday_metrics.txt 2>/dev/null || true
