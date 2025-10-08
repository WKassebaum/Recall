#!/bin/bash
set -e

echo "🔍 Running quality checks..."
echo "=============================="

# Exit codes
COVERAGE_EXIT=0
CC_EXIT=0
MI_EXIT=0
MYPY_EXIT=0
RUFF_EXIT=0

echo ""
echo "1. 📊 CYCLOMATIC COMPLEXITY:"
radon cc src/semvecmem/ -a -nc || true
radon cc src/semvecmem/ -n C || CC_EXIT=$?

echo ""
echo "2. 🧪 TEST COVERAGE:"
pytest --cov=src/semvecmem --cov-report=term-missing --cov-fail-under=80 -q || COVERAGE_EXIT=$?

echo ""
echo "3. 📈 MAINTAINABILITY INDEX:"
radon mi src/semvecmem/ -s || true
radon mi src/semvecmem/ -n C || MI_EXIT=$?

echo ""
echo "4. 🔎 TYPE CHECKING:"
mypy src/semvecmem/ --strict || MYPY_EXIT=$?

echo ""
echo "5. ✨ CODE QUALITY (ruff):"
ruff check src/semvecmem/ || RUFF_EXIT=$?

echo ""
echo "=============================="
echo "SUMMARY:"
[ $COVERAGE_EXIT -eq 0 ] && echo "✅ Coverage ≥80%" || echo "❌ Coverage <80%"
[ $CC_EXIT -eq 0 ] && echo "✅ Complexity ≤10" || echo "❌ Complexity >10"
[ $MI_EXIT -eq 0 ] && echo "✅ Maintainability ≥C" || echo "❌ Maintainability <C"
[ $MYPY_EXIT -eq 0 ] && echo "✅ Type checking clean" || echo "❌ Type errors found"
[ $RUFF_EXIT -eq 0 ] && echo "✅ Code quality clean" || echo "❌ Quality issues found"

# Exit with failure if any check failed
if [ $COVERAGE_EXIT -ne 0 ] || [ $CC_EXIT -ne 0 ] || [ $MI_EXIT -ne 0 ] || \
   [ $MYPY_EXIT -ne 0 ] || [ $RUFF_EXIT -ne 0 ]; then
    echo ""
    echo "❌ QUALITY CHECKS FAILED"
    exit 1
else
    echo ""
    echo "✅ ALL QUALITY CHECKS PASSED"
    exit 0
fi
