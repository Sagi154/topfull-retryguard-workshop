"""Admission-cap floor applied to the live TopFull sources on master.

Every API may be written as 0. The strings from the *_new() helpers are
what run_scenario.py inserts.
"""

MIN_THRESHOLD = 0

OVERLOAD_FLOOR_OLD = (
    "        if api['threshold'] <= 10:\n"
    "            api['threshold'] = 10\n"
)

DEPLOY_RL_ZERO_OLD = (
    "        if self.threshold == 0:\n"
    "            self.stop(reset=True)\n"
    '            print("zero threshold")\n'
    "            return\n"
)

DEPLOY_RL_RATIO_OLD = "        state = goodput / self.threshold\n"

PROXY_BURST_OLD = (
    "\t\ttargetLimiter.SetLimit(rate.Limit(float64(newRate)))\n"
    "\t\ttargetLimiter.SetBurst(int(newRate))\n"
    '\t\tprintln("Apply threshold to ", api, " : ", newRate)\n'
)


def floor_threshold(threshold: float) -> float:
    if threshold <= MIN_THRESHOLD:
        return MIN_THRESHOLD
    return threshold


def goodput_ratio(goodput: float, threshold: float) -> float:
    if threshold == 0:
        return 0.0
    return goodput / threshold


def overload_floor_new() -> str:
    return (
        "        # TOPFULL_CAP_FLOOR\n"
        "        if api['threshold'] <= 0:\n"
        "            api['threshold'] = 0\n"
    )


def deploy_rl_zero_block() -> str:
    return "        # TOPFULL_CAP_FLOOR: a summed threshold of 0 is a real cap.\n"


def deploy_rl_ratio_block() -> str:
    return "        state = 0.0 if self.threshold == 0 else goodput / self.threshold\n"


def proxy_burst_new() -> str:
    return (
        "\t\t// TOPFULL_CAP_FLOOR\n"
        "\t\tburst := int(newRate)\n"
        "\t\tif newRate > 0 && burst < 1 {\n"
        "\t\t\tburst = 1\n"
        "\t\t}\n"
        "\t\ttargetLimiter.SetLimit(rate.Limit(float64(newRate)))\n"
        "\t\ttargetLimiter.SetBurst(burst)\n"
        '\t\tprintln("Apply threshold to ", api, " : ", newRate)\n'
    )
