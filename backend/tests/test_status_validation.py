
import sys
import os

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.schemas.complaint import ComplaintCreate
from pydantic import ValidationError

def test_validation():
    print("Testing Complaint Status Validation...")
    
    # Test 1: Valid statuses
    print("\n1. Testing Valid Statuses:")
    for status in ['pending', 'in-progress', 'resolved']:
        try:
            complaint = ComplaintCreate(
                category="maintenance",
                appointment_datetime="2026-02-14T10:00:00",
                description="Test complaint",
                status=status,
                source="test"
            )
            print(f"   [PASS] '{status}' accepted")
        except ValidationError as e:
            print(f"   [FAIL] '{status}' rejected: {e}")
            return False

    # Test 2: Invalid status (underscore)
    print("\n2. Testing Invalid Status 'in_progress':")
    try:
        ComplaintCreate(
            category="maintenance",
            appointment_datetime="2026-02-14T10:00:00",
            description="Test",
            status="in_progress",
            source="test"
        )
        print("   [FAIL] 'in_progress' was accepted (should fail)")
        return False
    except ValidationError as e:
        if "Invalid status 'in_progress'" in str(e):
            print("   [PASS] 'in_progress' correctly rejected")
        else:
            print(f"   [WARN] Rejected but with unexpected error: {e}")

    # Test 3: Invalid random status
    print("\n3. Testing Random Invalid Status:")
    try:
        ComplaintCreate(
            category="maintenance",
            appointment_datetime="2026-02-14T10:00:00",
            description="Test",
            status="foo_bar",
            source="test"
        )
        print("   [FAIL] 'foo_bar' was accepted (should fail)")
        return False
    except ValidationError as e:
        if "Invalid status 'foo_bar'" in str(e):
            print("   [PASS] 'foo_bar' correctly rejected")
        else:
            print(f"   [WARN] Rejected but with unexpected error: {e}")

    print("\n[SUCCESS] ALL VALIDATION TESTS PASSED")
    return True

if __name__ == "__main__":
    success = test_validation()
    sys.exit(0 if success else 1)
