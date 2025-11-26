import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000/api/v1"
EMAIL = "teste@gmail.com"
PASSWORD = "teste123"

async def test_qr_flow():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login
        print("1. Logging in...")
        try:
            resp = await client.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
            if resp.status_code != 200:
                print(f"Login failed: {resp.status_code} {resp.text}")
                return
            data = resp.json()
            token = data["tokens"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("Login successful.")
        except Exception as e:
            print(f"Login error: {e}")
            return

        # 2. Create Chip
        print("2. Creating test chip...")
        import time
        chip_alias = f"Test QR Chip Auto {int(time.time())} v2"
        resp = await client.post(f"{BASE_URL}/chips", json={"alias": chip_alias}, headers=headers)
        if resp.status_code != 201:
            print(f"Create chip failed: {resp.status_code} {resp.text}")
            return
        chip_data = resp.json()
        chip_id = chip_data["id"]
        print(f"Chip created: {chip_id}")

        # 3. Poll for QR Code
        print("3. Polling for QR Code (max 20 attempts)...")
        for i in range(20):
            try:
                resp = await client.get(f"{BASE_URL}/chips/{chip_id}/qr", headers=headers)
                if resp.status_code != 200:
                    print(f"Poll {i+1}: Error {resp.status_code} {resp.text}")
                    await asyncio.sleep(2)
                    continue
                
                data = resp.json()
                status = data.get("status")
                qr = data.get("qr_code") or data.get("qr")
                
                print(f"Poll {i+1}: Status={status}, Has QR={bool(qr)}")
                
                if qr and str(qr).startswith("data:image/png;base64"):
                    print("\nSUCCESS: Valid QR Code image received!")
                    print(f"QR Data length: {len(qr)} chars")
                    print(f"Starts with: {qr[:50]}...")
                    
                    # Cleanup
                    print("\n4. Deleting test chip...")
                    await client.delete(f"{BASE_URL}/chips/{chip_id}", headers=headers)
                    return
                
                if status == "CONNECTED":
                     print("\nChip connected before QR (unexpected but possible if session reused).")
                     await client.delete(f"{BASE_URL}/chips/{chip_id}", headers=headers)
                     return

            except Exception as e:
                print(f"Poll error: {e}")
            
            await asyncio.sleep(3)

        print("\nFAILURE: Timed out waiting for QR code.")
        # Cleanup
        await client.delete(f"{BASE_URL}/chips/{chip_id}", headers=headers)

if __name__ == "__main__":
    asyncio.run(test_qr_flow())

