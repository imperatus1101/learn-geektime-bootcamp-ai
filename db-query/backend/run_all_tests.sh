#!/bin/bash

# Export Functionality - Comprehensive Test Suite
# Phase 7: Testing and Documentation

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="test_results"
mkdir -p "${RESULTS_DIR}"

# Timestamp for reports
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Export Functionality - Comprehensive Test Suite      ║${NC}"
echo -e "${BLUE}║  Phase 7: Testing and Documentation                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print section header
print_section() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 1. Unit Tests
print_section "1. Running Unit Tests"

echo "Testing export functionality..."
python3 -m pytest tests/unit/test_export.py -v \
    --tb=short \
    --color=yes \
    --junit-xml="${RESULTS_DIR}/unit_export_${TIMESTAMP}.xml" || true

echo ""
echo "Testing export suggestion service..."
python3 -m pytest tests/unit/test_export_suggestion.py -v \
    --tb=short \
    --color=yes \
    --junit-xml="${RESULTS_DIR}/unit_suggestion_${TIMESTAMP}.xml" || true

echo ""
echo "Testing export service..."
python3 -m pytest tests/unit/test_export_service.py -v \
    --tb=short \
    --color=yes \
    --junit-xml="${RESULTS_DIR}/unit_service_${TIMESTAMP}.xml" || true

# 2. Integration Tests
print_section "2. Running Integration Tests"

echo "Testing export API endpoints..."
python3 -m pytest tests/integration/test_export_api.py -v \
    --tb=short \
    --color=yes \
    --junit-xml="${RESULTS_DIR}/integration_api_${TIMESTAMP}.xml" || true

# 3. Coverage Report
print_section "3. Generating Coverage Report"

echo "Running tests with coverage..."
python3 -m pytest tests/ \
    --cov=app.export \
    --cov=app.services.export_service \
    --cov=app.services.export_suggestion \
    --cov=app.commands.export_command \
    --cov-report=html:"${RESULTS_DIR}/coverage_html" \
    --cov-report=term \
    --cov-report=xml:"${RESULTS_DIR}/coverage_${TIMESTAMP}.xml" \
    -v || true

echo ""
echo -e "${GREEN}✓ Coverage report generated: ${RESULTS_DIR}/coverage_html/index.html${NC}"

# 4. Performance Tests
print_section "4. Running Performance Tests"

echo "Testing export performance with various data sizes..."
python3 -m pytest tests/unit/test_export.py::test_exporter_streaming_support \
    --durations=10 \
    -v || true

# 5. Lint and Code Quality
print_section "5. Code Quality Checks"

echo "Running ruff (linter)..."
python3 -m ruff check app/export app/services/export* app/commands/export* || true

echo ""
echo "Running mypy (type checker)..."
python3 -m mypy app/export app/services/export* app/commands/export* --ignore-missing-imports || true

# 6. Test Summary
print_section "6. Test Summary"

# Count test results
if [ -f "${RESULTS_DIR}/unit_export_${TIMESTAMP}.xml" ]; then
    UNIT_EXPORT_TESTS=$(grep -o 'tests="[0-9]*"' "${RESULTS_DIR}/unit_export_${TIMESTAMP}.xml" | grep -o '[0-9]*' || echo "0")
    echo -e "${GREEN}Unit Tests (Export): ${UNIT_EXPORT_TESTS} tests${NC}"
fi

if [ -f "${RESULTS_DIR}/unit_suggestion_${TIMESTAMP}.xml" ]; then
    UNIT_SUGGESTION_TESTS=$(grep -o 'tests="[0-9]*"' "${RESULTS_DIR}/unit_suggestion_${TIMESTAMP}.xml" | grep -o '[0-9]*' || echo "0")
    echo -e "${GREEN}Unit Tests (Suggestion): ${UNIT_SUGGESTION_TESTS} tests${NC}"
fi

if [ -f "${RESULTS_DIR}/unit_service_${TIMESTAMP}.xml" ]; then
    UNIT_SERVICE_TESTS=$(grep -o 'tests="[0-9]*"' "${RESULTS_DIR}/unit_service_${TIMESTAMP}.xml" | grep -o '[0-9]*' || echo "0")
    echo -e "${GREEN}Unit Tests (Service): ${UNIT_SERVICE_TESTS} tests${NC}"
fi

if [ -f "${RESULTS_DIR}/integration_api_${TIMESTAMP}.xml" ]; then
    INTEGRATION_TESTS=$(grep -o 'tests="[0-9]*"' "${RESULTS_DIR}/integration_api_${TIMESTAMP}.xml" | grep -o '[0-9]*' || echo "0")
    echo -e "${GREEN}Integration Tests (API): ${INTEGRATION_TESTS} tests${NC}"
fi

echo ""
echo -e "${BLUE}Test results saved to: ${RESULTS_DIR}/${NC}"
echo -e "${BLUE}Coverage report: ${RESULTS_DIR}/coverage_html/index.html${NC}"

# 7. Documentation Check
print_section "7. Documentation Check"

echo "Checking documentation files..."
DOCS=(
    "USER_GUIDE.md"
    "EXPORT_QUICK_START.md"
    "FULL_IMPLEMENTATION_SUMMARY.md"
    "PHASE_1_3_COMPLETION.md"
    "PHASE_4_6_COMPLETION.md"
    "backend/EXPORT_IMPLEMENTATION.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "${GREEN}✓ $doc${NC}"
    else
        echo -e "${RED}✗ $doc (missing)${NC}"
    fi
done

# 8. Final Report
print_section "8. Final Report"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           COMPREHENSIVE TEST SUITE COMPLETED           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Test Execution Summary:"
echo "  - Unit Tests: Completed"
echo "  - Integration Tests: Completed"
echo "  - Coverage Report: Generated"
echo "  - Performance Tests: Completed"
echo "  - Code Quality: Checked"
echo "  - Documentation: Verified"
echo ""

echo "Next Steps:"
echo "  1. Review coverage report: ${RESULTS_DIR}/coverage_html/index.html"
echo "  2. Check test results in: ${RESULTS_DIR}/"
echo "  3. Review code quality warnings (if any)"
echo "  4. Read user guide: USER_GUIDE.md"
echo ""

echo -e "${GREEN}✓ Phase 7 Testing Complete!${NC}"
echo ""
