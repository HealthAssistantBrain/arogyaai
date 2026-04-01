import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1"

async def verify_envelope(name, url, method="GET", json=None, headers=None):
    async with httpx.AsyncClient() as client:
        try:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.post(url, json=json, headers=headers)
            
            data = resp.json()
            keys = set(data.keys())
            required = {"success", "status", "data"}
            
            if required.issubset(keys):
                print(f"[OK] {name} payload incorporates envelope core fields.")
                return True, data, resp.status_code
            else:
                print(f"[FAIL] {name} payload mismatch! Got {keys}, Expected minimum {required}. Full: {data}")
                return False, data, resp.status_code
        except Exception as e:
            print(f"[ERROR] {name} failed: {e}")
            return False, None, None

async def main():
    print("--- STARTING API CONTRACT VERIFICATION ---")
    
    # 1. Health
    await verify_envelope("Health Check", "http://localhost:8000/health")
    
    # 2. Signup
    payload = {
        "full_name": "Test Reliability User",
        "email": "reliablity_test@example.com",
        "password": "Password123!",
        "dob": "1990-01-01"
    }
    ok, data, status = await verify_envelope("Signup", f"{BASE_URL}/auth/signup", "POST", payload)
    
    if status == 409:
         # Try login if exists
         ok, data, status = await verify_envelope("Login", f"{BASE_URL}/auth/login", "POST", payload)

    token = None
    if data and data.get("data") and "access_token" in data["data"]:
        token = data["data"]["access_token"]
    
    if not token:
        print("[!] Could not get valid token to test protected endpoints.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Me
    await verify_envelope("Me", f"{BASE_URL}/users/me", "GET", headers=headers)
    
    # 4. Dashboard Profile
    await verify_envelope("Dashboard Profile", f"{BASE_URL}/user/profile", "GET", headers=headers)
    
    # 5. Prediction
    await verify_envelope("Prediction", f"{BASE_URL}/prediction/latest", "GET", headers=headers)
    
if __name__ == "__main__":
    asyncio.run(main())
