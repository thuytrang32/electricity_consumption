import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.cluster import KMeans
from sklearn.linear_model import Ridge


class RadialBasisFunctionNetwork(BaseEstimator, RegressorMixin):
    def __init__(self, n_centers=20, gamma="scale", alpha=1.0, random_state=42):
        """
        Radial Basis Function Network (RBFN) Regressor.

        Parameters:
        -----------
        n_centers : int, default=20
            Number of radial basis functions (centers of the KMeans clustering).
        gamma : float or 'scale', default='scale'
            The kernel width coefficient. If 'scale', it's calculated based on
            the average distance between the centers.
        alpha : float, default=1.0
            L2 regularization strength for the final Linear/Ridge regression layer.
        random_state : int, default=42
            Random state for KMeans initialization.
        """
        self.n_centers = n_centers
        self.gamma = gamma
        self.alpha = alpha
        self.random_state = random_state
        self.kmeans = None
        self.linear_layer = None
        self.centers_ = None
        self.gamma_ = None

    def _calculate_activations(self, X):
        """Compute the Gaussian activations of X relative to the centers."""
        # Shape of X: (n_samples, n_features)
        # Shape of centers: (n_centers, n_features)
        # Distance calculation using broadcasting: (n_samples, n_centers)
        n_samples = X.shape[0]
        distances = np.zeros((n_samples, self.n_centers))

        for idx, center in enumerate(self.centers_):
            distances[:, idx] = np.linalg.norm(X - center, axis=1)

        # Gaussian radial basis function: phi(r) = exp(-gamma * r^2)
        activations = np.exp(-self.gamma_ * (distances**2))
        return activations

    def fit(self, X, y):
        """
        Fit the RBFN model using KMeans to find centers and Ridge Regression for weights.
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        n_samples, n_features = X.shape

        # Guard: if n_centers > n_samples, restrict n_centers
        effective_centers = min(self.n_centers, n_samples)

        # Step 1: Find centers using KMeans
        self.kmeans = KMeans(
            n_clusters=effective_centers, random_state=self.random_state, n_init="auto"
        )
        self.kmeans.fit(X)
        self.centers_ = self.kmeans.cluster_centers_

        # Step 2: Compute Gamma (kernel width coefficient)
        if self.gamma == "scale":
            # Estimate sigma as the mean distance between centers
            # Or mean distance from points to their nearest center
            distances_between_centers = []
            for i in range(len(self.centers_)):
                for j in range(i + 1, len(self.centers_)):
                    distances_between_centers.append(
                        np.linalg.norm(self.centers_[i] - self.centers_[j])
                    )

            if distances_between_centers:
                mean_dist = np.mean(distances_between_centers)
                # Avoid division by zero
                sigma = mean_dist if mean_dist > 1e-5 else 1.0
            else:
                sigma = 1.0

            self.gamma_ = 1.0 / (2.0 * (sigma**2))
        else:
            self.gamma_ = float(self.gamma)

        # Step 3: Transform inputs to RBF activations
        phi_X = self._calculate_activations(X)

        # Step 4: Fit the output weights using Ridge Regression (linear layer with L2 penalty)
        self.linear_layer = Ridge(alpha=self.alpha)
        self.linear_layer.fit(phi_X, y)

        return self

    def predict(self, X):
        """
        Predict target values using the RBF activations and linear layer.
        """
        X = np.asarray(X, dtype=float)
        if self.centers_ is None or self.linear_layer is None:
            raise ValueError("RBFN model is not fitted yet.")

        phi_X = self._calculate_activations(X)
        return self.linear_layer.predict(phi_X)
