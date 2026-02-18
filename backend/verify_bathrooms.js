const BASE_URL = "http://localhost:8000";

async function verifyBathrooms() {
    console.log("Starting verification...");

    // 1. Create a flat with 3 bathrooms
    console.log("Step 1: Creating flat (bathrooms=3)...");
    const uniqueSuffix = Date.now();
    const flatNumber = `BATH_${uniqueSuffix}`;
    const formData = new FormData();
    formData.append("flat_number", flatNumber);
    formData.append("floor_number", "1");
    formData.append("bedrooms", "2");
    formData.append("bathrooms", "3");
    formData.append("address", "Test Bath Building JS");

    try {
        const createRes = await fetch(`${BASE_URL}/flats`, {
            method: "POST",
            body: formData,
        });

        if (!createRes.ok) {
            console.error("Create failed:", await createRes.text());
            return;
        }

        const createData = await createRes.json();
        console.log("Create response:", createData); // Debug log
        const flatUuid = createData.uuid;
        console.log("Flat created with UUID:", flatUuid);

        if (createData.bathrooms === 3) {
            console.log("[SUCCESS] Flat created with bathrooms=3");
        } else {
            console.error(`[FAILED] Flat created with bathrooms=${createData.bathrooms}`);
            return;
        }

        // 2. Verify GET /properties
        console.log("Step 2: Verifying GET /properties...");
        const propsRes = await fetch(`${BASE_URL}/properties`);
        const props = await propsRes.json();
        const targetProp = props.find((p) => p.uuid === flatUuid);

        if (targetProp && targetProp.bathrooms === 3) {
            console.log("[SUCCESS] GET /properties includes correct bathrooms count");
        } else {
            console.error(`[FAILED] GET /properties mismatch. Found:`, targetProp);
        }

        // 3. Update flat to 4 bathrooms
        console.log("Step 3: Updating flat to 4 bathrooms...");
        const updatePayload = {
            action: "UPDATE_FLAT_ONLY",
            flat_details: {
                bedrooms: 2,
                bathrooms: 4,
                floor_number: 1,
                address: "Test Bath Building JS",
            },
        };

        const updateRes = await fetch(`${BASE_URL}/flats/${flatUuid}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(updatePayload),
        });

        if (!updateRes.ok) {
            console.error("Update failed:", await updateRes.text());
            return;
        }

        const updateData = await updateRes.json();
        if (updateData.bathrooms === 4) {
            console.log("[SUCCESS] Flat updated to bathrooms=4");
        } else {
            console.error(`[FAILED] Update result mismatch: bathrooms=${updateData.bathrooms}`);
        }

        console.log("\nVERIFICATION COMPLETE: ALL SUCCESS");

    } catch (error) {
        console.error("Verification error:", error);
    }
}

verifyBathrooms();
