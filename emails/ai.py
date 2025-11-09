import json
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from typing import Dict, Any
import numpy as np


class EmailAnalyzer:
    def __init__(self):
        self.vectorizer = CountVectorizer()
        self.category_model = MultinomialNB()
        self.subcategory_model = MultinomialNB()
        self.priority_model = MultinomialNB()
        self.sentiment_model = MultinomialNB()
        self.urgency_model = MultinomialNB()
        self.department_model = MultinomialNB()
        self.trained = False
        self.training_data = []

    def train_from_file(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            self.training_data = json.load(f)

        texts = [item["body"] for item in self.training_data]
        categories = [item["category"] for item in self.training_data]
        subcategories = [item["subcategory"] for item in self.training_data]
        priorities = [item["priority"] for item in self.training_data]
        sentiments = [item["sentiment"] for item in self.training_data]
        urgencies = [item["urgency"] for item in self.training_data]
        departments = [item["department"] for item in self.training_data]
        actions_required = [item["action_required"] for item in self.training_data]
        response_templates = [item["response_template"] for item in self.training_data]

        X = self.vectorizer.fit_transform(texts)

        self.category_model.fit(X, categories)
        self.subcategory_model.fit(X, subcategories)
        self.priority_model.fit(X, priorities)
        self.sentiment_model.fit(X, sentiments)
        self.urgency_model.fit(X, urgencies)
        self.department_model.fit(X, departments)

        self.actions_required_mapping = {item["subcategory"]: item["action_required"] for item in self.training_data}
        self.response_templates_mapping = {item["subcategory"]: item["response_template"] for item in
                                           self.training_data}

        self.trained = True

    def predict(self, text: str) -> str:
        if not self.trained:
            raise ValueError("Model not trained yet")
        X = self.vectorizer.transform([text])
        return self.category_model.predict(X)[0]

    def predict_detailed(self, text: str) -> Dict[str, Any]:
        if not self.trained:
            raise ValueError("Model not trained yet")

        X = self.vectorizer.transform([text])

        category = self.category_model.predict(X)[0]
        subcategory = self.subcategory_model.predict(X)[0]
        priority = self.priority_model.predict(X)[0]
        sentiment = self.sentiment_model.predict(X)[0]
        urgency = self.urgency_model.predict(X)[0]
        department = self.department_model.predict(X)[0]

        action_required = self.actions_required_mapping.get(subcategory, "inceleme")
        response_template = self.response_templates_mapping.get(subcategory, f"{category}_standard")

        category_confidence = np.max(self.category_model.predict_proba(X))
        subcategory_confidence = np.max(self.subcategory_model.predict_proba(X))
        overall_confidence = (category_confidence + subcategory_confidence) / 2

        return {
            "category": category,
            "subcategory": subcategory,
            "priority": priority,
            "sentiment": sentiment,
            "urgency": urgency,
            "department": department,
            "action_required": action_required,
            "response_template": response_template,
            "confidence_score": round(overall_confidence, 4)
        }


analyzer = EmailAnalyzer()
analyzer.train_from_file("training_data.json")