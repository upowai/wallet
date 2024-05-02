from decimal import Decimal
from .constants import ENDIAN
from .helpers import InputType, sha256
from .transaction_output import TransactionOutput


class CoinbaseTransaction:
    _hex: str = None

    def __init__(self, block_hash: str, address: str, amount: Decimal):
        self.block_hash = block_hash
        self.address = address
        self.amount = amount
        self.outputs = [TransactionOutput(address, amount)]

    def hex(self):
        if self._hex is not None:
            return self._hex
        hex_inputs = (
            bytes.fromhex(self.block_hash) + (0).to_bytes(1, ENDIAN)
        ).hex() + InputType.REGULAR.value.to_bytes(1, ENDIAN).hex()
        hex_outputs = "".join(tx_output.tobytes().hex() for tx_output in self.outputs)

        if all(len(tx_output.address_bytes) == 64 for tx_output in self.outputs):
            version = 1
        elif all(len(tx_output.address_bytes) == 33 for tx_output in self.outputs):
            version = 2
        else:
            raise NotImplementedError()

        self._hex = "".join(
            [
                version.to_bytes(1, ENDIAN).hex(),
                (1).to_bytes(1, ENDIAN).hex(),
                hex_inputs,
                (len(self.outputs)).to_bytes(1, ENDIAN).hex(),
                hex_outputs,
                (36).to_bytes(1, ENDIAN).hex(),
            ]
        )

        return self._hex

    def hash(self):
        return sha256(self.hex())
