import logging
from decimal import Decimal

import requests

from upow_transactions.helpers import string_to_point, round_up_decimal
from upow_transactions.transaction_input import TransactionInput


class WalletRepository:
    def __init__(self, node_url: str) -> None:
        self.node_url = node_url

    def get_address_info(
        self,
        address: str,
        stake_outputs: bool = False,
        delegate_spent_votes: bool = False,
        delegate_unspent_votes: bool = False,
        address_state: bool = False,
        inode_registration_outputs: bool = False,
        validator_unspent_votes: bool = False,
    ):
        request = requests.get(
            f"{self.node_url}/get_address_info",
            {
                "address": address,
                "transactions_count_limit": 0,
                "show_pending": True,
                "stake_outputs": stake_outputs,
                "delegate_spent_votes": delegate_spent_votes,
                "delegate_unspent_votes": delegate_unspent_votes,
                "address_state": address_state,
                "inode_registration_outputs": inode_registration_outputs,
                "validator_unspent_votes": validator_unspent_votes,
            },
        )
        request.raise_for_status()
        result = request.json()["result"]

        return result

    def get_dobby_info(self):
        request = requests.get(f"{self.node_url}/dobby_info")
        request.raise_for_status()
        result = request.json()["result"]
        return result

    def get_address_input_from_json(self, result, address):
        pending_spent_outputs = [
            (output["tx_hash"], output["index"])
            for output in result["pending_spent_outputs"]
        ]
        tx_inputs = []
        for spendable_tx_input in result["spendable_outputs"]:
            if (
                spendable_tx_input["tx_hash"],
                spendable_tx_input["index"],
            ) in pending_spent_outputs:
                continue
            tx_input = TransactionInput(
                spendable_tx_input["tx_hash"], spendable_tx_input["index"]
            )
            tx_input.amount = Decimal(str(spendable_tx_input["amount"]))
            tx_input.public_key = string_to_point(address)
            tx_inputs.append(tx_input)
        return tx_inputs

    def get_stake_input_from_json(self, result, address):
        pending_spent_outputs = [
            (output["tx_hash"], output["index"])
            for output in result["pending_spent_outputs"]
        ]
        stake_tx_input = []
        if result["stake_outputs"]:
            for stake_tx_output in result["stake_outputs"]:
                if (
                    stake_tx_output["tx_hash"],
                    stake_tx_output["index"],
                ) in pending_spent_outputs:
                    continue
                tx_input = TransactionInput(
                    stake_tx_output["tx_hash"], stake_tx_output["index"]
                )
                tx_input.amount = Decimal(str(stake_tx_output["amount"]))
                tx_input.public_key = string_to_point(address)
                stake_tx_input.append(tx_input)
        return stake_tx_input

    def get_inode_registration_input_from_json(self, json, address):
        pending_spent_outputs = [
            (output["tx_hash"], output["index"])
            for output in json["pending_spent_outputs"]
        ]
        inode_registration_input = []
        if json["inode_registration_outputs"]:
            for inode_reg_output in json["inode_registration_outputs"]:
                if (
                    inode_reg_output["tx_hash"],
                    inode_reg_output["index"],
                ) in pending_spent_outputs:
                    continue
                tx_input = TransactionInput(
                    inode_reg_output["tx_hash"], inode_reg_output["index"]
                )
                tx_input.amount = Decimal(str(inode_reg_output["amount"]))
                tx_input.public_key = string_to_point(address)
                inode_registration_input.append(tx_input)
        return inode_registration_input

    def get_delegate_spent_votes_from_json(self, json, check_pending_txs: bool = True):
        """
        Fetches the delegate_spent_votes data from the json and converts that data in TransactionInput.

        :param check_pending_txs: This indicates that to ignore the votes if the spent votes is in pending state
        :param json: Json data of address_info
        :return: The delegate_spent_votes in List[TransactionInput] of the account.
        """
        pending_spent_outputs = (
            [
                (output["tx_hash"], output["index"])
                for output in json["pending_spent_outputs"]
            ]
            if check_pending_txs is True
            else []
        )
        delegate_vote_tx_input = []
        if json["delegate_spent_votes"]:
            for delegate_spent_vote in json["delegate_spent_votes"]:
                if (
                    delegate_spent_vote["tx_hash"],
                    delegate_spent_vote["index"],
                ) in pending_spent_outputs:
                    continue
                tx_input = TransactionInput(
                    delegate_spent_vote["tx_hash"], delegate_spent_vote["index"]
                )
                tx_input.amount = Decimal(str(delegate_spent_vote["amount"]))
                delegate_vote_tx_input.append(tx_input)
        return delegate_vote_tx_input

    def get_delegate_unspent_votes_from_json(
        self, json, address: str = None, check_pending_txs: bool = True
    ):
        """
        Fetches the delegate_unspent_votes data from the json and converts that data in TransactionInput.

        :param address: Address of delegate
        :param check_pending_txs: This indicates that to ignore the votes if the spent votes is in pending state
        :param json: Json data of address_info
        :return: The delegate_unspent_votes in List[TransactionInput] of the account.
        """
        pending_spent_outputs = (
            [
                (output["tx_hash"], output["index"])
                for output in json["pending_spent_outputs"]
            ]
            if check_pending_txs is True
            else []
        )
        delegate_vote_tx_input = []
        if json["delegate_unspent_votes"]:
            for delegate_unspent_votes in json["delegate_unspent_votes"]:
                if (
                    delegate_unspent_votes["tx_hash"],
                    delegate_unspent_votes["index"],
                ) in pending_spent_outputs:
                    continue
                tx_input = TransactionInput(
                    delegate_unspent_votes["tx_hash"], delegate_unspent_votes["index"]
                )
                tx_input.amount = Decimal(str(delegate_unspent_votes["amount"]))
                tx_input.public_key = string_to_point(address) if address else None
                delegate_vote_tx_input.append(tx_input)
        return delegate_vote_tx_input

    def get_validator_unspent_votes_from_json(
        self, json, address, check_pending_txs: bool = True
    ):
        """
        Fetches the validator_unspent_votes data from the json and converts that data in TransactionInput.

        :param address: Address of validator
        :param check_pending_txs: This indicates that to ignore the votes if the spent votes is in pending state
        :param json: Json data of address_info
        :return: The validator_unspent_votes in List[TransactionInput] of the account.
        """
        pending_spent_outputs = (
            [
                (output["tx_hash"], output["index"])
                for output in json["pending_spent_outputs"]
            ]
            if check_pending_txs is True
            else []
        )
        validator_vote_tx_input = []
        if json["validator_unspent_votes"]:
            for validator_unspent_votes in json["validator_unspent_votes"]:
                if (
                    validator_unspent_votes["tx_hash"],
                    validator_unspent_votes["index"],
                ) in pending_spent_outputs:
                    continue
                tx_input = TransactionInput(
                    validator_unspent_votes["tx_hash"], validator_unspent_votes["index"]
                )
                tx_input.amount = Decimal(str(validator_unspent_votes["amount"]))
                tx_input.public_key = string_to_point(address)
                validator_vote_tx_input.append(tx_input)
        return validator_vote_tx_input

    def get_delegates_all_power(self, json):
        delegates_unspent_votes = self.get_delegate_unspent_votes_from_json(
            json, check_pending_txs=False
        )
        delegates_spent_votes = self.get_delegate_spent_votes_from_json(
            json, check_pending_txs=False
        )
        delegates_unspent_votes.extend(delegates_spent_votes)
        assert (
            sum(delegate_votes.amount for delegate_votes in delegates_unspent_votes)
            <= 10
        )
        return delegates_unspent_votes

    def get_balance_info(self, address: str):
        """
        Fetches the account data from the node and calculates the pending balance.

        :param address: The address of the account.
        :return: The total balance and pending balance of the account.
        :raises: ConnectionError, ValueError, KeyError
        """
        try:
            # Send the request to the node
            request = requests.get(
                f"{self.node_url}/get_address_info",
                params={"address": address, "show_pending": True},
            )
            request.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

            response = request.json()
            result = response.get("result")

            if not response.get("ok"):
                logging.error(response.get("error"))
                return None, None, None, None, True

            # Handle potential missing 'result' key
            if result is None:
                logging.error("Missing 'result' key in response")
                return None, None, None, None, True

            pending_transactions = result.get("pending_transactions", [])
            spendable_outputs = result.get("spendable_outputs", [])

            # Create a set of spendable transaction hashes for easy lookup
            spendable_hashes = {output["tx_hash"] for output in spendable_outputs}

            # Ensure the balance is a string before converting to Decimal
            total_balance = Decimal(str(result["balance"]))
            pending_balance = Decimal("0")
            stake_balance = Decimal(str(result["stake"]))
            pending_stake_balance = Decimal("0")

            for transaction in pending_transactions:
                # Adjust the balance based on inputs
                for input in transaction.get("inputs", []):
                    if (
                        input.get("address") == address
                        and input.get("tx_hash") in spendable_hashes
                    ):
                        input_amount = Decimal(str(input.get("amount", "0")))
                        if any(
                            tx_output.get("type") == "UN_STAKE"
                            for tx_output in transaction.get("outputs", [])
                        ):
                            pending_balance += input_amount
                        elif transaction.get("transaction_type") == "REGULAR":
                            pending_balance -= input_amount

                # Adjust the balance based on outputs
                for output in transaction.get("outputs", []):
                    if output.get("address") == address:
                        output_amount = Decimal(str(output.get("amount", "0")))
                        if output.get("type") == "STAKE":
                            pending_stake_balance += output_amount
                        elif output.get("type") == "UN_STAKE":
                            pending_stake_balance -= output_amount
                        elif output.get("type") == "REGULAR":
                            pending_balance += output_amount

            # Format the total balance and pending balance to remove unnecessary trailing zeros
            formatted_total_balance = round_up_decimal(total_balance)
            formatted_pending_balance = round_up_decimal(pending_balance)
            formatted_pending_stake_balance = round_up_decimal(pending_stake_balance)
            formatted_stake_balance = round_up_decimal(stake_balance)

            balance_data = (
                formatted_total_balance,
                formatted_pending_balance,
                formatted_stake_balance,
                formatted_pending_stake_balance,
                False,
            )
            return balance_data

        except requests.RequestException as e:
            # Handles exceptions that occur during the request
            logging.error(f"Error during request to node: {e}")
            return None, None, None, None, True

        except ValueError as e:
            # Handles JSON decoding errors
            logging.error(f"Error decoding JSON response: {e}")
            return None, None, None, None, True

        except KeyError as e:
            # Handles missing keys in response data
            logging.error(f"Missing expected data in response: {e}")
            return None, None, None, None, True
