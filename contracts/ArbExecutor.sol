// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title  ArbExecutor - atomic cross-DEX arbitrage across V2 and V3 pools
/// @notice Borrows `tokenIn` from a V2 pair (flash swap), buys `tokenOut` on the
///         cheap venue (V2 router or V3 SwapRouter), sells it back on the
///         expensive venue and repays the pair - all in ONE transaction.
///         If the route is not profitable the whole tx reverts, so gas is only
///         ever spent on routes that simulation already proved profitable.
interface IERC20 {
    function balanceOf(address who) external view returns (uint256);
    function approve(address spender, uint256 value) external returns (bool);
    function transfer(address to, uint256 value) external returns (bool);
}

interface IUniswapV2Pair {
    function token0() external view returns (address);
    function token1() external view returns (address);
    function swap(uint256 amount0Out, uint256 amount1Out, address to, bytes calldata data) external;
}

interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

interface IUniswapV3SwapRouter {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }

    function exactInputSingle(ExactInputSingleParams calldata params)
        external
        returns (uint256 amountOut);
}

contract ArbExecutor {
    address public immutable owner;

    uint8 internal constant KIND_V2 = 0;
    uint8 internal constant KIND_V3 = 1;
    uint16 internal constant BPS = 10_000;

    struct Leg {
        uint8 kind;      // 0 = Uniswap-V2 style router, 1 = Uniswap-V3 SwapRouter
        address target;  // router to call
        address tokenIn;
        address tokenOut;
        uint24 fee;      // V3 fee tier (ignored for V2)
    }

    error NotOwner();
    error NotPair();
    error NotProfitable(uint256 got, uint256 need);
    error BadLeg();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Execute one arbitrage atomically.
    /// @return profit amount of tokenIn transferred to the owner
    function arb(
        address flashPair,
        address tokenIn,
        uint256 amountIn,
        uint256 minProfit,
        uint16 flashFeeBps,
        Leg calldata buy,
        Leg calldata sell
    ) external onlyOwner returns (uint256 profit) {
        require(amountIn > 0, "amountIn=0");
        require(minProfit > 0, "minProfit=0");
        require(flashFeeBps < BPS, "fee>=100%");

        IUniswapV2Pair pair = IUniswapV2Pair(flashPair);
        address token0 = pair.token0();

        uint256 amount0Out = tokenIn == token0 ? amountIn : 0;
        uint256 amount1Out = tokenIn == token0 ? 0 : amountIn;
        pair.swap(
            amount0Out,
            amount1Out,
            address(this),
            abi.encode(flashPair, tokenIn, amountIn, minProfit, flashFeeBps, buy, sell)
        );

        profit = IERC20(tokenIn).balanceOf(address(this));
        if (profit > 0) {
            IERC20(tokenIn).transfer(owner, profit);
        }
    }

    /// @notice Flash-swap callback: two swaps, then repay the pair.
    function uniswapV2Call(
        address sender,
        uint256 amount0,
        uint256 amount1,
        bytes calldata data
    ) external {
        (
            address flashPair,
            address tokenIn,
            uint256 amountIn,
            uint256 minProfit,
            uint16 flashFeeBps,
            Leg memory buy,
            Leg memory sell
        ) = abi.decode(data, (address, address, uint256, uint256, uint16, Leg, Leg));
        if (msg.sender != flashPair || sender != address(this)) revert NotPair();

        uint256 borrowed = amount0 > 0 ? amount0 : amount1;
        if (borrowed == 0 || borrowed != amountIn) revert BadLeg();

        uint256 bought = _swap(buy, borrowed);   // buy tokenOut on the cheap venue
        if (bought == 0) revert BadLeg();
        uint256 back = _swap(sell, bought);      // sell it on the expensive venue

        uint256 owed = borrowed + (borrowed * flashFeeBps) / (BPS - flashFeeBps) + 1;
        uint256 balance = IERC20(tokenIn).balanceOf(address(this));
        if (back < owed + minProfit || balance < owed + minProfit) {
            revert NotProfitable(balance, owed + minProfit);
        }
        IERC20(tokenIn).transfer(msg.sender, owed);
    }

    function _swap(Leg memory leg, uint256 amountIn) internal returns (uint256) {
        IERC20(leg.tokenIn).approve(leg.target, amountIn);
        if (leg.kind == KIND_V3) {
            return IUniswapV3SwapRouter(leg.target).exactInputSingle(
                IUniswapV3SwapRouter.ExactInputSingleParams({
                    tokenIn: leg.tokenIn,
                    tokenOut: leg.tokenOut,
                    fee: leg.fee,
                    recipient: address(this),
                    deadline: block.timestamp,
                    amountIn: amountIn,
                    amountOutMinimum: 0,
                    sqrtPriceLimitX96: 0
                })
            );
        }
        if (leg.kind == KIND_V2) {
            address[] memory path = new address[](2);
            path[0] = leg.tokenIn;
            path[1] = leg.tokenOut;
            uint256[] memory amounts = IUniswapV2Router(leg.target).swapExactTokensForTokens(
                amountIn,
                0,
                path,
                address(this),
                block.timestamp
            );
            return amounts[amounts.length - 1];
        }
        revert BadLeg();
    }
}

