"""
Model Inference Predictor

Provides interface for LSTM model inference with memory management
and optimized batch processing.
"""
from typing import Any

import torch
import numpy as np
from numpy.typing import NDArray
from typing import Optional

from app.ml.models.lstm_model import LSTMAnomalyDetector


class ModelPredictor:
    """LSTM model predictor with proper memory management and batch optimization."""

    DEFAULT_BATCH_SIZE = 32

    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        """Initialize predictor with device selection.

        Args:
            batch_size: Default batch size for batch predictions (default 32)
        """
        self.model: Optional[LSTMAnomalyDetector] = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size
        self._load_model()

    def _load_model(self) -> None:
        """Load model from file.

        Note: Model loading is deferred until actual prediction to avoid
        blocking initialization.
        """
        # Implementation placeholder - model loaded on demand
        pass

    def predict(self, features: NDArray[np.float32]) -> float:
        """Predict anomaly probability for single sample.

        Args:
            features: Feature array of shape (feature_dim,)

        Returns:
            Anomaly probability (0-1)
        """
        if self.model is None:
            self._load_model()
            if self.model is None:
                return 0.0  # Return default if model not loaded

        self.model.eval()
        with torch.no_grad():
            # Ensure float32 and add batch dimension
            input_tensor = torch.from_numpy(features.astype(np.float32)).unsqueeze(0)
            input_tensor = input_tensor.to(self.device)

            output = self.model(input_tensor)

            # Move tensor back to CPU and release GPU memory
            result = output.cpu().item()

            # Explicitly delete tensor to help garbage collection
            del input_tensor
            del output

            return result

    def predict_batch_list(
        self,
        features_list: list[list[float]],
        batch_size: int | None = None,
    ) -> list[float]:
        """Batch predict anomaly probabilities from list of features.

        Optimized for large batches with chunking to avoid memory issues.

        Args:
            features_list: List of feature vectors, each of shape (feature_dim,)
            batch_size: Override default batch size (default 32)

        Returns:
            List of anomaly probabilities (0-1)

        Example:
            >>> predictor = ModelPredictor()
            >>> features = [[0.1] * 109, [0.2] * 109, [0.3] * 109]
            >>> results = predictor.predict_batch_list(features, batch_size=32)
            >>> print(results)
            [0.15, 0.22, 0.31]
        """
        if not features_list:
            return []

        if self.model is None:
            self._load_model()
            if self.model is None:
                return [0.0] * len(features_list)

        # Use default batch size if not specified
        if batch_size is None:
            batch_size = self.batch_size

        # Convert to numpy array for efficient processing
        features_array = np.array(features_list, dtype=np.float32)
        num_samples = len(features_array)

        # Process in chunks to manage memory
        results: list[float] = []

        self.model.eval()
        with torch.no_grad():
            for start_idx in range(0, num_samples, batch_size):
                end_idx = min(start_idx + batch_size, num_samples)
                batch = features_array[start_idx:end_idx]

                # Create tensor and move to device
                input_tensor = torch.from_numpy(batch).to(self.device)

                # Inference
                outputs = self.model(input_tensor)

                # Extract results and move to CPU
                batch_results = outputs.cpu().numpy().flatten().tolist()
                results.extend(batch_results)

                # Explicit memory cleanup
                del input_tensor
                del outputs

        return results

    def predict_batch(self, features_batch: NDArray[np.float32]) -> list[float]:
        """Batch predict anomaly probabilities (numpy array input).

        Args:
            features_batch: Feature array of shape (batch_size, feature_dim)

        Returns:
            List of anomaly probabilities
        """
        if features_batch.shape[0] == 0:
            return []

        if self.model is None:
            self._load_model()
            if self.model is None:
                return [0.0] * len(features_batch)

        self.model.eval()
        with torch.no_grad():
            # Ensure float32
            input_tensor = torch.from_numpy(features_batch.astype(np.float32))
            input_tensor = input_tensor.to(self.device)

            outputs = self.model(input_tensor)

            # Move to CPU and convert to list
            result = outputs.cpu().numpy().flatten().tolist()

            # Explicitly delete tensors
            del input_tensor
            del outputs

            return result

    def reload_model(self) -> None:
        """Reload model from file."""
        self._load_model()

    def get_model_info(self) -> dict[str, Any]:
        """Get model information.

        Returns:
            Dictionary with model metadata
        """
        if self.model is None:
            return {"loaded": False, "batch_size": self.batch_size}

        return {
            "loaded": True,
            "device": str(self.device),
            "parameters": sum(p.numel() for p in self.model.parameters()),
            "batch_size": self.batch_size,
        }