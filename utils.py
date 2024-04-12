from decimal import Decimal

from fastecdsa import keys

from repository import WalletRepository
from upow_transactions.constants import CURVE, MAX_INODES
from upow_transactions.helpers import (
    point_to_string,
    OutputType,
    TransactionType,
)
from upow_transactions.transaction import Transaction
from upow_transactions.transaction_output import TransactionOutput


class Utils:
    NODE_URL = "https://api.upow.ai"

    def __init__(self) -> None:
        self.repo = WalletRepository(self.NODE_URL)

    def get_balance_info(self, address: str):
        result = self.repo.get_balance_info(address)
        return result

    async def create_transaction(
        self,
        private_key,
        receiving_address,
        amount,
        message: bytes = None,
        send_back_address=None,
    ):
        amount = Decimal(amount)
        inputs = []
        sender_address = point_to_string(keys.get_public_key(private_key, CURVE))
        if send_back_address is None:
            send_back_address = sender_address

        r_json = self.repo.get_address_info(sender_address)
        address_inputs = self.repo.get_address_input_from_json(
            r_json, address=sender_address
        )
        inputs.extend(address_inputs)
        if not inputs:
            raise Exception("No spendable outputs")

        if sum(input.amount for input in inputs) < amount:
            raise Exception(f"Error: You don't have enough funds")

        transaction_inputs = self.select_transaction_input(inputs, amount)

        transaction_amount = sum(input.amount for input in transaction_inputs)

        transaction = Transaction(
            transaction_inputs,
            [TransactionOutput(receiving_address, amount=amount)],
            message,
        )
        if transaction_amount > amount:
            transaction.outputs.append(
                TransactionOutput(send_back_address, transaction_amount - amount)
            )

        transaction.sign([private_key])

        return transaction

    async def create_transaction_to_send_multiple_wallet(
        self,
        private_key,
        receiving_addresses,
        amounts,
        message: bytes = None,
        send_back_address=None,
    ):
        if len(receiving_addresses) != len(amounts):
            raise Exception(
                "Receiving addresses length is different from amounts length"
            )
        amounts = [Decimal(amount) for amount in amounts]
        total_amount = sum(amounts)
        total_amount = Decimal(total_amount)
        inputs = []
        sender_address = point_to_string(keys.get_public_key(private_key, CURVE))
        if send_back_address is None:
            send_back_address = sender_address

        r_json = self.repo.get_address_info(sender_address)
        address_inputs = self.repo.get_address_input_from_json(
            r_json, address=sender_address
        )
        inputs.extend(address_inputs)

        if not inputs:
            raise Exception("No spendable outputs")

        total_input_amount = sum(input.amount for input in inputs)

        if total_input_amount < total_amount:
            raise Exception(f"Error: You don't have enough funds")

        transaction_inputs = []
        transaction_outputs = []

        # Select inputs to cover the total amount
        input_amount = Decimal(0)
        for tx_input in sorted(inputs, key=lambda item: item.amount, reverse=True):
            transaction_inputs.append(tx_input)
            input_amount += tx_input.amount
            if input_amount >= total_amount:
                break

        # Create outputs for each receiving address
        for receiving_address, amount in zip(receiving_addresses, amounts):
            transaction_outputs.append(
                TransactionOutput(receiving_address, amount=Decimal(amount))
            )

        # If there's change, add an output back to the sender
        change_amount = input_amount - total_amount
        if change_amount > 0:
            transaction_outputs.append(
                TransactionOutput(send_back_address, amount=change_amount)
            )

        transaction = Transaction(transaction_inputs, transaction_outputs, message)
        transaction.sign([private_key])

        return transaction

    async def create_stake_transaction(
        self, private_key, amount, send_back_address=None
    ):
        amount = Decimal(amount)
        inputs = []

        sender_address = point_to_string(keys.get_public_key(private_key, CURVE))
        if send_back_address is None:
            send_back_address = sender_address

        result_json = self.repo.get_address_info(
            sender_address,
            stake_outputs=True,
            delegate_unspent_votes=True,
            delegate_spent_votes=True,
        )
        inputs.extend(
            self.repo.get_address_input_from_json(result_json, address=sender_address)
        )

        if not inputs:
            raise Exception("No spendable outputs")

        if sum(input.amount for input in inputs) < amount:
            raise Exception(f"Error: You don't have enough funds")

        stake_inputs = self.repo.get_stake_input_from_json(
            result_json, address=sender_address, check_pending_txs=False
        )
        if stake_inputs:
            raise Exception("Already staked")

        transaction_inputs = []

        for tx_input in sorted(inputs, key=lambda item: item.amount):
            if tx_input.amount >= amount:
                transaction_inputs.append(tx_input)
                break
        for tx_input in sorted(inputs, key=lambda item: item.amount, reverse=True):
            if sum(input.amount for input in transaction_inputs) >= amount:
                break
            transaction_inputs.append(tx_input)

        transaction_amount = sum(input.amount for input in transaction_inputs)

        transaction = Transaction(
            transaction_inputs,
            [
                TransactionOutput(
                    sender_address, amount=amount, transaction_type=OutputType.STAKE
                )
            ],
        )

        if transaction_amount > amount:
            transaction.outputs.append(
                TransactionOutput(send_back_address, transaction_amount - amount)
            )

        if not self.repo.get_delegates_all_power(result_json):
            voting_power = Decimal(10)
            transaction.outputs.append(
                TransactionOutput(
                    sender_address,
                    voting_power,
                    transaction_type=OutputType.DELEGATE_VOTING_POWER,
                )
            )

        transaction.sign([private_key])

        return transaction

    async def create_unstake_transaction(self, private_key):
        sender_address = point_to_string(keys.get_public_key(private_key, CURVE))
        result_json = self.repo.get_address_info(sender_address, stake_outputs=True, delegate_spent_votes=True)
        stake_inputs = self.repo.get_stake_input_from_json(
            result_json, address=sender_address
        )
        if not stake_inputs:
            raise Exception(f"Error: There is nothing staked")
        amount = stake_inputs[0].amount

        if self.repo.get_delegate_spent_votes_from_json(
            result_json, check_pending_txs=False
        ):
            raise Exception("Kindly release the votes.")

        pending_vote_tx = self.repo.get_pending_vote_as_delegate_transaction_from_json(sender_address, result_json)
        if pending_vote_tx:
            raise Exception('Kindly release the votes. Vote transaction is in pending')

        transaction = Transaction(
            [stake_inputs[0]],
            [
                TransactionOutput(
                    sender_address, amount=amount, transaction_type=OutputType.UN_STAKE
                )
            ],
        )
        transaction.sign([private_key])
        return transaction

    async def create_inode_registration_transaction(self, private_key):
        amount = Decimal(1000)
        inputs = []
        address = point_to_string(keys.get_public_key(private_key, CURVE))

        result_json = self.repo.get_address_info(
            address, stake_outputs=True, address_state=True
        )
        inputs.extend(
            self.repo.get_address_input_from_json(result_json, address=address)
        )

        if not inputs:
            raise Exception("No spendable outputs")

        if sum(input.amount for input in inputs) < amount:
            raise Exception(f"Error: You don't have enough funds")

        stake_inputs = self.repo.get_stake_input_from_json(result_json, address=address)
        if not stake_inputs:
            raise Exception(f"You are not a delegate. Become a delegate by staking.")

        is_inode_registered = result_json["is_inode"]
        if is_inode_registered:
            raise Exception(f"This address is already registered as inode.")

        is_validator_registered = result_json["is_validator"]
        if is_validator_registered:
            raise Exception(
                f"This address is registered as validator and a validator cannot be an inode."
            )

        inode_addresses = self.repo.get_dobby_info()
        if len(inode_addresses) >= MAX_INODES:
            raise Exception(f"{MAX_INODES} inodes are already registered.")

        transaction_inputs = []

        for tx_input in sorted(inputs, key=lambda item: item.amount):
            if tx_input.amount >= amount:
                transaction_inputs.append(tx_input)
                break
        for tx_input in sorted(inputs, key=lambda item: item.amount, reverse=True):
            if sum(input.amount for input in transaction_inputs) >= amount:
                break
            transaction_inputs.append(tx_input)

        transaction_amount = sum(input.amount for input in transaction_inputs)

        transaction = Transaction(
            transaction_inputs,
            [
                TransactionOutput(
                    address,
                    amount=amount,
                    transaction_type=OutputType.INODE_REGISTRATION,
                )
            ],
        )
        if transaction_amount > amount:
            transaction.outputs.append(
                TransactionOutput(address, transaction_amount - amount)
            )

        transaction.sign([private_key])
        return transaction

    async def create_inode_de_registration_transaction(self, private_key):
        inputs = []
        address = point_to_string(keys.get_public_key(private_key, CURVE))

        result_json = self.repo.get_address_info(
            address, inode_registration_outputs=True
        )
        inputs.extend(
            self.repo.get_inode_registration_input_from_json(
                result_json, address=address
            )
        )

        if not inputs:
            raise Exception("This address is not registered as an inode.")

        active_inode_addresses = self.repo.get_dobby_info()
        is_inode_active = any(
            entry.get("wallet") == address for entry in active_inode_addresses
        )
        if is_inode_active:
            raise Exception("This address is an active inode. Cannot de-register.")

        amount = inputs[0].amount
        message = self.string_to_bytes(str(TransactionType.INODE_DE_REGISTRATION.value))
        transaction = Transaction(
            inputs, [TransactionOutput(address, amount=amount)], message
        )
        transaction.sign([private_key])
        return transaction

    async def create_validator_registration_transaction(self, private_key):
        amount = Decimal(100)
        inputs = []
        address = point_to_string(keys.get_public_key(private_key, CURVE))
        result_json = self.repo.get_address_info(
            address, stake_outputs=True, address_state=True
        )
        inputs.extend(
            self.repo.get_address_input_from_json(result_json, address=address)
        )

        if not inputs:
            raise Exception("No spendable outputs")

        if sum(input.amount for input in inputs) < amount:
            raise Exception(f"Error: You don't have enough funds")

        stake_inputs = self.repo.get_stake_input_from_json(result_json, address=address)
        if not stake_inputs:
            raise Exception(f"You are not a delegate. Become a delegate by staking.")

        is_validator_registered = result_json["is_validator"]
        if is_validator_registered:
            raise Exception(f"This address is already registered as validator.")

        is_inode_registered = result_json["is_inode"]
        if is_inode_registered:
            raise Exception(
                f"This address is registered as inode and an inode cannot be a validator."
            )

        transaction_inputs = self.select_transaction_input(inputs, amount)

        transaction_amount = sum(input.amount for input in transaction_inputs)

        message = self.string_to_bytes(
            str(TransactionType.VALIDATOR_REGISTRATION.value)
        )
        transaction = Transaction(
            transaction_inputs,
            [
                TransactionOutput(
                    address,
                    amount=amount,
                    transaction_type=OutputType.VALIDATOR_REGISTRATION,
                )
            ],
            message,
        )

        voting_power = Decimal(10)
        transaction.outputs.append(
            TransactionOutput(
                address,
                voting_power,
                transaction_type=OutputType.VALIDATOR_VOTING_POWER,
            )
        )

        if transaction_amount > amount:
            transaction.outputs.append(
                TransactionOutput(address, transaction_amount - amount)
            )

        transaction.sign([private_key])
        return transaction

    async def create_voting_transaction(
        self, private_key, vote_range, vote_receiving_address
    ):
        try:
            vote_range = int(vote_range)
        except:
            raise Exception("Invalid voting range")
        if vote_range > 10:
            raise Exception("Voting should be in range of 10")
        if vote_range <= 0:
            raise Exception("Invalid voting range")

        address = point_to_string(keys.get_public_key(private_key, CURVE))
        result_json = self.repo.get_address_info(
            address,
            stake_outputs=True,
            address_state=True,
            validator_unspent_votes=True,
            delegate_unspent_votes=True,
        )
        stake_inputs = self.repo.get_stake_input_from_json(result_json, address=address)

        is_inode_registered = result_json["is_inode"]
        if is_inode_registered:
            raise Exception(f"This address is registered as inode. Cannot vote.")

        is_validator_registered = result_json["is_validator"]
        if is_validator_registered:
            return await self.vote_as_validator(
                private_key, vote_range, vote_receiving_address, result_json
            )
        elif stake_inputs:
            return await self.vote_as_delegate(
                private_key, vote_range, vote_receiving_address, result_json
            )
        else:
            raise Exception("Not eligible to vote")

    async def vote_as_validator(
        self, private_key, vote_range, vote_receiving_address, result_json
    ):
        address = point_to_string(keys.get_public_key(private_key, CURVE))
        vote_range = Decimal(vote_range)
        inputs = []
        inputs.extend(
            self.repo.get_validator_unspent_votes_from_json(result_json, address)
        )
        if not inputs:
            raise Exception("No voting outputs")

        if sum(input.amount for input in inputs) < vote_range:
            raise Exception(
                f"Error: You don't have enough voting power left. Kindly revoke some voting power."
            )

        transaction_inputs = self.select_transaction_input(inputs, vote_range)

        transaction_vote_range = sum(input.amount for input in transaction_inputs)

        message = self.string_to_bytes(str(TransactionType.VOTE_AS_VALIDATOR.value))
        transaction = Transaction(
            transaction_inputs,
            [
                TransactionOutput(
                    vote_receiving_address,
                    amount=vote_range,
                    transaction_type=OutputType.VOTE_AS_VALIDATOR,
                )
            ],
            message,
        )
        if transaction_vote_range > vote_range:
            transaction.outputs.append(
                TransactionOutput(
                    address,
                    transaction_vote_range - vote_range,
                    transaction_type=OutputType.VALIDATOR_VOTING_POWER,
                )
            )

        transaction.sign([private_key])
        return transaction

    async def vote_as_delegate(
        self, private_key, vote_range, vote_receiving_address, result_json
    ):
        address = point_to_string(keys.get_public_key(private_key, CURVE))

        vote_range = Decimal(vote_range)
        inputs = []
        inputs.extend(
            self.repo.get_delegate_unspent_votes_from_json(result_json, address)
        )
        if not inputs:
            raise Exception("No voting outputs")

        if sum(input.amount for input in inputs) < vote_range:
            raise Exception(
                f"Error: You don't have enough voting power left. Kindly release some voting power."
            )

        transaction_inputs = self.select_transaction_input(inputs, vote_range)

        transaction_vote_range = sum(input.amount for input in transaction_inputs)

        message = self.string_to_bytes(str(TransactionType.VOTE_AS_DELEGATE.value))
        transaction = Transaction(
            transaction_inputs,
            [
                TransactionOutput(
                    vote_receiving_address,
                    amount=vote_range,
                    transaction_type=OutputType.VOTE_AS_DELEGATE,
                )
            ],
            message,
        )
        if transaction_vote_range > vote_range:
            transaction.outputs.append(
                TransactionOutput(
                    address,
                    transaction_vote_range - vote_range,
                    transaction_type=OutputType.DELEGATE_VOTING_POWER,
                )
            )

        transaction.sign([private_key])
        return transaction

    async def create_revoke_transaction(self, private_key, revoke_from_address):
        address = point_to_string(keys.get_public_key(private_key, CURVE))
        result_json = self.repo.get_address_info(address, stake_outputs=True,
                                                 address_state=True)

        stake_inputs = self.repo.get_stake_input_from_json(result_json, address=address)

        is_validator_registered = result_json['is_validator']
        if is_validator_registered:
            return await self.revoke_vote_as_validator(private_key, revoke_from_address, result_json)
        elif stake_inputs:
            pass
            return await self.revoke_vote_as_delegate(private_key, revoke_from_address, result_json)
        else:
            raise Exception('Not eligible to revoke')

    async def revoke_vote_as_validator(self, private_key, inode_address, address_info):
        address = point_to_string(keys.get_public_key(private_key, CURVE))
        inode_ballot = self.repo.get_validators_info(inode_address)
        inode_ballot_inputs = self.repo.get_inode_ballot_input_by_address_from_json(inode_ballot, address,
                                                                                    inode_address,
                                                                                    pending_spent_outputs=address_info[
                                                                                        'pending_spent_outputs'])
        if not inode_ballot_inputs:
            raise Exception('You have not voted.')

        message = self.string_to_bytes(str(TransactionType.REVOKE_AS_VALIDATOR.value))
        sum_of_votes = sum(inode_ballot_input.amount for inode_ballot_input in inode_ballot_inputs)
        transaction = Transaction(inode_ballot_inputs,
                                  [TransactionOutput(address, amount=sum_of_votes,
                                                     transaction_type=OutputType.VALIDATOR_VOTING_POWER)], message)
        transaction.sign([private_key])
        return transaction

    async def revoke_vote_as_delegate(self, private_key, validator_address, address_info):
        address = point_to_string(keys.get_public_key(private_key, CURVE))

        validator_ballot = self.repo.get_delegates_info(validator_address)
        validator_ballot_inputs = self.repo.get_validator_ballot_input_by_address_from_json(validator_ballot, address,
                                                                                            validator_address,
                                                                                            pending_spent_outputs=
                                                                                            address_info['pending_spent_outputs'])

        if not validator_ballot_inputs:
            raise Exception('You have not voted.')

        message = self.string_to_bytes(str(TransactionType.REVOKE_AS_DELEGATE.value))
        sum_of_votes = sum(validator_ballot_input.amount for validator_ballot_input in validator_ballot_inputs)
        transaction = Transaction(validator_ballot_inputs,
                                  [TransactionOutput(address, amount=sum_of_votes,
                                                     transaction_type=OutputType.DELEGATE_VOTING_POWER)], message)
        transaction.sign([private_key])
        return transaction

    def select_transaction_input(self, inputs, amount):
        transaction_inputs = []
        for tx_input in sorted(inputs, key=lambda item: item.amount):
            if tx_input.amount >= amount:
                transaction_inputs.append(tx_input)
                break
        for tx_input in sorted(inputs, key=lambda item: item.amount, reverse=True):
            if sum(input.amount for input in transaction_inputs) >= amount:
                break
            transaction_inputs.append(tx_input)
        return transaction_inputs

    def string_to_bytes(self, string: str) -> bytes:
        if string is None:
            return None
        try:
            return bytes.fromhex(string)
        except ValueError:
            return string.encode("utf-8")
