import logging
from typing import Literal, Sequence

from hhd.controller import Event
from hhd.controller.lib.hid import Device
import time

from .const import (
    COMMANDS_GAME,
    COMMANDS_INIT,
    COMMANDS_MOUSE,
    RGB_APPLY,
    RGB_BRIGHTNESS_MAX,
    RGB_INIT_1,
    RGB_INIT_2,
    RGB_SET,
    buf,
)

Zone = Literal["all", "left_left", "left_right", "right_left", "right_right"]
RgbMode = Literal["solid", "pulse", "dynamic", "spiral"]
GamepadMode = Literal["default", "mouse", "macro"]

logger = logging.getLogger(__name__)


def rgb_command(zone: Zone, mode: RgbMode, red: int, green: int, blue: int):
    match mode:
        case "solid":
            # Static
            c_mode = 0x00
        case "pulse":
            # Breathing
            c_mode = 0x01
        case "dynamic":
            # Color cycle
            c_mode = 0x02
        case "spiral":
            # Rainbow
            c_mode = 0x03
        # case "adsf":
        #     # Strobing
        #     c_mode = 0x0A
        # case "asdf":
        #     # Direct (?)
        #     c_mode = 0xFF
        case _:
            c_mode = 0x00

    match zone:
        case "left_left":
            c_zone = 0x01
        case "left_right":
            c_zone = 0x02
        case "right_left":
            c_zone = 0x03
        case "right_right":
            c_zone = 0x04
        case _:
            c_zone = 0x00

    return buf(
        [
            0x5A,
            0xB3,
            c_zone,  # zone
            c_mode,  # mode
            red,
            green,
            blue,
            0x00,  # speed
            0x00,  # direction
            0x00,  # breathing
            red,
            green,
            blue,
        ]
    )


def rgb_set(
    side: Literal["main", "left", "right"],
    mode: RgbMode,
    red: int,
    green: int,
    blue: int,
):
    match side:
        case "left":
            return [
                rgb_command("left_left", mode, red, green, blue),
                rgb_command("left_right", mode, red, green, blue),
            ]
        case "right":
            return [
                rgb_command("right_right", mode, red, green, blue),
                rgb_command("right_left", mode, red, green, blue),
            ]
        case _:
            return [
                rgb_command("all", mode, red, green, blue),
            ]


INIT_EVERY_S = 10


def process_events(events: Sequence[Event]):
    cmds = []
    for ev in events:
        if ev["type"] == "led":
            if ev["mode"] == "disable":
                cmds.extend(rgb_set(ev["code"], "solid", 0, 0, 0))
            else:
                match ev["mode"]:
                    case "blinking":
                        mode = "pulse"
                    case "rainbow":
                        mode = "dynamic"
                    case "solid":
                        mode = "solid"
                    case "spiral":
                        mode = "spiral"
                    case _:
                        assert False, f"Mode '{ev['mode']}' not supported."
                cmds.extend(
                    rgb_set(
                        ev["code"],
                        mode,
                        ev["red"],
                        ev["green"],
                        ev["blue"],
                    )
                )
    return cmds


class RgbCallback:
    def __init__(self) -> None:
        self.last_update = None

    def __call__(self, dev: Device, events: Sequence[Event]):
        cmds = process_events(events)
        if not cmds:
            return

        curr = time.perf_counter()
        if not self.last_update or self.last_update + INIT_EVERY_S < curr:
            self.last_update = curr
            cmds = [
                RGB_INIT_1,
                RGB_INIT_2,
                RGB_BRIGHTNESS_MAX,
                *cmds,
                RGB_APPLY,
                RGB_SET,
            ]

        for r in cmds:
            logger.warning(r.hex())
            dev.write(r)


def initialize(dev: Device):
    for cmd in COMMANDS_INIT:
        dev.write(cmd)


def switch_mode(dev: Device, mode: GamepadMode):
    match mode:
        case "default":
            cmds = COMMANDS_GAME
        # case "macro":
        #     cmds = MODE_MACRO
        case "mouse":
            cmds = COMMANDS_MOUSE
        case _:
            assert False, f"Mode '{mode}' not supported."

    for cmd in cmds:
        dev.write(cmd)
