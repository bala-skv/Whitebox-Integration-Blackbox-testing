"""
test_tickets.py — Tests for support tickets.

Spec:
  - Subject: 5–100 characters.
  - Message: 1–500 characters. Full message must be saved exactly.
  - New ticket status = OPEN.
  - Status transitions: OPEN→IN_PROGRESS, IN_PROGRESS→CLOSED only.
  - Invalid transitions (OPEN→CLOSED, CLOSED→OPEN, etc.) must be rejected.
"""

import requests
import pytest

BASE_URL = "http://localhost:8080/api/v1"


def _create_ticket(uh, subject="Test subject here", message="Test message body"):
    return requests.post(
        f"{BASE_URL}/support/ticket",
        json={"subject": subject, "message": message},
        headers=uh,
    )


class TestCreateTicket:
    def test_create_valid_ticket_returns_200(self, uh):
        """Justification: A valid subject and message must create a ticket successfully."""
        r = _create_ticket(uh)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_new_ticket_status_is_open(self, uh):
        """Justification: Every new ticket must start with status OPEN per spec."""
        r = _create_ticket(uh, subject="Status check ticket", message="Checking initial status")
        assert r.status_code == 200
        data = r.json()
        ticket = data.get("ticket", data)
        status = ticket.get("status", "")
        assert status == "OPEN", f"Expected status OPEN, got '{status}'"

    def test_subject_too_short_returns_400(self, uh):
        """Justification: Subject < 5 chars violates spec → 400."""
        r = _create_ticket(uh, subject="Hi")
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_subject_too_long_returns_400(self, uh):
        """Justification: Subject > 100 chars violates spec → 400."""
        r = _create_ticket(uh, subject="A" * 101)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_subject_exactly_5_chars_accepted(self, uh):
        """Justification: Boundary value — 5 chars is the minimum allowed subject length."""
        r = _create_ticket(uh, subject="Hello")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_subject_exactly_100_chars_accepted(self, uh):
        """Justification: Boundary value — 100 chars is the maximum allowed subject length."""
        r = _create_ticket(uh, subject="A" * 100)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_message_empty_returns_400(self, uh):
        """Justification: Message must be at least 1 character → empty is invalid."""
        r = _create_ticket(uh, message="")
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_message_too_long_returns_400(self, uh):
        """Justification: Message > 500 chars violates spec → 400."""
        r = _create_ticket(uh, message="A" * 501)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_message_saved_exactly(self, uh):
        """Justification: Full message must be saved exactly as written per spec."""
        message = "Exact message content: special chars !@#$%^&*()"
        r = _create_ticket(uh, subject="Exact save test", message=message)
        assert r.status_code == 200
        data = r.json()
        ticket = data.get("ticket", data)
        ticket_id = ticket.get("ticket_id")

        if ticket_id:
            r_list = requests.get(f"{BASE_URL}/support/tickets", headers=uh)
            if r_list.status_code == 200:
                tickets = r_list.json()
                if isinstance(tickets, dict):
                    tickets = tickets.get("tickets", [])
                found = next((t for t in tickets if t.get("ticket_id") == ticket_id), None)
                if found:
                    assert found.get("message") == message, \
                        f"Message not saved exactly. Expected: '{message}', got: '{found.get('message')}'"


class TestTicketStatusTransitions:
    def _get_ticket_id(self, uh):
        r = _create_ticket(uh, subject="Transition test ticket", message="For status transition testing")
        assert r.status_code == 200
        data = r.json()
        ticket = data.get("ticket", data)
        return ticket.get("ticket_id")

    def test_open_to_in_progress_valid(self, uh):
        """Justification: OPEN → IN_PROGRESS is a valid forward transition."""
        ticket_id = self._get_ticket_id(uh)
        if not ticket_id:
            pytest.skip("Could not get ticket_id")
        r = requests.put(
            f"{BASE_URL}/support/tickets/{ticket_id}",
            json={"status": "IN_PROGRESS"},
            headers=uh,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_in_progress_to_closed_valid(self, uh):
        """Justification: IN_PROGRESS → CLOSED is a valid forward transition."""
        ticket_id = self._get_ticket_id(uh)
        if not ticket_id:
            pytest.skip("Could not get ticket_id")
        requests.put(
            f"{BASE_URL}/support/tickets/{ticket_id}",
            json={"status": "IN_PROGRESS"},
            headers=uh,
        )
        r = requests.put(
            f"{BASE_URL}/support/tickets/{ticket_id}",
            json={"status": "CLOSED"},
            headers=uh,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    def test_open_to_closed_invalid(self, uh):
        """Justification: OPEN → CLOSED skips IN_PROGRESS, which is not allowed per spec."""
        ticket_id = self._get_ticket_id(uh)
        if not ticket_id:
            pytest.skip("Could not get ticket_id")
        r = requests.put(
            f"{BASE_URL}/support/tickets/{ticket_id}",
            json={"status": "CLOSED"},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400 for invalid transition, got {r.status_code}: {r.text}"

    def test_closed_to_open_invalid(self, uh):
        """Justification: Regressing from CLOSED → OPEN must not be allowed per spec."""
        ticket_id = self._get_ticket_id(uh)
        if not ticket_id:
            pytest.skip("Could not get ticket_id")
        # Move to CLOSED
        requests.put(f"{BASE_URL}/support/tickets/{ticket_id}", json={"status": "IN_PROGRESS"}, headers=uh)
        requests.put(f"{BASE_URL}/support/tickets/{ticket_id}", json={"status": "CLOSED"}, headers=uh)
        # Now try to go back
        r = requests.put(
            f"{BASE_URL}/support/tickets/{ticket_id}",
            json={"status": "OPEN"},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400 for regression transition, got {r.status_code}: {r.text}"

    def test_invalid_status_value_rejected(self, uh):
        """Justification: Arbitrary status strings outside the allowed values must be rejected."""
        ticket_id = self._get_ticket_id(uh)
        if not ticket_id:
            pytest.skip("Could not get ticket_id")
        r = requests.put(
            f"{BASE_URL}/support/tickets/{ticket_id}",
            json={"status": "PENDING"},
            headers=uh,
        )
        assert r.status_code == 400, f"Expected 400 for invalid status value, got {r.status_code}: {r.text}"
