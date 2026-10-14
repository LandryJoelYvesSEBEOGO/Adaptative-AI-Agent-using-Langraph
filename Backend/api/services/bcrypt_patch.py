"""
Patch pour corriger l'incompatibilité entre passlib 1.7.4 et bcrypt 4.x+
Ce patch doit être importé avant passlib pour éviter l'erreur AttributeError.
"""

import sys
import warnings

# Importer bcrypt et appliquer le patch immédiatement
import bcrypt

# Créer l'attribut __about__ manquant pour compatibilité avec passlib
if not hasattr(bcrypt, "__about__"):

    class _About:
        """Objet de compatibilité pour passlib."""

        __version__ = getattr(bcrypt, "__version__", "4.0.0")

    bcrypt.__about__ = _About()  # type: ignore[attr-defined]

# Supprimer les warnings de passlib concernant bcrypt
warnings.filterwarnings("ignore", message=".*bcrypt.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*trapped.*", category=UserWarning)

# S'assurer que le module bcrypt dans sys.modules a aussi le patch
if "bcrypt" in sys.modules:
    sys.modules["bcrypt"].__about__ = bcrypt.__about__  # type: ignore[attr-defined]
