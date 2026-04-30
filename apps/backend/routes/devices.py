from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models import User
from routes.users import get_current_user_from_header
from schemas.api_models import NotificationDeviceRegistration
from services.device_registry_service import DeviceRegistryService

router = APIRouter(prefix="/api/v1/devices", tags=["Devices"])


@router.get("")
def list_devices(
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return DeviceRegistryService.list_devices(db, current_user)


@router.post("/push-subscriptions")
def register_push_subscription(
    payload: NotificationDeviceRegistration,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return DeviceRegistryService.register_push_subscription(db, current_user, payload.model_dump())


@router.delete("/push-subscriptions/current")
def unregister_current_push_subscription(
    endpoint: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return DeviceRegistryService.unregister_current_push_subscription(db, current_user, endpoint)


@router.delete("/{device_id}")
def disconnect_device(
    device_id: str,
    current_user: User = Depends(get_current_user_from_header),
    db: Session = Depends(get_db),
):
    return DeviceRegistryService.disconnect_device(db, current_user, device_id)
