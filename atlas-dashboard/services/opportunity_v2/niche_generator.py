"""
niche_generator.py — Atlas Autonomous Niche Generator

This is the "idea engine" that feeds the opportunity pipeline.
It replaces static lists with generated market hypotheses.
"""

from typing import List


class NicheGenerator:

    def generate_base_niches(self) -> List[str]:
        """
        Core high-signal categories (seed layer)
        """

        return [
            "pet services",
            "home services",
            "local service businesses",
            "health and wellness services",
            "automotive services",
            "digital marketing services",
            "AI tools for business",
            "personal finance tools",
        ]

    def expand_niche(self, niche: str) -> List[str]:
        """
        Expands a niche into sub-opportunities
        """

        expansions = {
            "pet services": [
                "mobile dog grooming",
                "dog walking service",
                "pet sitting service",
                "dog training classes",
                "dog bakery business"
            ],

            "home services": [
                "pressure washing service",
                "window cleaning business",
                "handyman services",
                "home cleaning service",
                "junk removal service"
            ],

            "automotive services": [
                "mobile car detailing",
                "car wash business",
                "oil change service",
                "windshield repair service"
            ],

            "AI tools for business": [
                "AI resume builder",
                "AI marketing copy generator",
                "AI sales outreach tool",
                "AI SEO content writer"
            ]
        }

        return expansions.get(niche, [])

    def generate(self) -> List[str]:
        """
        Full autonomous generation pipeline
        """

        base = self.generate_base_niches()

        all_niches = []

        for b in base:
            all_niches.append(b)
            all_niches.extend(self.expand_niche(b))

        # remove duplicates while preserving order
        seen = set()
        cleaned = []

        for n in all_niches:
            if n not in seen:
                cleaned.append(n)
                seen.add(n)

        return cleaned