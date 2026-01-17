#!/bin/bash
# API Test Runner - 3 Iterations
# Tests all calculator endpoints on the live Brew Brain instance

PI_URL="${1:-http://192.168.155.226:5000}"

echo "🧪 Brew Brain API Test Suite"
echo "============================"
echo "Target: $PI_URL"
echo ""

test_count=0
pass_count=0
fail_count=0

run_test() {
    local name="$1"
    local endpoint="$2"
    local data="$3"
    
    test_count=$((test_count + 1))
    
    result=$(curl -s -w "\n%{http_code}" -X POST "$PI_URL$endpoint" \
        -H "Content-Type: application/json" \
        -d "$data" 2>/dev/null)
    
    http_code=$(echo "$result" | tail -n1)
    body=$(echo "$result" | sed '$d')
    
    if [ "$http_code" = "200" ] && [ ! -z "$body" ] && [[ ! "$body" =~ "error" ]]; then
        echo "✅ $name"
        pass_count=$((pass_count + 1))
        return 0
    else
        echo "❌ $name (HTTP $http_code)"
        echo "   Response: ${body:0:100}..."
        fail_count=$((fail_count + 1))
        return 1
    fi
}

run_iteration() {
    local iteration=$1
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 Iteration $iteration"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Carbonation tests
    run_test "Carbonation (4°C, 2.5 vol)" \
        "/api/automation/calc/carbonation" \
        '{"temp_c": 4, "volumes_co2": 2.5}'
    
    run_test "Carbonation (20°C, 2.8 vol)" \
        "/api/automation/calc/carbonation" \
        '{"temp_c": 20, "volumes_co2": 2.8}'
    
    # Refractometer tests
    run_test "Refractometer (15/8 Brix)" \
        "/api/automation/calc/refractometer" \
        '{"original_brix": 15.0, "final_brix": 8.0}'
    
    run_test "Refractometer (20/10 Brix)" \
        "/api/automation/calc/refractometer" \
        '{"original_brix": 20.0, "final_brix": 10.0}'
    
    # Priming tests
    run_test "Priming (20L, corn sugar)" \
        "/api/automation/calc/priming" \
        '{"volume_liters": 20, "temp_c": 20, "target_co2": 2.4, "sugar_type": "corn_sugar"}'
    
    run_test "Priming (23L, honey)" \
        "/api/automation/calc/priming" \
        '{"volume_liters": 23, "temp_c": 18, "target_co2": 2.6, "sugar_type": "honey"}'
    
    # Water chemistry tests
    run_test "Water Chemistry (NEIPA)" \
        "/api/automation/calc/water_chemistry" \
        '{"target_profile": "neipa", "volume_liters": 23}'
    
    run_test "Water Chemistry (West Coast)" \
        "/api/automation/calc/water_chemistry" \
        '{"target_profile": "west_coast", "volume_liters": 20}'
    
    # Mash pH tests
    run_test "Mash pH (Pale Ale)" \
        "/api/automation/calc/mash_ph" \
        '{"grains": [{"name": "Pale Malt", "weight_kg": 5.0, "lovibond": 2.5}], "water_profile": {"bicarbonate": 50, "calcium": 80, "magnesium": 10}}'
    
    run_test "Mash pH (Stout)" \
        "/api/automation/calc/mash_ph" \
        '{"grains": [{"name": "Pale Malt", "weight_kg": 4.0, "lovibond": 2.5}, {"name": "Roasted Barley", "weight_kg": 0.5, "lovibond": 500}], "water_profile": {"bicarbonate": 100, "calcium": 100, "magnesium": 20}}'
    
    # Hop freshness tests
    run_test "Hop Freshness (Fresh Citra)" \
        "/api/automation/calc/hop_freshness" \
        '{"hop_name": "Citra", "original_alpha": 12.0, "purchase_date": "2026-01-01", "storage": "freezer"}'
    
    run_test "Hop Freshness (Old Cascade)" \
        "/api/automation/calc/hop_freshness" \
        '{"hop_name": "Cascade", "original_alpha": 6.0, "purchase_date": "2025-01-01", "storage": "ambient"}'
    
    # IBU test
    run_test "IBU Calculation" \
        "/api/automation/calc_ibu" \
        '{"amount": 50, "alpha": 10, "time": 60, "volume": 23, "gravity": 1.050}'
    
    # Status check
    status=$(curl -s "$PI_URL/api/status" 2>/dev/null)
    if [ ! -z "$status" ]; then
        echo "✅ Status endpoint"
        pass_count=$((pass_count + 1))
        test_count=$((test_count + 1))
    fi
}

# Run 3 iterations
for i in 1 2 3; do
    run_iteration $i
    sleep 1
done

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total Tests: $test_count"
echo "Passed:      $pass_count"
echo "Failed:      $fail_count"
echo ""

if [ $fail_count -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
    exit 0
else
    echo "❌ SOME TESTS FAILED"
    exit 1
fi
