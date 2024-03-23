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

2. **Prepare Your Development Environment**

   Depending on your operating system, you may need to install additional tools to ensure the `fastecdsa` Python package and other dependencies compile correctly:

   - **Ubuntu Users:**

     Install the necessary libraries by running:

     ```bash
     sudo apt-get update
     sudo apt-get install libgmp3-dev
     sudo apt-get install build-essential libssl-dev libffi-dev python3-dev
     ```

   - **Windows Users:**

     Install Visual Studio, which includes the necessary C++ build tools. Download it from [https://visualstudio.microsoft.com/vs/preview/](https://visualstudio.microsoft.com/vs/preview/) and ensure to select the C++ workload during installation.
     [wikihow Install Clang on Windows](https://www.wikihow.com/Install-Clang-on-Windows)

   - **macOS Users:**

     Install Xcode or the standalone Command Line Tools for Xcode, which include `clang`. This can be done by installing Xcode from the Mac App Store or by running the following command in the terminal:

     ```bash
     xcode-select --install
     ```

     For users who prefer not to install Xcode, downloading Command Line Tools for Xcode from [Apple Developer Downloads](https://developer.apple.com/download/more/) is an alternative.
     [https://ics.uci.edu/~pattis/common/handouts/macclion/clang.html](https://ics.uci.edu/~pattis/common/handouts/macclion/clang.html)

Please ensure these tools are correctly installed and configured on your system before proceeding with the installation of the Python package dependencies.

3. **Install the required dependencies** by running the following command in your terminal:

   ```bash
   pip install -r requirements.txt
   ```

4. **Navigate to the project directory** where the `wallet.py` file is located.

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
   - Delegates can vote for validators within a specified range from 1 to 10. The amount of staked coins directly influences their voting power. For example, if a delegate stakes 1000 coins and allocates a voting range of 5 to a validator, it signifies that 500 of their staked coins support that validator.

```bash
python3 wallet.py vote -r [range] -to [recipient_address]
```

- `-r`: The range of your vote.
- `-to`: The address of the validator you are voting for.

2. To vote for a Inode by a validator:
   - Validators, once registered, can cast votes towards iNodes based on their total stake from delegate This process is similar to delegate voting but is specifically aimed at supporting network infrastructure and governance.

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
