import hashlib
import json
import logging
import sys
from decimal import Decimal
from enum import Enum, IntEnum
from math import ceil
from datetime import datetime, timezone
from typing import Union

import base58
from fastecdsa.point import Point
from fastecdsa.util import mod_sqrt
from icecream import ic

from .constants import ENDIAN, CURVE, SMALLEST

_print = print

logging.basicConfig(level=logging.INFO if '--nologs' not in sys.argv else logging.WARNING)


def log(s):
    logging.getLogger('upow').info(s)


ic.configureOutput(outputFunction=log)


def get_json(obj):
    return json.loads(
        json.dumps(obj, default=lambda o: getattr(o, 'as_dict', getattr(o, '__dict__', str(o))))
    )


def timestamp():
    return int(datetime.now(timezone.utc).replace(tzinfo=timezone.utc).timestamp())


def sha256(message: Union[str, bytes]):
    if isinstance(message, str):
        message = bytes.fromhex(message)
    return hashlib.sha256(message).hexdigest()


def byte_length(i: int):
    return ceil(i.bit_length() / 8.0)


def normalize_block(block) -> dict:
    block = dict(block)
    block['address'] = block['address'].strip(' ')
    block['timestamp'] = int(block['timestamp'].replace(tzinfo=timezone.utc).timestamp())
    return block


def x_to_y(x: int, is_odd: bool = False):
    a, b, p = CURVE.a, CURVE.b, CURVE.p
    y2 = x ** 3 + a * x + b
    y_res, y_mod = mod_sqrt(y2, p)
    return y_res if y_res % 2 == is_odd else y_mod


class AddressFormat(Enum):
    FULL_HEX = 'hex'
    COMPRESSED = 'compressed'


class TransactionType(IntEnum):
    REGULAR = 0
    STAKE = 1
    UN_STAKE = 2
    INODE_REGISTRATION = 3
    INODE_DE_REGISTRATION = 4
    VALIDATOR_REGISTRATION = 5
    VOTE_AS_VALIDATOR = 6
    VOTE_AS_DELEGATE = 7
    REVOKE_AS_VALIDATOR = 8
    REVOKE_AS_DELEGATE = 9


class OutputType(IntEnum):
    REGULAR = 0
    STAKE = 1
    UN_STAKE = 2
    INODE_REGISTRATION = 3
    VALIDATOR_REGISTRATION = 5
    VOTE_AS_VALIDATOR = 6
    VOTE_AS_DELEGATE = 7
    VALIDATOR_VOTING_POWER = 8
    DELEGATE_VOTING_POWER = 9


class InputType(IntEnum):
    REGULAR = 0
    FEES = 1


def get_transaction_type_from_message(message: bytes) -> TransactionType:
    # Create a reverse mapping from string to enum value
    transaction_type_mapping = {str(item.value): item for item in TransactionType}

    try:
        # Convert bytes to string
        str_message = simple_bytes_to_string(message)

        # Convert str_message back to enum
        decoded_message = int(str_message)
        transaction_type = transaction_type_mapping.get(str(decoded_message), TransactionType.REGULAR)
    except (UnicodeDecodeError, ValueError, TypeError):
        # Handle potential decoding errors or value errors
        transaction_type = TransactionType.REGULAR

    return transaction_type


def simple_bytes_to_string(data: bytes) -> str:
    if data is None:
        return None
    try:
        # Attempt to decode bytes as hex
        return data.decode('utf-8')
    except UnicodeDecodeError:
        # If decoding as hex fails, assume it's already a string
        return data.hex()


def point_to_bytes(point: Point, address_format: AddressFormat = AddressFormat.FULL_HEX) -> bytes:
    if address_format is AddressFormat.FULL_HEX:
        return point.x.to_bytes(32, byteorder=ENDIAN) + point.y.to_bytes(32, byteorder=ENDIAN)
    elif address_format is AddressFormat.COMPRESSED:
        return string_to_bytes(point_to_string(point, AddressFormat.COMPRESSED))
    else:
        raise NotImplementedError()


def bytes_to_point(point_bytes: bytes) -> Point:
    if len(point_bytes) == 64:
        x, y = int.from_bytes(point_bytes[:32], ENDIAN), int.from_bytes(point_bytes[32:], ENDIAN)
        return Point(x, y, CURVE)
    elif len(point_bytes) == 33:
        specifier = point_bytes[0]
        x = int.from_bytes(point_bytes[1:], ENDIAN)
        return Point(x, x_to_y(x, specifier == 43))
    else:
        raise NotImplementedError()


def round_up_decimal(decimal: Decimal, round_up_length: str = '0.00000001'):
    round_up_length = Decimal(round_up_length)
    if (decimal * SMALLEST) % 1 != 0.0:
        decimal = decimal.quantize(round_up_length)
    return decimal


def bytes_to_string(point_bytes: bytes) -> str:
    point = bytes_to_point(point_bytes)
    if len(point_bytes) == 64:
        address_format = AddressFormat.FULL_HEX
    elif len(point_bytes) == 33:
        address_format = AddressFormat.COMPRESSED
    else:
        raise NotImplementedError()
    return point_to_string(point, address_format)


def point_to_string(point: Point, address_format: AddressFormat = AddressFormat.COMPRESSED) -> str:
    if address_format is AddressFormat.FULL_HEX:
        point_bytes = point_to_bytes(point)
        return point_bytes.hex()
    elif address_format is AddressFormat.COMPRESSED:
        x, y = point.x, point.y
        address = base58.b58encode((42 if y % 2 == 0 else 43).to_bytes(1, ENDIAN) + x.to_bytes(32, ENDIAN))
        return address if isinstance(address, str) else address.decode('utf-8')
    else:
        raise NotImplementedError()


def string_to_bytes(string: str) -> bytes:
    try:
        point_bytes = bytes.fromhex(string)
    except ValueError:
        point_bytes = base58.b58decode(string)
    return point_bytes


def string_to_point(string: str) -> Point:
    return bytes_to_point(string_to_bytes(string))
