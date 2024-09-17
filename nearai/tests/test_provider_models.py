import unittest

from nearai.naming import NamespacedName
from nearai.provider_models import get_provider_namespaced_model, provider_models


class TestGetProviderNamespacedModel(unittest.TestCase):
    """Unit tests for get_provider_namespaced_model."""

    def test_hyperbolic(self):  # noqa: D102
        self.assertEqual(
            get_provider_namespaced_model("hyperbolic::StableDiffusion"),
            ("hyperbolic", NamespacedName(name="StableDiffusion")),
        )
        self.assertEqual(
            get_provider_namespaced_model("hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
            ("hyperbolic", NamespacedName(name="Meta-Llama-3.1-70B-Instruct")),
        )

    def test_fireworks(self):  # noqa: D102
        self.assertEqual(
            get_provider_namespaced_model("fireworks::accounts/fireworks/models/mixtral-8x7b-instruct"),
            ("fireworks", NamespacedName(name="mixtral-8x7b-instruct")),
        )
        self.assertEqual(
            get_provider_namespaced_model("fireworks::accounts/yi-01-ai/models/yi-large"),
            ("fireworks", NamespacedName(name="yi-large", namespace="yi-01-ai")),
        )


class TestMatchProviderModel(unittest.TestCase):
    """Unit tests for get_provider_namespaced_model."""

    def test_fireworks(self):  # noqa: D102
        self.assertEqual(
            provider_models.match_provider_model("fireworks::accounts/yi-01-ai/models/yi-large"),
            ("fireworks", "fireworks::accounts/yi-01-ai/models/yi-large"),
        )
        self.assertEqual(
            provider_models.match_provider_model("accounts/yi-01-ai/models/yi-large"),
            ("fireworks", "fireworks::accounts/yi-01-ai/models/yi-large"),
        )
        self.assertEqual(
            provider_models.match_provider_model("llama-v3-70b-instruct"),
            ("fireworks", "fireworks::accounts/fireworks/models/llama-v3-70b-instruct"),
        )
        self.assertEqual(
            provider_models.match_provider_model("yi-01-ai/yi-large"),
            ("fireworks", "fireworks::accounts/yi-01-ai/models/yi-large"),
        )

    def test_hyperbolic(self):  # noqa: D102
        self.assertEqual(
            provider_models.match_provider_model("hyperbolic::StableDiffusion"),
            ("hyperbolic", "hyperbolic::StableDiffusion"),
        )
        self.assertEqual(
            provider_models.match_provider_model("hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
            ("hyperbolic", "hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
        )
        self.assertEqual(
            provider_models.match_provider_model("hyperbolic::Meta-Llama-3.1-70B-Instruct"),
            ("hyperbolic", "hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
        )

    def test_registry_with_multiple_providers(self):  # noqa: D102
        self.assertEqual(
            provider_models.match_provider_model("llama-3.1-70b-instruct"),
            ("fireworks", "fireworks::accounts/fireworks/models/llama-v3p1-70b-instruct"),
        )
        self.assertEqual(
            provider_models.match_provider_model("llama-3.1-70b-instruct", provider="hyperbolic"),
            ("hyperbolic", "hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
        )
        self.assertEqual(
            provider_models.match_provider_model("near.ai/llama-3.1-70b-instruct", provider="hyperbolic"),
            ("hyperbolic", "hyperbolic::meta-llama/Meta-Llama-3.1-70B-Instruct"),
        )


if __name__ == "__main__":
    unittest.main()
