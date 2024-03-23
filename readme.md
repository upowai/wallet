# uPow Blockchain Wallet

The uPow Blockchain Wallet is a command-line interface (CLI) tool designed for interacting with the uPow blockchain. It allows users to perform various actions such as creating wallets, sending transactions, checking balances, staking, voting, and more. This document provides detailed instructions on how to set up and use the uPow Blockchain Wallet.

## Prerequisites

- Python 3.11 or higher
- An internet connection

## Installation

1. **Clone the repository or download the source code** to your local machine.

   ```bash
   git clone https://github.com/upowai/wallet.git
   cd wallet
   ```

2. **Install the required dependencies** by running the following command in your terminal:

   ```bash
   pip install -r requirements.txt
   ```

3. **Navigate to the project directory** where the `wallet.py` file is located.

## Usage

To use the uPow Blockchain Wallet, you will run commands in the format of `python3 wallet.py [command] [options]`. Below are the available commands and their usage:

### Creating a Wallet

To create a new wallet, which includes generating a new private key and its associated public address:

```bash
python3 wallet.py createwallet
```

- Your Privatekey and Publickey will be stored locally in `key_pair_list.json`

### Checking Balance

To check the balance of all addresses in your wallet:

```bash
python3 wallet.py balance
```

### Sending uPow

To send uPow to another address:

```bash
python3 wallet.py send -to [recipient_address] -a [amount] -m [message (optional)]
```

- `-to`: The recipient's address.
- `-a`: The amount of uPow to send.
- `-m`: An optional message to include with the transaction.

### Staking uPow

To stake uPow:

```bash
python3 wallet.py stake -a [amount]
```

- `-a`: The amount of uPow to stake.

### Unstaking uPow

To unstake all staked uPow:

```bash
python3 wallet.py unstake
```

### Registering as an Inode

To register as an inode:

```bash
python3 wallet.py register_inode
```

### Deregistering as an Inode

To deregister as an inode:

```bash
python3 wallet.py de_register_inode
```

### Registering as a Validator

To register as a validator:

```bash
python3 wallet.py register_validator
```

### Voting

1. To vote for a validator by a delegate:

```bash
python3 wallet.py vote -r [range] -to [recipient_address]
```

- `-r`: The range of your vote.
- `-to`: The address of the validator you are voting for.

2. To vote for a Inode by a validator:

```bash
python3 wallet.py vote -r [range] -to [recipient_address]
```

- `-r`: The range of your vote.
- `-to`: The address of the inode you are voting for.

### Revoke

The `revoke` command allows users to withdraw their delegation or validation rights. This can be applied dynamically and is useful for managing staking preferences or validator participation.

- To revoke a delegation or validation:

```bash
python3 wallet.py revoke -from [address]
```

- `-from`: The address from which you are revoking your stake or validation rights. This could be a validator address if you are a staked delegate, or it could be an inode address if you are a validator.

## Support

For additional help or information about the uPow Blockchain Wallet, please refer to the official uPow documentation or contact the support team at discord.
