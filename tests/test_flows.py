import pytest

from termix_platform_sdk.flows import Flows

FAST = {"timeout_s": 2.0, "interval_s": 0.01}


def intent(action):
    return {
        "id": f"i-{action}",
        "action": action,
        "chainId": 56,
        "contract": "0x00000000000000000000000000000000000000ee",
        "callData": "0xdeadbeef",
        "value": "0",
        "status": "PREPARED",
        "nonceKey": f"k-{action}",
    }


class MockSigner:
    def __init__(self, with_receipt=False):
        self.events = []
        self._n = 0
        self._with_receipt = with_receipt

    async def get_address(self):
        return "0x00000000000000000000000000000000000000a1"

    async def sign_message(self, m):
        return "0xsig"

    async def send_transaction(self, tx):
        self._n += 1
        h = f"0x{'d' * 62}{self._n:02d}"
        self.events.append(f"send:{h}")
        return h

    if True:
        async def wait_for_receipt(self, tx_hash, chain_id):
            self.events.append(f"receipt:{tx_hash}")


class FakeCheckout:
    def __init__(self, order_states):
        self.order_states = order_states
        self.intent_order = []

    async def tx_intent(self, cid, action="createOrder"):
        self.intent_order.append(action)
        return intent(action)

    async def confirm(self, cid, tx_hash):
        return {"ok": True}

    async def get(self, cid):
        return {"id": cid, "amount": "10", "currency": "USDC", "status": "CONFIRMED", "orderId": "o1"}


class FakeOrders:
    def __init__(self, states):
        self._states = states

    async def get(self, oid):
        return self._states.pop(0) if len(self._states) > 1 else self._states[0]


class FakeClient:
    def __init__(self, signer=None):
        self.signer = signer
        self.checkout = FakeCheckout([])
        self.orders = FakeOrders([
            {"id": "o1", "status": "PENDING_ACCEPT", "budget": "10", "currency": "USDC"},
            {"id": "o1", "status": "SETTLED", "budget": "10", "currency": "USDC"},
        ])


@pytest.mark.asyncio
async def test_complete_checkout_mode_b_waits_for_approve_receipt():
    signer = MockSigner(with_receipt=True)
    client = FakeClient(signer)
    flows = Flows(client)
    res = await flows.complete_checkout("c1", auto_sign=True, wait=FAST)
    assert len(res["tx_hashes"]) == 2
    assert res["result"]["id"] == "o1"
    # approve intent requested before createOrder intent
    assert client.checkout.intent_order.index("approveEscrow") < client.checkout.intent_order.index("createOrder")
    # the approve receipt was awaited before the second send
    send_idxs = [i for i, e in enumerate(signer.events) if e.startswith("send:")]
    receipt_idx = next(i for i, e in enumerate(signer.events) if e.startswith("receipt:"))
    assert send_idxs[0] < receipt_idx < send_idxs[1]


@pytest.mark.asyncio
async def test_complete_checkout_mode_a_returns_intents():
    client = FakeClient(signer=None)
    flows = Flows(client)
    res = await flows.complete_checkout("c1")
    assert len(res["intents"]) == 2
    assert res["tx_hashes"] == []


@pytest.mark.asyncio
async def test_register_agent_rejects_taken_handle():
    class Agents:
        async def name_availability(self, name):
            return {"available": False}

    class C:
        signer = MockSigner()
        agents = Agents()

    with pytest.raises(ValueError, match="not available"):
        await Flows(C()).register_agent("taken", auto_sign=True)
