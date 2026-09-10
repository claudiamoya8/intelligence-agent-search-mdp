"""Regression tests for the core models and planning algorithms."""

from __future__ import annotations

import random
import unittest

import kurtz
import palacio
import river_mdp


class LogicalPalaceTests(unittest.TestCase):
    def setUp(self) -> None:
        kurtz.USE_COLOR = False

    def test_grid_neighbours_respect_board_boundaries(self) -> None:
        self.assertEqual(
            set(kurtz.vecinos_ortogonales(4, (1, 1))),
            {(1, 2), (2, 1)},
        )
        self.assertEqual(len(kurtz.vecinos_ortogonales(4, (2, 2))), 4)

    def test_generated_world_has_distinct_elements(self) -> None:
        for seed in range(20):
            random.seed(seed)
            world = kurtz.crear_mundo(6)
            pits = set(world["pits"])
            unique_positions = pits | {
                world["soldier"],
                world["exit"],
                world["kurtz"],
            }

            self.assertEqual(len(pits), 3)
            self.assertEqual(len(unique_positions), 6)
            self.assertNotIn(world["start"], unique_positions)

    def test_percept_has_expected_schema_at_start(self) -> None:
        random.seed(7)
        world = kurtz.crear_mundo(6)
        percept = kurtz.calcular_percepto(world)

        self.assertEqual(len(percept), 8)
        self.assertTrue(percept[3])  # upper wall
        self.assertFalse(percept[4])
        self.assertTrue(percept[5])  # left wall
        self.assertFalse(percept[6])

    def test_search_algorithms_return_valid_paths(self) -> None:
        allowed = set(kurtz.todas_las_celdas(4))
        for method in ("bfs", "dfs", "gbfs", "astar"):
            path = kurtz.planificar_camino_permitido(
                4,
                (1, 1),
                (4, 4),
                allowed,
                method,
                objetivo_heuristica=(4, 4),
            )
            self.assertIsNotNone(path, method)
            assert path is not None
            self.assertEqual(path[0], (1, 1))
            self.assertEqual(path[-1], (4, 4))
            self.assertTrue(all(cell in allowed for cell in path))
            self.assertTrue(
                all(kurtz.distancia_manhattan(a, b) == 1 for a, b in zip(path, path[1:])),
                method,
            )

        for method in ("bfs", "astar"):
            path = kurtz.planificar_camino_permitido(
                4,
                (1, 1),
                (4, 4),
                allowed,
                method,
                objetivo_heuristica=(4, 4),
            )
            self.assertEqual(len(path or []), 7)


class BayesianPalaceTests(unittest.TestCase):
    def test_initial_posteriors_are_normalised_and_exclude_start(self) -> None:
        kb = palacio.crear_kb_bayes(4, (1, 1))
        for key in (
            "posterior_F",
            "posterior_P",
            "posterior_D",
            "posterior_M",
            "posterior_S",
            "posterior_CK",
        ):
            distribution = kb[key]
            self.assertNotIn((1, 1), distribution)
            self.assertAlmostEqual(sum(distribution.values()), 1.0)

    def test_deterministic_update_matches_stimulus_zone(self) -> None:
        prior = palacio.prior_uniforme(palacio.todas_las_celdas(4))
        posterior = palacio.actualizar_posterior_determinista(
            4,
            prior,
            observacion=True,
            celda_actual=(1, 1),
        )
        compatible = palacio.zona_estimulo(4, (1, 1))

        self.assertAlmostEqual(sum(posterior.values()), 1.0)
        self.assertTrue(all(posterior[cell] > 0 for cell in compatible))
        self.assertTrue(
            all(probability == 0 for cell, probability in posterior.items() if cell not in compatible)
        )

    def test_generated_entities_avoid_all_traps(self) -> None:
        for seed in range(20):
            kurtz.random.seed(seed)
            world = palacio.crear_mundo_bayes(6)
            traps = set().union(*world["traps"].values())

            self.assertNotIn(world["start"], traps)
            self.assertNotIn(world["soldier"], traps)
            self.assertNotIn(world["exit"], traps)
            self.assertNotIn(world["kurtz"], traps)

    def test_all_search_methods_cross_an_open_grid(self) -> None:
        allowed = set(palacio.todas_las_celdas(3))
        for method in ("bfs", "dfs", "gbfs", "astar"):
            actions = palacio.planificar_camino_trazado(
                3,
                (1, 1),
                (3, 3),
                allowed,
                method,
            )
            self.assertIsNotNone(actions, method)
            self.assertEqual(len(actions or []), 4)


class RiverMdpTests(unittest.TestCase):
    def setUp(self) -> None:
        river_mdp.USE_COLOR = False

    def test_generated_environment_respects_invariants(self) -> None:
        random.seed(7)
        env = river_mdp.generar_entorno(
            nrows=7,
            ncols=6,
            nislas=2,
            npeligros=3,
        )

        self.assertEqual(env["start"], (0, 0))
        self.assertEqual(env["exit"][1], 5)
        self.assertEqual(len(env["islands"]), 2)
        self.assertEqual(len(env["hazards"]), 3)
        self.assertTrue(set(env["islands"]).isdisjoint(env["hazards"]))
        self.assertEqual(env["strength"][0], 0.0)
        self.assertEqual(env["strength"][-1], 0.0)
        self.assertTrue(all(0.0 <= value <= 1.0 for value in env["strength"]))

    def test_every_transition_is_a_probability_distribution(self) -> None:
        random.seed(11)
        env = river_mdp.generar_entorno(npeligros=2)
        valid_states = set(river_mdp.estados(env))

        for state in valid_states:
            for action in env["actions"]:
                transitions = river_mdp.transiciones(env, state, action)
                self.assertAlmostEqual(sum(probability for _, probability in transitions), 1.0)
                self.assertTrue(all(next_state in valid_states for next_state, _ in transitions))
                self.assertTrue(all(0.0 <= probability <= 1.0 for _, probability in transitions))

    def test_value_iteration_finds_the_direct_deterministic_route(self) -> None:
        env = {
            "nrows": 2,
            "ncols": 3,
            "start": (0, 0),
            "exit": (0, 2),
            "islands": set(),
            "hazards": set(),
            "hazard_terminal": True,
            "hazard_penalty": -100.0,
            "strength": [0.0, 0.0, 0.0],
            "actions": ["up", "down", "left", "right", "stay"],
        }
        _, policy = river_mdp.value_iteration(env)
        path = river_mdp.simular(env, policy, max_steps=10)

        self.assertEqual(policy[(0, 0)], "right")
        self.assertEqual(policy[(0, 1)], "right")
        self.assertEqual(policy[env["exit"]], "·")
        self.assertEqual(path, [(0, 0), (0, 1), (0, 2)])


if __name__ == "__main__":
    unittest.main()
