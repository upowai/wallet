from decimal import Decimal
from io import BytesIO
from typing import List

from fastecdsa import keys
from icecream import ic

from .coinbase_transaction import CoinbaseTransaction
from .constants import ENDIAN, SMALLEST, CURVE
from .helpers import (
    get_transaction_type_from_message,
    sha256,
    TransactionType,
    OutputType,
    bytes_to_string,
    point_to_string,
    InputType,
)
from .transaction_input import TransactionInput
from .transaction_output import TransactionOutput

print = ic


class Transaction:
    def __init__(
        self,
        inputs: List[TransactionInput],
        outputs: List[TransactionOutput],
        message: bytes = None,
        version: int = None,
    ):
        if len(inputs) >= 256:
            raise Exception(
                f"You can spend max 255 inputs in a single transactions, not {len(inputs)}"
            )
        if len(outputs) >= 256:
            raise Exception(
                f"You can have max 255 outputs in a single transactions, not {len(outputs)}"
            )
        self.inputs = inputs
        self.outputs = outputs
        self.message = message
        self.transaction_type = get_transaction_type_from_message(message)
        if version is None:
            if all(len(tx_output.address_bytes) == 64 for tx_output in outputs):
                version = 1
            elif all(len(tx_output.address_bytes) == 33 for tx_output in outputs):
                version = 3
            else:
                raise NotImplementedError()
        if version > 3:
            raise NotImplementedError()
        self.version = version
        self._hex: str = None
        self.fees: Decimal = None
        self.tx_hash: str = None

    def hex(self, full: bool = True):
        inputs, outputs = self.inputs, self.outputs
        hex_inputs = "".join(tx_input.tobytes().hex() for tx_input in inputs)
        hex_outputs = "".join(tx_output.tobytes().hex() for tx_output in outputs)

        version = self.version

        self._hex = "".join(
            [
                version.to_bytes(1, ENDIAN).hex(),
                len(inputs).to_bytes(1, ENDIAN).hex(),
                hex_inputs,
                (len(outputs)).to_bytes(1, ENDIAN).hex(),
                hex_outputs,
            ]
        )

        if not full and (version <= 2 or self.message is None):
            return self._hex

        if self.message is not None:
            if version <= 2:
                self._hex += bytes([1, len(self.message)]).hex()
            else:
                self._hex += bytes([1]).hex()
                self._hex += (len(self.message)).to_bytes(2, ENDIAN).hex()
            self._hex += self.message.hex()
            if not full:
                return self._hex
        else:
            self._hex += (0).to_bytes(1, ENDIAN).hex()

        signatures = []
        for tx_input in inputs:
            signed = tx_input.get_signature()
            if signed not in signatures:
                signatures.append(signed)
                self._hex += signed

        return self._hex

    def hash(self):
        if self.tx_hash is None:
            self.tx_hash = sha256(self.hex())
        return self.tx_hash

    def _verify_double_spend_same_transaction(self):
        used_inputs = []
        for tx_input in self.inputs:
            input_hash = f"{tx_input.tx_hash}{tx_input.index}"
            if input_hash in used_inputs:
                return False
            used_inputs.append(input_hash)
        return True

    async def _check_signature(self):
        tx_hex = self.hex(False)
        checked_signatures = []
        for tx_input in self.inputs:
            if tx_input.signed is None:
                print("not signed")
                return False
            await tx_input.get_public_key()
            signature = (tx_input.public_key, tx_input.signed)
            if signature in checked_signatures:
                continue
            if not await tx_input.verify(tx_hex):
                print("signature not valid")
                return False
            checked_signatures.append(signature)
        return True

    def sign(self, private_keys: list = []):
        for private_key in private_keys:
            for input in self.inputs:
                if input.private_key is None and (
                    input.public_key or input.transaction
                ):
                    public_key = keys.get_public_key(private_key, CURVE)
                    input_public_key = (
                        input.public_key
                        or input.transaction.outputs[input.index].public_key
                    )
                    if public_key == input_public_key:
                        input.private_key = private_key
        for input in self.inputs:
            if input.private_key is not None:
                input.sign(self.hex(False))
        return self

    @staticmethod
    async def from_hex(hexstring: str, check_signatures: bool = True):
        tx_bytes = BytesIO(bytes.fromhex(hexstring))
        version = int.from_bytes(tx_bytes.read(1), ENDIAN)
        if version > 3:
            raise NotImplementedError()

        inputs_count = int.from_bytes(tx_bytes.read(1), ENDIAN)

        inputs = []

        for i in range(0, inputs_count):
            tx_hex = tx_bytes.read(32).hex()
            tx_index = int.from_bytes(tx_bytes.read(1), ENDIAN)
            input_type = int.from_bytes(tx_bytes.read(1), ENDIAN)
            inputs.append(
                TransactionInput(
                    tx_hex, index=tx_index, input_type=InputType(input_type)
                )
            )

        outputs_count = int.from_bytes(tx_bytes.read(1), ENDIAN)

        outputs = []

        for i in range(0, outputs_count):
            pubkey = tx_bytes.read(64 if version == 1 else 33)
            amount_length = int.from_bytes(tx_bytes.read(1), ENDIAN)
            amount = int.from_bytes(tx_bytes.read(amount_length), ENDIAN) / Decimal(
                SMALLEST
            )
            transaction_type = int.from_bytes(tx_bytes.read(1), ENDIAN)
            outputs.append(
                TransactionOutput(
                    bytes_to_string(pubkey), amount, OutputType(transaction_type)
                )
            )

        specifier = int.from_bytes(tx_bytes.read(1), ENDIAN)
        if specifier == 36:
            # assert len(inputs) == 1 and len(outputs) == 1
            assert len(inputs) == 1
            coinbase_transaction = CoinbaseTransaction(
                inputs[0].tx_hash, outputs[0].address, outputs[0].amount
            )
            if len(outputs) > 1:
                coinbase_transaction.outputs.extend(outputs[1:])
            return coinbase_transaction
        else:
            if specifier == 1:
                message_length = int.from_bytes(
                    tx_bytes.read(1 if version <= 2 else 2), ENDIAN
                )
                message = tx_bytes.read(message_length)
            else:
                message = None
                assert specifier == 0

            signatures = []

            while True:
                signed = (
                    int.from_bytes(tx_bytes.read(32), ENDIAN),
                    int.from_bytes(tx_bytes.read(32), ENDIAN),
                )
                if signed[0] == 0:
                    break
                signatures.append(signed)

            if len(signatures) == 1:
                for tx_input in inputs:
                    tx_input.signed = signatures[0]
            elif len(inputs) == len(signatures):
                for i, tx_input in enumerate(inputs):
                    tx_input.signed = signatures[i]
            else:
                if not check_signatures:
                    return Transaction(inputs, outputs, message, version)
                index = {}
                for tx_input in inputs:
                    public_key = point_to_string(await tx_input.get_public_key())
                    if public_key not in index.keys():
                        index[public_key] = []
                    index[public_key].append(tx_input)

                for i, signed in enumerate(signatures):
                    for tx_input in index[list(index.keys())[i]]:
                        tx_input.signed = signed

            return Transaction(inputs, outputs, message, version)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.hex() == other.hex()
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)
