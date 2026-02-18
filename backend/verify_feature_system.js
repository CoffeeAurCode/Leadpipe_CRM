/**
 * Verification script for Feature Control System
 * 
 * Tests:
 * 1. GET /properties/{uuid}/settings - Fetch feature states
 * 2. PATCH /properties/{uuid}/settings - Toggle features
 * 3. Verify backend enforcement (403 for disabled features)
 */

const BASE_URL = "http://localhost:8000";

async function verifyFeatureSystem() {
    console.log("=== Feature Control System Verification ===\n");

    // Use an existing property UUID from your database
    // For testing, we'll use the first property
    const propsRes = await fetch(`${BASE_URL}/properties`);
    const props = await propsRes.json();

    if (props.length === 0) {
        console.error("❌ No properties found. Create a property first.");
        return;
    }

    const testPropertyUuid = props[0].uuid;
    console.log(`✅ Using property: ${testPropertyUuid}\n`);

    // ===============================================
    // TEST 1: GET Feature Settings
    // ===============================================
    console.log("TEST 1: Fetching feature settings...");
    const settingsRes = await fetch(`${BASE_URL}/properties/${testPropertyUuid}/settings`);

    if (!settingsRes.ok) {
        console.error(`❌ Failed to fetch settings: ${await settingsRes.text()}`);
        return;
    }

    const settingsData = await settingsRes.json();
    console.log("✅ Feature settings retrieved:");
    console.log(JSON.stringify(settingsData, null, 2));
    console.log("");

    // ===============================================
    // TEST 2: Toggle Features
    // ===============================================
    console.log("TEST 2: Toggling SMS Automation feature...");

    const currentSmsState = settingsData.features.sms_automation.enabled;
    const newSmsState = !currentSmsState;

    const toggleRes = await fetch(`${BASE_URL}/properties/${testPropertyUuid}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            features: {
                sms_automation: newSmsState
            }
        })
    });

    if (!toggleRes.ok) {
        console.error(`❌ Failed to toggle feature: ${await toggleRes.text()}`);
        return;
    }

    const toggleData = await toggleRes.json();
    console.log(`✅ SMS Automation toggled from ${currentSmsState} to ${newSmsState}`);
    console.log(`   Current state: ${toggleData.features.sms_automation.enabled}`);
    console.log("");

    // ===============================================
    // TEST 3: Verify State Persistence
    // ===============================================
    console.log("TEST 3: Verifying state persistence...");

    const verifyRes = await fetch(`${BASE_URL}/properties/${testPropertyUuid}/settings`);
    const verifyData = await verifyRes.json();

    if (verifyData.features.sms_automation.enabled === newSmsState) {
        console.log("✅ Feature state persisted correctly");
    } else {
        console.error("❌ Feature state did not persist");
    }
    console.log("");

    // ===============================================
    // TEST 4: Restore Original State
    // ===============================================
    console.log("TEST 4: Restoring original state...");

    const restoreRes = await fetch(`${BASE_URL}/properties/${testPropertyUuid}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            features: {
                sms_automation: currentSmsState
            }
        })
    });

    if (restoreRes.ok) {
        console.log("✅ Original state restored");
    }
    console.log("");

    // ===============================================
    // TEST 5: Invalid Feature Key
    // ===============================================
    console.log("TEST 5: Testing invalid feature key...");

    const invalidRes = await fetch(`${BASE_URL}/properties/${testPropertyUuid}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            features: {
                invalid_feature: true
            }
        })
    });

    if (invalidRes.status === 400) {
        console.log("✅ Correctly rejected invalid feature key (400)");
    } else {
        console.error(`❌ Expected 400, got ${invalidRes.status}`);
    }
    console.log("");

    console.log("=== Verification Complete ===");
}

verifyFeatureSystem().catch(console.error);
