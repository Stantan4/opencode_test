"""
Unit Tests for LSTM Model

Tests cover:
1. Model initialization (different parameters)
2. Forward pass (input dimension validation)
3. Training process (loss should decrease)
4. Model save and load (predictions should match after reload)
5. Edge cases (all-zero input, extreme values)
"""
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch
from torch.utils.data import DataLoader, TensorDataset

from app.ml.models.lstm_model import LSTMAnomalyDetector, create_model


class TestLSTMModelInitialization:
    """Test model initialization with different parameters."""

    def test_default_initialization(self):
        """Test default parameters."""
        model = LSTMAnomalyDetector(input_dim=109)
        assert model.input_dim == 109
        assert model.hidden_dim == 128
        assert model.num_layers == 2
        assert model.dropout_rate == 0.3

    def test_custom_parameters(self):
        """Test custom hidden_dim and num_layers."""
        model = LSTMAnomalyDetector(
            input_dim=109,
            hidden_dim=256,
            num_layers=3,
            dropout=0.5,
            num_device_types=50,
        )
        assert model.hidden_dim == 256
        assert model.num_layers == 3
        assert model.dropout_rate == 0.5
        assert model.num_device_types == 50

    def test_parameter_count(self):
        """Test that model has correct number of parameters."""
        model = LSTMAnomalyDetector(input_dim=109, hidden_dim=64, num_layers=2)
        param_count = sum(p.numel() for p in model.parameters())
        assert param_count > 0

    def test_model_creation_helper(self):
        """Test create_model helper function."""
        model = create_model(input_dim=109, hidden_dim=64)
        assert isinstance(model, LSTMAnomalyDetector)
        assert model.hidden_dim == 64


class TestLSTMModelForward:
    """Test forward pass and input validation."""

    def test_forward_output_shape(self):
        """Test forward pass output shape."""
        model = LSTMAnomalyDetector(input_dim=109)
        model.eval()

        batch_size = 4
        seq_len = 30
        input_tensor = torch.randn(batch_size, seq_len, 109)

        with torch.no_grad():
            output = model(input_tensor)

        assert output.shape == (batch_size, 1)

    def test_single_sample_input(self):
        """Test single sample input (batch_size=1)."""
        model = LSTMAnomalyDetector(input_dim=109)
        model.eval()

        input_tensor = torch.randn(1, 30, 109)

        with torch.no_grad():
            output = model(input_tensor)

        assert output.shape == (1, 1)

    def test_invalid_input_dim_raises(self):
        """Test that invalid input dimension raises error."""
        model = LSTMAnomalyDetector(input_dim=109)
        model.eval()

        # Wrong dimension (expected 109, got 50)
        input_tensor = torch.randn(2, 30, 50)

        # Should raise RuntimeError due to dimension mismatch
        with pytest.raises(RuntimeError, match="input.size\\(-1\\)"):
            with torch.no_grad():
                model(input_tensor)

    def test_predict_method(self):
        """Test predict method returns correct shape."""
        model = LSTMAnomalyDetector(input_dim=109)
        model.eval()

        input_tensor = torch.randn(3, 30, 109)
        predictions = model.predict(input_tensor)

        assert predictions.shape == (3,)


class TestLSTMModelTraining:
    """Test training process and loss convergence."""

    @pytest.fixture
    def training_data(self):
        """Create simple training data."""
        np.random.seed(42)
        torch.manual_seed(42)

        # Generate synthetic data
        num_samples = 100
        seq_len = 30
        input_dim = 109

        # Normal samples (label=0)
        X_normal = torch.randn(num_samples, seq_len, input_dim) * 0.5
        y_normal = torch.zeros(num_samples)

        # Anomalous samples (label=1)
        X_anomaly = torch.randn(num_samples, seq_len, input_dim) * 2 + 5
        y_anomaly = torch.ones(num_samples)

        X = torch.cat([X_normal, X_anomaly], dim=0)
        y = torch.cat([y_normal, y_anomaly], dim=0)

        # Create data loaders
        dataset = TensorDataset(X, y)
        train_loader = DataLoader(dataset, batch_size=16, shuffle=True)

        return train_loader

    def test_training_decreases_loss(self, training_data):
        """Test that training decreases loss."""
        model = LSTMAnomalyDetector(input_dim=109, hidden_dim=32, num_layers=1)

        # Train for a few epochs
        history = model.train_model(
            train_loader=training_data,
            epochs=5,
            learning_rate=0.01,
            device="cpu",
        )

        # Check that loss generally decreases
        initial_loss = history["train_loss"][0]
        final_loss = history["train_loss"][-1]

        assert final_loss < initial_loss, "Loss should decrease during training"

    def test_validation_loss_exists(self, training_data):
        """Test that validation loss is recorded."""
        # Split data for train/val
        X_list = []
        y_list = []
        for X, y in training_data:
            X_list.append(X)
            y_list.append(y)

        X_all = torch.cat(X_list, dim=0)
        y_all = torch.cat(y_list, dim=0)

        # Create train/val split
        split_idx = int(len(X_all) * 0.8)
        X_train, X_val = X_all[:split_idx], X_all[split_idx:]
        y_train, y_val = y_all[:split_idx], y_all[split_idx:]

        train_ds = TensorDataset(X_train, y_train)
        val_ds = TensorDataset(X_val, y_val)

        train_loader = DataLoader(train_ds, batch_size=16)
        val_loader = DataLoader(val_ds, batch_size=16)

        model = LSTMAnomalyDetector(input_dim=109, hidden_dim=32, num_layers=1)

        history = model.train_model(
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=3,
            learning_rate=0.01,
            device="cpu",
        )

        assert "val_loss" in history
        assert len(history["val_loss"]) > 0


