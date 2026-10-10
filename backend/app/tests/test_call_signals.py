from app.models.platform import AppointmentStatus
from app.websocket.manager import call_signal_target

CLIENT = "c" * 24
LAWYER = "l" * 24


def appointment(status: str = AppointmentStatus.CONFIRMED.value) -> dict:
    return {"client_id": CLIENT, "lawyer_id": LAWYER, "status": status}


def test_client_rings_lawyer():
    assert call_signal_target(appointment(), CLIENT) == LAWYER


def test_lawyer_rings_client():
    assert call_signal_target(appointment(), LAWYER) == CLIENT


def test_missing_appointment_returns_none():
    assert call_signal_target(None, CLIENT) is None


def test_non_participant_returns_none():
    assert call_signal_target(appointment(), "x" * 24) is None


def test_non_confirmed_returns_none():
    assert call_signal_target(appointment(AppointmentStatus.PENDING.value), CLIENT) is None
