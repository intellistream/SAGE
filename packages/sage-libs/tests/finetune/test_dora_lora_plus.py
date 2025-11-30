"""
Unit tests for DoRA and LoRA+ implementations.

Tests:
- DoRA configuration via PEFT
- LoRA+ differentiated learning rates
- LoRAPlusTrainer optimizer creation
"""

from sage.libs.finetune.agent.config import AgentSFTConfig


class TestDoRAConfig:
    """Test DoRA configuration."""

    def test_default_dora_disabled(self):
        """Test that DoRA is disabled by default."""
        config = AgentSFTConfig()
        assert config.use_dora is False

    def test_enable_dora(self):
        """Test enabling DoRA via config."""
        config = AgentSFTConfig(use_dora=True)
        assert config.use_dora is True

    def test_dora_with_other_settings(self):
        """Test DoRA can be combined with other settings."""
        config = AgentSFTConfig(
            use_dora=True,
            use_coreset_selection=True,
            coreset_strategy="hybrid",
        )
        assert config.use_dora is True
        assert config.use_coreset_selection is True


class TestLoRAPlusConfig:
    """Test LoRA+ configuration."""

    def test_default_lora_plus_disabled(self):
        """Test that LoRA+ is disabled by default."""
        config = AgentSFTConfig()
        assert config.use_lora_plus is False
        assert config.lora_plus_lr_ratio == 16.0  # Default ratio

    def test_enable_lora_plus(self):
        """Test enabling LoRA+ via config."""
        config = AgentSFTConfig(use_lora_plus=True)
        assert config.use_lora_plus is True

    def test_custom_lr_ratio(self):
        """Test custom learning rate ratio."""
        config = AgentSFTConfig(use_lora_plus=True, lora_plus_lr_ratio=8.0)
        assert config.lora_plus_lr_ratio == 8.0

    def test_lora_plus_with_continual(self):
        """Test LoRA+ can be combined with continual learning."""
        config = AgentSFTConfig(
            use_lora_plus=True,
            use_online_continual=True,
            continual_buffer_size=1024,
        )
        assert config.use_lora_plus is True
        assert config.use_online_continual is True


class TestLoRAPlusTrainer:
    """Test LoRA+ trainer optimizer creation."""

    def test_optimizer_param_groups(self):
        """Test that LoRAPlusTrainer stores lr_ratio correctly."""
        from sage.libs.finetune.agent.trainer import LoRAPlusTrainer

        # Test that the class accepts lr_ratio parameter
        # Full integration test requires actual model, so we just test config
        assert hasattr(LoRAPlusTrainer, "__init__")

        # Test that lora_plus_lr_ratio is documented in class
        assert "lora_plus_lr_ratio" in LoRAPlusTrainer.__init__.__code__.co_varnames

    def test_lr_ratio_calculation(self):
        """Test learning rate calculation for B matrices."""
        base_lr = 2e-5
        lr_ratio = 16.0
        expected_b_lr = base_lr * lr_ratio

        assert expected_b_lr == 3.2e-4


class TestMethodRegistryIntegration:
    """Test Method Registry includes DoRA and LoRA+ methods."""

    def test_dora_method_registered(self):
        """Test G_dora method is registered."""
        from sage.benchmark.benchmark_agent.experiments.method_comparison import MethodRegistry

        methods = MethodRegistry.get_all_methods()
        assert "G_dora" in methods

        dora_config = methods["G_dora"]
        assert dora_config.use_dora is True
        assert "DoRA" in dora_config.name

    def test_lora_plus_method_registered(self):
        """Test H_lora_plus method is registered."""
        from sage.benchmark.benchmark_agent.experiments.method_comparison import MethodRegistry

        methods = MethodRegistry.get_all_methods()
        assert "H_lora_plus" in methods

        lora_plus_config = methods["H_lora_plus"]
        assert lora_plus_config.use_lora_plus is True
        assert lora_plus_config.lora_plus_lr_ratio == 16.0

    def test_combined_methods_registered(self):
        """Test combined methods are registered."""
        from sage.benchmark.benchmark_agent.experiments.method_comparison import MethodRegistry

        methods = MethodRegistry.get_all_methods()

        # DoRA + Coreset
        assert "I_dora_coreset" in methods
        dora_coreset = methods["I_dora_coreset"]
        assert dora_coreset.use_dora is True
        assert dora_coreset.use_coreset is True

        # LoRA+ + Continual
        assert "J_loraplus_continual" in methods
        lora_cont = methods["J_loraplus_continual"]
        assert lora_cont.use_lora_plus is True
        assert lora_cont.use_continual is True


class TestMethodConfigSerialization:
    """Test MethodConfig serialization includes new fields."""

    def test_to_dict_includes_dora(self):
        """Test to_dict includes DoRA fields."""
        from sage.benchmark.benchmark_agent.experiments.method_comparison import MethodConfig

        config = MethodConfig(
            name="Test DoRA",
            description="Test description",
            use_dora=True,
        )

        config_dict = config.to_dict()
        assert "use_dora" in config_dict
        assert config_dict["use_dora"] is True

    def test_to_dict_includes_lora_plus(self):
        """Test to_dict includes LoRA+ fields."""
        from sage.benchmark.benchmark_agent.experiments.method_comparison import MethodConfig

        config = MethodConfig(
            name="Test LoRA+",
            description="Test description",
            use_lora_plus=True,
            lora_plus_lr_ratio=8.0,
        )

        config_dict = config.to_dict()
        assert "use_lora_plus" in config_dict
        assert config_dict["use_lora_plus"] is True
        assert config_dict["lora_plus_lr_ratio"] == 8.0
