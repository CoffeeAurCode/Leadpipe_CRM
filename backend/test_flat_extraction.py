"""
Test script to validate _extract_flat_number() regex pattern priority fix.

Tests that alphanumeric patterns are matched before pure digits,
preventing "A101" from being incorrectly parsed as "101".
"""

from app.ai.extractor import _extract_flat_number


def test_flat_extraction():
    """Validate all flat number formats extract correctly."""
    
    test_cases = [
        # (input, expected_output, description)
        ("A101", "A101", "Alphanumeric without hyphen"),
        ("B203", "B203", "Different letter prefix"),
        ("101", "101", "Pure numeric flat"),
        ("202", "202", "Another pure numeric"),
        ("  A102  ", "A102", "Alphanumeric with whitespace"),
        ("flat A101", "A101", "Keyword + alphanumeric"),
        ("unit B204", "B204", "Unit keyword variant"),
        ("A-101", "A-101", "Hyphenated format"),
        ("B-205", "B-205", "Another hyphenated"),
        ("A 101", "A 101", "Letter space digits"),
        ("101A", "101A", "Digits with letter suffix"),
        ("C304", "C304", "Three-digit alphanumeric"),
        ("  101  ", "101", "Pure digits with whitespace"),
    ]
    
    print("=" * 70)
    print("FLAT NUMBER EXTRACTION VALIDATION")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for input_text, expected, description in test_cases:
        result = _extract_flat_number(input_text)
        
        if result == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        print(f"\n{status} | {description}")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED - Regex pattern priority fix is working correctly!")
        return True
    else:
        print(f"\n❌ {failed} TESTS FAILED - Review pattern matching logic")
        return False


if __name__ == "__main__":
    success = test_flat_extraction()
    exit(0 if success else 1)
