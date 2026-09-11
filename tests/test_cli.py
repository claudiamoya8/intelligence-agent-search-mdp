"""End-to-end smoke tests for the three interactive entry points."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def run_program(filename: str, answers: list[str]) -> subprocess.CompletedProcess[str]:
    """Run one console program with deterministic, non-interactive answers."""
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"

    return subprocess.run(
        [sys.executable, "-B", filename],
        cwd=ROOT,
        input="\n".join(answers) + "\n",
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=20,
        check=False,
        env=environment,
    )


class CommandLineSmokeTests(unittest.TestCase):
    def assert_successful_run(
        self,
        result: subprocess.CompletedProcess[str],
        expected_fragments: tuple[str, ...],
    ) -> None:
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        for fragment in expected_fragments:
            self.assertIn(fragment, output)
        self.assertNotIn("Traceback (most recent call last)", output)

    def test_logical_palace_starts_and_exits_cleanly(self) -> None:
        result = run_program("kurtz.py", ["manual", "n", "3", "t"])
        self.assert_successful_run(
            result,
            (
                "BUSCANDO AL CORONEL KURTZ",
                "Conocimiento del agente sobre el PALACIO",
                "Modelos pits consistentes",
                "Partida terminada por el usuario.",
            ),
        )

    def test_bayesian_palace_starts_and_exits_cleanly(self) -> None:
        result = run_program("palacio.py", ["manual", "n", "3", "", "t"])
        self.assert_successful_run(
            result,
            (
                "PARTE 2 - BAYES",
                "Mapas de probabilidad (Bayes)",
                "Mapa de riesgo (para decidir movimientos)",
                "Partida terminada por el usuario.",
            ),
        )

    def test_river_mdp_completes_a_seeded_episode(self) -> None:
        result = run_program("river_mdp.py", ["n", "3", "0"])
        self.assert_successful_run(
            result,
            (
                "RÍO MDP",
                "Entorno generado",
                "Política óptima",
                "Simulación siguiendo la política",
                "Estado final:",
            ),
        )


if __name__ == "__main__":
    unittest.main()
