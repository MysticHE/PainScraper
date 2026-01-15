"""
Cloud-based classifier using Groq API (free tier available).
Alternative to local Ollama for cloud deployment.
"""
import os
import json
import re
from typing import Optional

import requests

from config import CLASSIFICATION_PROMPT, CATEGORIES, AUDIENCES
from database import get_unclassified_posts, insert_classification


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def extract_json_from_response(text: str) -> Optional[dict]:
    """Extract JSON from LLM response."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def validate_classification(data: dict) -> dict:
    """Validate and normalize classification data."""
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

    category = data.get("pain_point_category") or data.get("category")
    if category and category.lower() in [c.lower() for c in CATEGORIES]:
        validated["category"] = category.lower()
    else:
        validated["category"] = "other"

    audience = data.get("target_audience") or data.get("audience")
    if audience and audience.lower() in [a.lower() for a in AUDIENCES]:
        validated["audience"] = audience.lower()
    else:
        validated["audience"] = "consumer"

    intensity = data.get("intensity")
    if intensity is not None:
        try:
            intensity = int(intensity)
            validated["intensity"] = max(1, min(10, intensity))
        except (ValueError, TypeError):
            validated["intensity"] = 5

    automation = data.get("automation_potential")
    if automation and automation.lower() in ["low", "medium", "high"]:
        validated["automation_potential"] = automation.lower()
    else:
        validated["automation_potential"] = "medium"

    validated["suggested_solution"] = data.get("suggested_solution")
    validated["summary"] = data.get("summary")

    keywords = data.get("keywords")
    if isinstance(keywords, list):
        validated["keywords"] = [str(k) for k in keywords[:10]]
    elif isinstance(keywords, str):
        validated["keywords"] = [k.strip() for k in keywords.split(",")][:10]

    return validated


class CloudClassifier:
    """Classifier using Groq API for cloud deployment."""

    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.api_key = GROQ_API_KEY
        self.model = GROQ_MODEL
        print(f"Groq API initialized. Using model: {self.model}")

    def classify_post(self, title: str, content: str, source: str) -> dict:
        """Classify a single post using Groq API."""
        prompt = CLASSIFICATION_PROMPT.format(
            title=title[:500],
            content=content[:2000],
            source=source,
        )

        try:
            response = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            response_text = result["choices"][0]["message"]["content"]

            data = extract_json_from_response(response_text)

            if data is None:
                print(f"  Failed to parse JSON from response")
                return {"is_pain_point": False, "raw_response": response_text}

            validated = validate_classification(data)
            validated["raw_response"] = response_text
            return validated

        except Exception as e:
            print(f"  Classification error: {e}")
            return {"is_pain_point": False, "raw_response": str(e)}

    def classify_batch(self, posts: list, progress_callback=None) -> list:
        """Classify a batch of posts."""
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


def classify_unclassified_cloud(limit: int = 100) -> dict:
    """Classify unclassified posts using cloud API."""
    print("\n=== Cloud Pain Point Classifier (Groq) ===")

    posts = get_unclassified_posts(limit=limit)

    if not posts:
        print("No unclassified posts found.")
        return {"classified": 0, "pain_points": 0}

    print(f"Found {len(posts)} unclassified posts")

    classifier = CloudClassifier()
    classified = 0
    pain_points = 0

    def progress(current, total):
        print(f"  Classifying {current}/{total}...", end="\r")

    results = classifier.classify_batch(posts, progress_callback=progress)

    for post_id, classification in results:
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
    return {"classified": classified, "pain_points": pain_points}


if __name__ == "__main__":
    classify_unclassified_cloud()
