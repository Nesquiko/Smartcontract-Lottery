from brownie import Lottery, accounts, config, network, exceptions
from web3 import Web3
from scripts.deploy_lottery import deploy_lottery
from scripts.util import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    fund_with_link,
    get_account,
    get_contract,
)
import pytest


def test_get_entrance_fee():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    lottery = deploy_lottery()

    entrance_fee = lottery.getEntranceFee()
    expected_entrance_fee = Web3.toWei(0.025, "ether")

    assert (
        entrance_fee == expected_entrance_fee
    ), f"Entrance fee of {entrance_fee} is not equal to expected entrance fee of {expected_entrance_fee}"


def test_cant_enter_unless_started():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    lottery = deploy_lottery()

    with pytest.raises(exceptions.VirtualMachineError):
        lottery.enter({"from": get_account(), "value": lottery.getEntranceFee()})


def test_can_start_and_enter_lottery():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": get_account(), "value": lottery.getEntranceFee()})

    assert lottery.players(0) == account


def test_can_end_lottery():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    fund_with_link(lottery)
    lottery.endLottery({"from": account})

    # 2 = LOTTERY_STATE.CALCULATING_WINNER
    assert (
        lottery.lottery_state() == 2
    ), f"Lottery is in wrong state {lottery.lottery_state()}!"


def test_can_pick_winner_correctly():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()

    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=1), "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=2), "value": lottery.getEntranceFee()})

    fund_with_link(lottery)

    tx = lottery.endLottery({"from": account})
    requestId = tx.events["RequestRandomness"]["requestId"]

    RANDOM_NUMBER = 12
    # pretending we are chainlink node
    get_contract("vrf_coordinator").callBackWithRandomness(
        requestId, RANDOM_NUMBER, lottery.address, {"from": account}
    )

    starting_balance_account = account.balance()
    lottery_balance = lottery.balance()
    expected_account_balance = starting_balance_account + lottery_balance
    assert (
        lottery.recentWinner() == account
    ), f"Expected winner was {account}, but was {lottery.recentWinner()}"

    assert (
        lottery.balance() == 0
    ), f"Lottery balance should have been 0, but was {lottery.balane()}"

    assert (
        account.balance() == expected_account_balance
    ), f"Expected account balance is {expected_account_balance}, but was {account.balance()} "
