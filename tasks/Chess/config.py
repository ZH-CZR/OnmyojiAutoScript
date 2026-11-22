# This Python file uses the following encoding: utf-8

from pydantic import Field

from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler
from tasks.Chess.strategy.lineup import LineupBond


class ChessConfig(ConfigBase):
    """百鬼棋局循环与结束条件。"""

    lineup_bond: LineupBond = Field(
        title='选择阵容羁绊',
        default=LineupBond.ARAKAWA,
        description='选择百鬼棋局使用的阵容羁绊与对应运营策略',
    )

    custom_lineup: str = Field(
        title='自定义阵容标识',
        default='',
        description=(
            '留空时使用“选择阵容羁绊”；填写阵容工坊保存的标识'
            '（如 my_lineup）则优先使用该自定义阵容'
        ),
    )

    rank_protection: bool = Field(
        title='保段位',
        default=False,
        description='开启后每完成前四名一局主动退出三局；退出局不计入执行次数',
    )

    run_count: int = Field(
        title='执行次数',
        default=1,
        ge=-1,
        description='完成目标局数后结束；设置为-1时一直执行',
    )
    matchmaking_timeout_seconds: int = Field(
        title='匹配限制时间（秒）',
        default=60,
        ge=10,
        description=(
            '单次匹配超过限制后取消并重新匹配；连续三次超时'
            '则标记为等待过多并结束任务'
        ),
    )
    limit_time: Time = Field(
        title='运行时间限制',
        default=Time(minute=30),
        description='达到限制时间后不再开始下一局，已经开始的对局会正常完成',
    )
    coin_full_exit: bool = Field(
        title='刷满鼬乐币',
        default=False,
        description='勾选后检测到鼬乐币已满时立即结束百鬼棋局',
    )
    continue_grigri_refresh_below_nine: bool = Field(
        title='刷新非前40%符咒',
        default=True,
        description=(
            '按当前品质符咒总数的实际收益排名，保留排名前40%的'
            '选项，只刷新其余仍有刷新次数的位置；同收益边界按'
            '固定图鉴顺序确定名次'
        ),
    )
    hyakki_draft_enabled: bool = Field(
        title='百鬼优先所需御魂',
        default=True,
        description=(
            '百鬼阶段本人锁消失后主动投掷一次；优先选择阵容所需御魂，'
            '没有所需御魂且全场锁均已消失时才随机投掷'
        ),
    )


class Chess(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    chess_config: ChessConfig = Field(default_factory=ChessConfig)
