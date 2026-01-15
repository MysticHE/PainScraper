"""
Pain point classifier using Ollama with Llama 3.1 8B.
"""
import json
import re
from typing import Optional

import ollama

from config import OLLAMA_CONFIG, CLASSIFICATION_PROMPT, CATEGORIES, AUDIENCES
from database import get_unclassified_posts, insert_classification


def extract_json_from_response(text: str) -> Optional[dict]:
    """
    Extract JSON from LLM response, handling various formats.

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dict or None
    """
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in markdown code block
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object pattern
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def validate_classification(data: dict) -> dict:
    """
    Validate and normalize classification data.

    Args:
        data: Raw classification dict

    Returns:
        Validated classification dict
    """
    validated = {
        "is_pain_point": bool(data.get("is_pain_point", False)),
        "category": None,
        "audience": None,
        "intensity": None,
        "automation_potential": None,
        "suggested_solution": None,
        "keywords": None,
        "summary": None,
    }

    if not validated["is_pain_point"]:
        return validated

    # Validate category
    category = data.get("pain_point_category") or data.get("category")
    if category and category.lower() in [c.lower() for c in CATEGORIES]:
        validated["category"] = category.lower()
    else:
        validated["category"] = "other"

    # Validate audience
    audience = data.get("target_audience") or data.get("audience")
    if audience and audience.lower() in [a.lower() for a in AUDIENCES]:
        validated["audience"] = audience.lower()
    else:
        validated["audience"] = "consumer"

    # Validate intensity (1-10)
    intensity = data.get("intensity")
    if intensity is not None:
        try:
            intensity = int(intensity)
            validated["intensity"] = max(1, min(10, intensity))
        except (ValueError, TypeError):
            validated["intensity"] = 5

    # Validate automation potential
    automation = data.get("automation_potential")
    if automation and automation.lower() in ["low", "medium", "high"]:
        validated["automation_potential"] = automation.lower()
    else:
        validated["automation_potential"] = "medium"

    # Extract other fields
    validated["suggested_solution"] = data.get("suggested_solution")
    validated["summary"] = data.get("summary")

    # Handle keywords
    keywords = data.get("keywords")
    if isinstance(keywords, list):
        validated["keywords"] = [str(k) for k in keywords[:10]]
    elif isinstance(keywords, str):
        validated["keywords"] = [k.strip() for k in keywords.split(",")][:10]

    return validated


class PainPointClassifier:
    """Classifier using Ollama to analyze posts for pain points."""

    def __init__(self):
        self.model = OLLAMA_CONFIG["model"]
        self.client = None
        self._check_ollama()

    def _check_ollama(self):
        """Check if Ollama is running and model is available."""
        try:
            # Test connection
            models = ollama.list()
            model_names = [m.get("name", "") for m in models.get("models", [])]

            if not any(self.model in name for name in model_names):
                print(f"Warning: Model {self.model} not found. Available: {model_names}")
                print(f"Run: ollama pull {self.model}")

            print(f"Ollama connected. Using model: {self.model}")

        except Exception as e:
            print(f"Error connecting to Ollama: {e}")
            print("Make sure Ollama is running: ollama serve")
            raise

    def classify_post(
        self,
        title: str,
        content: str,
        source: str,
    ) -> dict:
        """
        Classify a single post using Ollama.

        Args:
            title: Post title
            content: Post content
            source: Source platform

        Returns:
            Classification dict
        """
        # Prepare prompt
        prompt = CLASSIFICATION_PROMPT.format(
            title=title[:500],
            content=content[:2000],
            source=source,
        )

        try:
            # Call Ollama
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": 500,
                },
            )

            response_text = response.get("response", "")

            # Parse JSON response
            data = extract_json_from_response(response_text)

            if data is None:
                print(f"  Failed to parse JSON from response")
                return {
                    "is_pain_point": False,
                    "raw_response": response_text,
                }

            # Validate and return
            validated = validate_classification(data)
            validated["raw_response"] = response_text

            return validated

        except Exception as e:
            print(f"  Classification error: {e}")
            return {
                "is_pain_point": False,
                "raw_response": str(e),
            }

    def classify_batch(
        self,
        posts: list,
        progress_callback=None,
    ) -> list:
        """
        Classify a batch of posts.

        Args:
            posts: List of post dicts with id, title, content, source
            progress_callback: Optional callback(current, total)

        Returns:
            List of (post_id, classification) tuples
        """
        results = []
        total = len(posts)

        for i, post in enumerate(posts):
            if progress_callback:
                progress_callback(i + 1, total)

            classification = self.classify_post(
                title=post.get("title", ""),
                content=post.get("content", ""),
                source=post.get("source", "unknown"),
            )

            results.append((post["id"], classification))

        return results


