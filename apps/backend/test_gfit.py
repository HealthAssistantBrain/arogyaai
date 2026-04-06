import asyncio
import httpx
from core.security import create_access_token
from database.session import get_db
from models import User


async def main():
    db = next(get_db())
    u = db.query(User).filter(User.email == "gdrb@gmail.com").first()
    tok = create_access_token(subject=u.id)
    print("GOT TOKEN:", tok[:40])
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(
            "http://localhost:8000/api/v1/google-fit/connect/start",
            json={"timezone": "Asia/Kolkata", "redirect_path": "/device-connection"},
            headers={"Authorization": f"Bearer {tok}"},
        )
        print("STATUS:", r.status_code)
        print("BODY:", r.text[:600])


asyncio.run(main())
