"""
LSTM Anomaly Detection Model for Account Risk Early Warning System.

This module implements a bidirectional LSTM with attention mechanism for detecting
anomalous user behavior patterns in social media accounts.
"""
import json
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


class AttentionLayer(nn.Module):
    """Attention mechanism for LSTM outputs."""

    def __init__(self, hidden_dim: int) -> None:
        """Initialize attention layer.

        Args:
            hidden_dim: Hidden dimension of LSTM output
        """
        super(AttentionLayer, self).__init__()
        self.attention = nn.Linear(hidden_dim, 1)

    def forward(self, lstm_output: torch.Tensor) -> torch.Tensor:
        """Compute attention-weighted output.

        Args:
            lstm_output: LSTM output tensor of shape (batch, seq_len, hidden_dim)

        Returns:
            Attention-weighted tensor of shape (batch, hidden_dim)
        """
        # Compute attention scores
        attention_scores = self.attention(lstm_output)  # (batch, seq_len, 1)
        attention_weights = torch.softmax(attention_scores, dim=1)  # (batch, seq_len, 1)

        # Apply attention weights
        weighted = lstm_output * attention_weights  # (batch, seq_len, hidden_dim)
        output = torch.sum(weighted, dim=1)  # (batch, hidden_dim)

        return output


class LSTMAnomalyDetector(nn.Module):
    """LSTM-based anomaly detection model with bidirectional layers and attention.

    Input: User behavior sequence (time_steps=30, feature_dim=N+8)
        - Login time (normalized 0-23 hours): 1 dimension
        - Login location (normalized lat/lon): 2 dimensions
        - Device fingerprint (one-hot): N dimensions (configurable)
        - Operation type (one-hot: post/comment/dm/login): 4 dimensions
        - Operation interval (log-normalized): 1 dimension

    Output: Anomaly probability (float between 0-1)
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        num_device_types: int = 100,
    ) -> None:
        """Initialize LSTM anomaly detector.

        Args:
            input_dim: Input feature dimension
            hidden_dim: Hidden layer dimension
            num_layers: Number of LSTM layers
            dropout: Dropout rate
            num_device_types: Number of device type categories for one-hot encoding
        """
        super(LSTMAnomalyDetector, self).__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout_rate = dropout
        self.num_device_types = num_device_types

        # Bidirectional LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True,
        )

        # Attention mechanism
        self.attention = AttentionLayer(hidden_dim * 2)  # *2 for bidirectional

        # Fully connected layers
        self.fc1 = nn.Linear(hidden_dim * 2, 64)
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(64, 16)
        self.fc3 = nn.Linear(16, 1)

        # Output activation
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass of the model.

        Args:
            x: Input tensor of shape (batch, seq_len, input_dim)

        Returns:
            Anomaly probability tensor of shape (batch, 1)
        """
        # LSTM layer
        lstm_out, _ = self.lstm(x)  # (batch, seq_len, hidden_dim * 2)

        # Attention mechanism
        attention_out = self.attention(lstm_out)  # (batch, hidden_dim * 2)

        # Fully connected layers
        out = self.fc1(attention_out)
        out = torch.relu(out)
        out = self.dropout(out)

        out = self.fc2(out)
        out = torch.relu(out)
        out = self.dropout(out)

        out = self.fc3(out)
        out = self.sigmoid(out)

        return out

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """Predict anomaly probability for input sequence.

        Args:
            x: Input tensor of shape (batch, seq_len, input_dim) or (seq_len, input_dim)

        Returns:
            Anomaly probability tensor of shape (batch,) or scalar
        """
        self.eval()
        with torch.no_grad():
            output = self.forward(x)
        return output.squeeze(-1)

    def train_model(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader | None = None,
        epochs: int = 50,
        learning_rate: float = 0.001,
        device: str = "cpu",
        early_stopping_patience: int = 10,
    ) -> dict[str, list[float]]:
        """Train the anomaly detection model.

        Args:
            train_loader: Training data loader
            val_loader: Validation data loader (optional)
            epochs: Number of training epochs
            learning_rate: Learning rate for optimizer
            device: Device to train on ('cpu' or 'cuda')
            early_stopping_patience: Epochs to wait before early stopping

        Returns:
            Training history dictionary with 'train_loss' and 'val_loss' lists
        """
        self.to(device)
        self.train()

        optimizer = torch.optim.Adam(self.parameters(), lr=learning_rate)
        criterion = nn.BCELoss()

        history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}
        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(epochs):
            # Training phase
            self.train()
            train_loss = 0.0

            for batch_x, batch_y in train_loader:
                batch_x = batch_x.to(device)
                batch_y = batch_y.to(device)

                optimizer.zero_grad()
                outputs = self(batch_x).squeeze(-1)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                train_loss += loss.item()

            avg_train_loss = train_loss / len(train_loader)
            history["train_loss"].append(avg_train_loss)

            # Validation phase
            if val_loader is not None:
                self.eval()
                val_loss = 0.0

                with torch.no_grad():
                    for batch_x, batch_y in val_loader:
                        batch_x = batch_x.to(device)
                        batch_y = batch_y.to(device)

                        outputs = self(batch_x).squeeze(-1)
                        loss = criterion(outputs, batch_y)
                        val_loss += loss.item()

                avg_val_loss = val_loss / len(val_loader)
                history["val_loss"].append(avg_val_loss)

                # Early stopping check
                if avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1

                if patience_counter >= early_stopping_patience:
                    break

        return history

    def save_model(self, path: str | Path) -> None:
        """Save model state and metadata to file.

        Args:
            path: Path to save the model file
        """
        model_path = Path(path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # Save model state
        torch.save(self.state_dict(), model_path)

        # Save metadata
        metadata = {
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "dropout": self.dropout_rate,
            "num_device_types": self.num_device_types,
        }
        metadata_path = model_path.with_suffix(".json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    @classmethod
    def load_model(
        cls,
        path: str | Path,
        device: str = "cpu",
    ) -> "LSTMAnomalyDetector":
        """Load model from file.

        Args:
            path: Path to the model file
            device: Device to load the model to

        Returns:
            Loaded LSTMAnomalyDetector model instance
        """
        model_path = Path(path)

        # Load metadata
        metadata_path = model_path.with_suffix(".json")
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Create model instance
        model = cls(
            input_dim=metadata["input_dim"],
            hidden_dim=metadata["hidden_dim"],
            num_layers=metadata["num_layers"],
            dropout=metadata["dropout"],
            num_device_types=metadata.get("num_device_types", 100),
        )

        # Load state dict
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.to(device)
        model.eval()

        return model


def create_model(
    input_dim: int,
    hidden_dim: int = 128,
    num_layers: int = 2,
    dropout: float = 0.3,
    num_device_types: int = 100,
) -> LSTMAnomalyDetector:
    """Create LSTM anomaly detector model instance.

    Args:
        input_dim: Input feature dimension
        hidden_dim: Hidden layer dimension
        num_layers: Number of LSTM layers
        dropout: Dropout rate
        num_device_types: Number of device type categories

    Returns:
        LSTMAnomalyDetector model instance
    """
    return LSTMAnomalyDetector(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        dropout=dropout,
        num_device_types=num_device_types,
    )


def prepare_dummy_data(
    num_samples: int = 1000,
    seq_len: int = 30,
    input_dim: int = 109,
    anomaly_ratio: float = 0.1,
) -> tuple[DataLoader, DataLoader]:
    """Prepare dummy training data for testing.

    Args:
        num_samples: Number of samples to generate
        seq_len: Sequence length (time steps)
        input_dim: Input feature dimension
        anomaly_ratio: Ratio of anomalous samples

    Returns:
        Tuple of (train_loader, val_loader)
    """
    # Generate random data
    X = torch.randn(num_samples, seq_len, input_dim)
    y = (torch.randn(num_samples) < -anomaly_ratio).float()

    # Split into train/val
    split_idx = int(num_samples * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]

    train_dataset = TensorDataset(X_train, y_train)
    val_dataset = TensorDataset(X_val, y_val)

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    return train_loader, val_loader


if __name__ == "__main__":
    # Test model creation and training
    print("Testing LSTM Anomaly Detector...")

    # Create model with default input_dim (109 = 1 + 2 + 100 + 4 + 1)
    # 1 (login time) + 2 (location) + 100 (device fingerprint) + 4 (operation type) + 1 (interval)
    input_dim = 109
    model = create_model(input_dim=input_dim)

    # Print model summary
    print(f"Model created with input_dim={input_dim}")
    print(f"Total parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Prepare dummy data
    train_loader, val_loader = prepare_dummy_data(num_samples=200, input_dim=input_dim)

    # Train for 2 epochs (quick test)
    history = model.train_model(
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=2,
        learning_rate=0.001,
    )

    print(f"Training completed. Final train loss: {history['train_loss'][-1]:.4f}")
    print(f"Final val loss: {history['val_loss'][-1]:.4f}")

    # Test prediction
    test_input = torch.randn(1, 30, input_dim)
    prediction = model.predict(test_input)
    print(f"Test prediction: {prediction.item():.4f}")

    # Test save/load
    model.save_model("models/test_model.pth")
    loaded_model = LSTMAnomalyDetector.load_model("models/test_model.pth")
    print("Model save/load test passed!")

    # Cleanup test model
    import shutil
    shutil.rmtree("models", ignore_errors=True)
    print("All tests passed!")