def classify_unclassified(limit: int = 100) -> dict:
    """
    Classify all unclassified posts in the database.

    Args:
        limit: Maximum posts to classify

    Returns:
        Statistics dict
    """
    print("\n=== Pain Point Classifier ===")

    # Get unclassified posts
    posts = get_unclassified_posts(limit=limit)

    if not posts:
        print("No unclassified posts found.")
        return {"classified": 0, "pain_points": 0}

    print(f"Found {len(posts)} unclassified posts")

    # Initialize classifier
    classifier = PainPointClassifier()

    # Classify each post
    classified = 0
    pain_points = 0

    def progress(current, total):
        print(f"  Classifying {current}/{total}...", end="\r")

    results = classifier.classify_batch(posts, progress_callback=progress)

    for post_id, classification in results:
        # Save to database
        insert_classification(
            post_id=post_id,
            is_pain_point=classification["is_pain_point"],
            category=classification.get("category"),
            audience=classification.get("audience"),
            intensity=classification.get("intensity"),
            automation_potential=classification.get("automation_potential"),
            suggested_solution=classification.get("suggested_solution"),
            keywords=classification.get("keywords"),
            summary=classification.get("summary"),
            raw_response=classification.get("raw_response"),
        )

        classified += 1
        if classification["is_pain_point"]:
            pain_points += 1

    print(f"\nClassified {classified} posts, found {pain_points} pain points")

    return {
        "classified": classified,
        "pain_points": pain_points,
    }


def test_classifier():
    """Test classifier with sample posts."""
    print("Testing Pain Point Classifier...")

    classifier = PainPointClassifier()

    # Test posts
    test_posts = [
        {
            "title": "So frustrated with MRT delays again",
            "content": "Third time this week the train broke down. Wasted 30 minutes waiting. How is public transport so unreliable in Singapore? Anyone else experiencing this?",
            "source": "reddit/r/singapore",
        },
        {
            "title": "Best chicken rice in Singapore",
            "content": "Looking for recommendations for good chicken rice. Preferably near Orchard area. Thanks!",
            "source": "reddit/r/singapore",
        },
        {
            "title": "SME compliance nightmare",
            "content": "Running a small business here is so hard. The paperwork for ACRA, IRAS, CPF is endless. Takes me 2 days every month just to file everything. Need to hire someone just for compliance.",
            "source": "hwz/edmw",
        },
    ]

    print("\nClassifying test posts:\n")

    for i, post in enumerate(test_posts, 1):
        print(f"--- Test {i}: {post['title'][:50]}... ---")

        result = classifier.classify_post(
            title=post["title"],
            content=post["content"],
            source=post["source"],
        )

        print(f"  Is Pain Point: {result['is_pain_point']}")

        if result["is_pain_point"]:
            print(f"  Category: {result.get('category')}")
            print(f"  Audience: {result.get('audience')}")
            print(f"  Intensity: {result.get('intensity')}")
            print(f"  Automation: {result.get('automation_potential')}")
            print(f"  Solution: {result.get('suggested_solution')}")
            print(f"  Keywords: {result.get('keywords')}")

        print()

    print("Test complete!")


if __name__ == "__main__":
    test_classifier()
