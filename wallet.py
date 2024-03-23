import argparse
import asyncio
import logging
import os
import sys

import pickledb
import requests
from fastecdsa import keys, curve

from upow_transactions.constants import CURVE
from upow_transactions.helpers import point_to_string, sha256
from utils import Utils

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, dir_path + "/../..")


async def main():
    parser = argparse.ArgumentParser(description="UPOW wallet")
    parser.add_argument(
        "command",
        metavar="command",
        type=str,
        help="action to do with the wallet",
        choices=[
            "createwallet",
            "send",
            "balance",
            "stake",
            "unstake",
            "register_inode",
            "de_register_inode",
            "register_validator",
            "vote",
            "revoke",
        ],
    )
    parser.add_argument("-to", metavar="recipient", type=str, required=False)
    parser.add_argument("-a", metavar="amount", type=str, required=False)
    parser.add_argument(
        "-m", metavar="message", type=str, dest="message", required=False
    )
    parser.add_argument("-r", metavar="range", type=str, dest="range", required=False)
    parser.add_argument(
        "-from", metavar="revoke_from", type=str, dest="revoke_from", required=False
    )

    args = parser.parse_args()
    db = pickledb.load(f"{dir_path}/key_pair_list.json", True)
    wallet_utils: Utils = Utils()

    command = args.command

    if command == "createwallet":
        key_list = db.get("keys") or []
        private_key = keys.gen_private_key(CURVE)
        public_key = keys.get_public_key(private_key, curve.P256)
        address = point_to_string(public_key)
        key_list.append({"private_key": private_key, "public_key": address})
        db.set("keys", key_list)

        print(f"Private key: {hex(private_key)}\nAddress: {address}")
    elif command == "balance":
        key_pair_list = db.get("keys") or []
        total_balance = 0
        total_pending_balance = 0
        for key_pair in key_pair_list:
            public_key = keys.get_public_key(key_pair["private_key"], curve.P256)
            address = point_to_string(public_key)

            balance, pending_balance, stake, pending_stake, is_error = (
                wallet_utils.get_balance_info(address)
            )
            if is_error:
                break
            total_balance += balance
            total_pending_balance += pending_balance

            print(
                f'\nAddress: {address}\nPrivate key: {hex(key_pair["private_key"])}'
                f'\nBalance: {balance}{f" ({pending_balance} pending)" if pending_balance != 0 else ""}'
                f'\nStake: {stake}{f" ({pending_stake} pending)" if pending_stake != 0 else ""}'
            )
        print(
            f'\nTotal Balance: {total_balance}{f" ({total_pending_balance} pending)" if total_pending_balance != 0 else ""}'
        )
    elif command == "send":
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "command", metavar="command", type=str, help="action to do with the wallet"
        )
        parser.add_argument(
            "-to", metavar="recipient", type=str, dest="recipient", required=True
        )
        parser.add_argument(
            "-a", metavar="amount", type=str, dest="amount", required=True
        )
        parser.add_argument(
            "-m", metavar="message", type=str, dest="message", required=False
        )

        args = parser.parse_args()
        recipients = args.recipient.split(",")
        amounts = args.amount.split(",")
        message = args.message

        if len(recipients) > 1 and len(amounts) > 1 and len(recipients) == len(amounts):
            selected_private_key = await select_key(db)
            tx = await wallet_utils.create_transaction_to_send_multiple_wallet(
                selected_private_key, recipients, amounts, string_to_bytes(message)
            )
        else:
            receiver = recipients[0]
            amount = amounts[0]
            selected_private_key = await select_key(db)
            tx = await wallet_utils.create_transaction(
                selected_private_key, receiver, amount, string_to_bytes(message)
            )

        await push_tx(tx, wallet_utils)

    elif command == "stake":
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "command", metavar="command", type=str, help="action to do with the wallet"
        )
        parser.add_argument(
            "-a", metavar="amount", type=str, dest="amount", required=True
        )

        args = parser.parse_args()
        amount = args.amount

        selected_private_key = await select_key(db)

        tx = await wallet_utils.create_stake_transaction(selected_private_key, amount)
        await push_tx(tx, wallet_utils)

    elif command == "unstake":
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "command", metavar="command", type=str, help="action to do with the wallet"
        )

        selected_private_key = await select_key(db)
        tx = await wallet_utils.create_unstake_transaction(selected_private_key)
        await push_tx(tx, wallet_utils)

    elif command == "register_inode":
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "command", metavar="command", type=str, help="action to do with the wallet"
        )

        selected_private_key = await select_key(db)
        tx = await wallet_utils.create_inode_registration_transaction(
            selected_private_key
        )
        await push_tx(tx, wallet_utils)

    elif command == "de_register_inode":
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "command", metavar="command", type=str, help="action to do with the wallet"
        )
        selected_private_key = await select_key(db)
        tx = await wallet_utils.create_inode_de_registration_transaction(
            selected_private_key
        )
        await push_tx(tx, wallet_utils)

    elif command == "register_validator":
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "command", metavar="command", type=str, help="action to do with the wallet"
        )

        selected_private_key = await select_key(db)
        tx = await wallet_utils.create_validator_registration_transaction(
            selected_private_key
        )
        await push_tx(tx, wallet_utils)

    elif command == "vote":
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "command", metavar="command", type=str, help="action to do with the wallet"
        )
        parser.add_argument(
            "-r", metavar="range", type=str, dest="range", required=True
        )
        parser.add_argument(
            "-to", metavar="recipient", type=str, dest="recipient", required=True
        )
        args = parser.parse_args()
        voting_range = args.range
        recipient = args.recipient

        selected_private_key = await select_key(db)
        tx = await wallet_utils.create_voting_transaction(
            selected_private_key, voting_range, recipient
        )
        await push_tx(tx, wallet_utils)

    elif command == 'revoke':
        parser = argparse.ArgumentParser()
        parser.add_argument('command', metavar='command', type=str, help='action to do with the wallet')
        parser.add_argument('-from', metavar='revoke_from', type=str, dest='revoke_from', required=True)
        args = parser.parse_args()
        revoke_from = args.revoke_from
        selected_private_key = await select_key(db)
        tx = await wallet_utils.create_revoke_transaction(selected_private_key, revoke_from)
        await push_tx(tx, wallet_utils)


