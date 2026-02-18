"""
Options pricing and Greeks calculation using Black-Scholes model.
"""

import numpy as np
from scipy.stats import norm
from datetime import datetime


class OptionCalculator:
    """Black-Scholes option pricing calculator."""

    def __init__(self, S, K, T, r, sigma, option_type="call"):
        """
        Initialize the option calculator.

        Parameters:
        -----------
        S : float
            Spot price (current underlying price)
        K : float
            Strike price
        T : float
            Time to maturity (in years)
        r : float
            Risk-free rate (e.g., 0.05 for 5%)
        sigma : float
            Volatility / Implied Volatility (e.g., 0.20 for 20%)
        option_type : str
            "call" or "put"
        """
        self.S = float(S)
        self.K = float(K)
        self.T = float(T) if T > 0 else 0.00001  # Avoid division by zero
        self.r = float(r)
        self.sigma = float(sigma)
        self.type = option_type.lower()

        # Compute d1 and d2 (Black-Scholes components)
        self.d1 = (
            np.log(self.S / self.K) + (self.r + 0.5 * self.sigma**2) * self.T
        ) / (self.sigma * np.sqrt(self.T))
        self.d2 = self.d1 - self.sigma * np.sqrt(self.T)

    def price(self):
        """Calculate option price using Black-Scholes."""
        if self.type == "call":
            price = (
                self.S * norm.cdf(self.d1)
                - self.K * np.exp(-self.r * self.T) * norm.cdf(self.d2)
            )
        else:  # put
            price = (
                self.K * np.exp(-self.r * self.T) * norm.cdf(-self.d2)
                - self.S * norm.cdf(-self.d1)
            )
        return max(price, 0.0)

    def greeks(self):
        """
        Calculate the Greeks (Delta, Gamma, Theta, Vega, Rho).

        Returns:
        --------
        dict : Dictionary with Greeks rounded to appropriate precision
        """
        # Delta: Rate of change of option price with respect to spot price
        if self.type == "call":
            delta = norm.cdf(self.d1)
        else:  # put
            delta = norm.cdf(self.d1) - 1

        # Gamma: Rate of change of delta with respect to spot price
        gamma = norm.pdf(self.d1) / (self.S * self.sigma * np.sqrt(self.T))

        # Theta: Time decay (per day)
        term1 = -(self.S * norm.pdf(self.d1) * self.sigma) / (
            2 * np.sqrt(self.T)
        )
        if self.type == "call":
            theta = (
                term1
                - self.r
                * self.K
                * np.exp(-self.r * self.T)
                * norm.cdf(self.d2)
            )
        else:  # put
            theta = (
                term1
                + self.r
                * self.K
                * np.exp(-self.r * self.T)
                * norm.cdf(-self.d2)
            )

        # Vega: Sensitivity to volatility (per 1% change in volatility)
        vega = self.S * norm.pdf(self.d1) * np.sqrt(self.T) / 100

        # Rho: Sensitivity to interest rate changes
        if self.type == "call":
            rho = self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(self.d2)
        else:  # put
            rho = (
                -self.K
                * self.T
                * np.exp(-self.r * self.T)
                * norm.cdf(-self.d2)
            )

        return {
            "Delta": round(delta, 3),
            "Gamma": round(gamma, 4),
            "Theta": round(theta / 365, 3),  # Daily theta
            "Vega": round(vega, 3),  # Per 1% vol change
            "Rho": round(rho / 100, 3),  # Per 1% rate change
        }

    def intrinsic_value(self):
        """Calculate intrinsic value (immediate exercise value)."""
        if self.type == "call":
            return max(self.S - self.K, 0.0)
        else:  # put
            return max(self.K - self.S, 0.0)

    def time_value(self):
        """Calculate time value (extrinsic value)."""
        return max(self.price() - self.intrinsic_value(), 0.0)