class TestLSTMModelSaveLoad:
    """Test model save and load functionality."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained model for testing."""
        model = LSTMAnomalyDetector(input_dim=109, hidden_dim=32, num_layers=1)

        # Create simple training data
        X = torch.randn(20, 30, 109)
        y = torch.randint(0, 2, (20,)).float()
        dataset = TensorDataset(X, y)
        loader = DataLoader(dataset, batch_size=8)

        # Train briefly
        model.train_model(loader, epochs=1, device="cpu")

        return model

    def test_save_and_load_model(self, trained_model):
        """Test that save and load produces consistent predictions."""
        # Create test input
        test_input = torch.randn(5, 30, 109)

        # Get predictions before save
        trained_model.eval()
        with torch.no_grad():
            pred_before = trained_model.predict(test_input).numpy()

        # Save model to temp file
        with tempfile.NamedTemporaryFile(suffix=".pth", delete=False) as f:
            model_path = f.name

        try:
            trained_model.save_model(model_path)

            # Load model
            loaded_model = LSTMAnomalyDetector.load_model(model_path, device="cpu")
            loaded_model.eval()

            # Get predictions after load
            with torch.no_grad():
                pred_after = loaded_model.predict(test_input).numpy()

            # Compare predictions
            np.testing.assert_allclose(pred_before, pred_after, rtol=1e-5)
        finally:
            # Cleanup
            os.remove(model_path)
            json_path = model_path.replace(".pth", ".json")
            if os.path.exists(json_path):
                os.remove(json_path)

    def test_save_creates_metadata_file(self, trained_model):
        """Test that save creates metadata JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".pth", delete=False) as f:
            model_path = f.name

        try:
            trained_model.save_model(model_path)

            # Check metadata file exists
            metadata_path = model_path.replace(".pth", ".json")
            assert os.path.exists(metadata_path)
        finally:
            os.remove(model_path)
            json_path = model_path.replace(".pth", ".json")
            if os.path.exists(json_path):
                os.remove(json_path)


class TestLSTMModelEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_zero_input(self):
        """Test model with all-zero input."""
        model = LSTMAnomalyDetector(input_dim=109)
        model.eval()

        # All zeros
        zero_input = torch.zeros(3, 30, 109)

        with torch.no_grad():
            output = model(zero_input)

        # Should not raise, output in valid range
        assert output.shape == (3, 1)
        assert (output >= 0).all() and (output <= 1).all()

    def test_all_ones_input(self):
        """Test model with all-ones input."""
        model = LSTMAnomalyDetector(input_dim=109)
        model.eval()

        # All ones
        ones_input = torch.ones(3, 30, 109)

        with torch.no_grad():
            output = model(ones_input)

        assert output.shape == (3, 1)
        assert (output >= 0).all() and (output <= 1).all()

    def test_extreme_values_input(self):
        """Test model with extreme values."""
        model = LSTMAnomalyDetector(input_dim=109)
        model.eval()

        # Very large values
        extreme_input = torch.randn(3, 30, 109) * 1000

        with torch.no_grad():
            output = model(extreme_input)

        assert output.shape == (3, 1)
        assert (output >= 0).all() and (output <= 1).all()

    def test_single_timestep_sequence(self):
        """Test with minimum sequence length."""
        model = LSTMAnomalyDetector(input_dim=109)
        model.eval()

        # Single timestep
        single_ts_input = torch.randn(2, 1, 109)

        with torch.no_grad():
            output = model(single_ts_input)

        assert output.shape == (2, 1)

    def test_gradient_flow(self):
        """Test that gradients flow through model."""
        model = LSTMAnomalyDetector(input_dim=109)

        input_tensor = torch.randn(2, 30, 109, requires_grad=True)
        output = model(input_tensor)
        loss = output.sum()
        loss.backward()

        # Check that gradients exist
        assert input_tensor.grad is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])