"""Premium product-launch styling."""

from .base import StyleTemplate


class PremiumStyle(StyleTemplate):
    def __init__(self):
        super().__init__(
            name="premium",
            accent="#7063f2",
            background="#11111a",
            secondary="#ffffff",
            transition="Soft cinematic dissolve with restrained UI motion",
        )