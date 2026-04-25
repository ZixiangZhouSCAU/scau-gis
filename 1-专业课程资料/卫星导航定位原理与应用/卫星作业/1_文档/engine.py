"""
GNSS OrbitMaster - engine.py
Required libraries: georinex, numpy, astropy, scipy, PyQt6

核心计算引擎：聚合广播与精密星历解算器并提供统一接口。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from astropy.time import Time

from broadcast_solver import BroadcastSolver
from models import CalculationResult
from precise_solver import PreciseSolver
from time_utils import to_gpst


class PositioningEngine:
    """GNSS OrbitMaster 的核心坐标解算引擎。"""

    def __init__(self) -> None:
        self.broadcast_solver = BroadcastSolver()
        self.precise_solver = PreciseSolver()
        self._loaded_files: Dict[str, str] = {}

    # ------------------------------------------------------------------
    def load_ephemeris(self, file_path: str) -> Dict[str, Sequence[str]]:
        """根据扩展名自动解析星历文件。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"星历文件不存在: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".sp3":
            satellites = self.precise_solver.load_sp3_file(str(path))
            ephemeris_type = "Precise"
        else:
            satellites = self.broadcast_solver.load_nav_file(str(path))
            ephemeris_type = "Broadcast"

        self._loaded_files[str(path)] = ephemeris_type
        return {"type": ephemeris_type, "satellites": tuple(satellites)}

    # ------------------------------------------------------------------
    def get_position(
        self,
        sv_id: str,
        epoch: Time,
        ephemeris_type: str,
    ) -> CalculationResult:
        """根据指定类型的星历计算卫星坐标。"""
        ephemeris_type = ephemeris_type.capitalize()
        if ephemeris_type not in {"Broadcast", "Precise"}:
            raise ValueError("ephemeris_type 只能为 'Broadcast' 或 'Precise'")

        if ephemeris_type == "Broadcast":
            gps_week, sow = to_gpst(epoch)
            x, y, z = self.broadcast_solver.calculate_position(sv_id, (gps_week, float(sow)))
        else:
            x, y, z = self.precise_solver.calculate_position(sv_id, epoch)

        return CalculationResult(
            sv=sv_id,
            epoch=epoch,
            x=x,
            y=y,
            z=z,
            ephemeris_type=ephemeris_type,
        )

    # ------------------------------------------------------------------
    def list_satellites(self) -> Sequence[str]:
        """综合返回所有已加载卫星编号。"""
        sats = set(self.broadcast_solver.available_satellites()) | set(self.precise_solver.available_satellites())
        return tuple(sorted(sats))

    def has_broadcast(self) -> bool:
        return bool(self.broadcast_solver.available_satellites())

    def has_precise(self) -> bool:
        return bool(self.precise_solver.available_satellites())

    def loaded_files(self) -> Dict[str, str]:
        return dict(self._loaded_files)
