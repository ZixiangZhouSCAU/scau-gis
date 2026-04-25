"""
GNSS OrbitMaster - time_utils.py
Required libraries: georinex, numpy, astropy, scipy, PyQt6

时间转换工具：提供UTC -> GPST 的高精度转换。
"""
from __future__ import annotations

from datetime import datetime
from typing import Tuple, Union

import numpy as np
from astropy.time import Time

from models import GPSConstants

UTCInput = Union[str, datetime, Time]


def to_gpst(input_time: UTCInput) -> Tuple[int, np.float64]:
    """将UTC时间转换为GPS周与周内秒.

    Args:
        input_time: datetime/字符串(ISO8601)/AstroPy Time

    Returns:
        (gps_week, seconds_of_week)
    """
    if isinstance(input_time, str):
        time_obj = Time(input_time, scale="utc")
    elif isinstance(input_time, datetime):
        time_obj = Time(input_time, scale="utc")
    elif isinstance(input_time, Time):
        time_obj = input_time
    else:
        raise TypeError("input_time 必须为 str, datetime 或 astropy.time.Time 类型")

    gps_seconds = np.float64(time_obj.to_value("gps"))
    if np.isnan(gps_seconds):
        raise ValueError(f"无法将时间 {time_obj.iso} 转换为GPS秒，请检查输入数据是否完整")
    gps_week = int(np.floor(gps_seconds / GPSConstants.GPS_WEEK_SECONDS))
    seconds_of_week = np.float64(gps_seconds - gps_week * GPSConstants.GPS_WEEK_SECONDS)
    return gps_week, seconds_of_week