async def push_tx(tx, wallet_utils: Utils):
    try:
        r = requests.get(
            f"{wallet_utils.NODE_URL}/push_tx", {"tx_hex": tx.hex()}, timeout=10
        )
        r.raise_for_status()
        res = r.json()
        if res["ok"]:
            print(f"Transaction pushed. Transaction hash: {sha256(tx.hex())}")
        else:
            logging.error("\nTransaction has not been pushed")
    except Exception as e:
        logging.error(f"Error during request to node: {e}")


async def push_tx_request(tx):
    r = requests.get("https://upow.network/push_tx", {"tx_hex": tx.hex()}, timeout=10)
    res = r.json()
    if res["ok"]:
        print(f"Transaction pushed. Transaction hash: {sha256(tx.hex())}")
    else:
        logging.error("\nTransaction has not been added")


async def select_key(db):
    selected_private_key = None
    if db.get("keys") is False:
        raise Exception("No key. please create key")

    if len(db.get("keys")) > 1:
        print("Keys: ", end="\n")
        for i, key_pair in enumerate(db.get("keys")):
            print(i, key_pair["public_key"], end="\n")
        try:
            user_input = int(input("Select key: "))
            if user_input >= len(db.get("keys")):
                raise Exception("Invalid input. Please enter a correct key number.")
            selected_private_key = db.get("keys")[user_input]["private_key"]
        except ValueError:
            raise Exception("Invalid input. Please enter a valid integer.")
    else:
        selected_private_key = db.get("keys")[0]["private_key"]
    return selected_private_key


def string_to_bytes(string: str) -> bytes:
    if string is None:
        return None
    try:
        return bytes.fromhex(string)
    except ValueError:
        return string.encode("utf-8")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
