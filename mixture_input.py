# MIT License
#
# Copyright (c) [2026] [Alan A. Smith]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



from dataclasses import dataclass
from typing import List

@dataclass
class MixtureInput:
    T: List[float]          # melting points (°C)
    DH: List[float]         # heats of fusion (kJ/mol)
    X: List[float]          # mole fractions
    case_id: str = None
    modes: List[str] = None # "SVL" or "PD"
    use_bracket: bool = True

    @property
    def n_components(self):
        return len(self.T)

    def copy(self):
        """Return a deep-ish copy of the mixture so cascade can mutate safely."""
        return MixtureInput(
            T=self.T[:],
            DH=self.DH[:],
            X=self.X[:],
            case_id=self.case_id,
            modes=self.modes[:] if self.modes else None,
            use_bracket=self.use_bracket
        )

    def active_components(self):
        """Return indices of components still present (X > 0)."""
        return [i for i, x in enumerate(self.X) if x > 1e-12]

    def remove_component(self, idx):
        """
        Remove a component from the mixture by zeroing it and renormalising.
        This matches your VBA logic exactly.
        """
        self.X[idx] = 0.0
        s = sum(self.X)
        if s > 0:
            self.X = [x / s for x in self.X]
