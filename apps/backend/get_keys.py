from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization
import base64

v = Vapid()
v.generate_keys()

public_key = v.public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

private_key = v.private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

print("PUBLIC_KEY:", base64.urlsafe_b64encode(public_key).decode())
print("PRIVATE_KEY:", base64.urlsafe_b64encode(private_key).decode())
