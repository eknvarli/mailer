import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from pathlib import Path
from typing import Dict, Any
import numpy as np


class MailAnalyzer:
    def __init__(self, training_file: str):
        self.vectorizer = TfidfVectorizer()
        self.category_clf = MultinomialNB()
        self.subcategory_clf = MultinomialNB()
        self.priority_clf = MultinomialNB()
        self.sentiment_clf = MultinomialNB()
        self.urgency_clf = MultinomialNB()
        self.department_clf = MultinomialNB()
        self._train(training_file)

    def _train(self, training_file: str):
        training_path = Path(training_file)
        if not training_path.exists():
            raise FileNotFoundError(f"{training_file} bulunamadı.")

        with open(training_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        texts = [x["body"] for x in data]
        categories = [x["category"] for x in data]
        subcategories = [x["subcategory"] for x in data]
        priorities = [x["priority"] for x in data]
        sentiments = [x["sentiment"] for x in data]
        urgencies = [x["urgency"] for x in data]
        departments = [x["department"] for x in data]
        actions_required = [x["action_required"] for x in data]
        response_templates = [x["response_template"] for x in data]

        X = self.vectorizer.fit_transform(texts)

        self.category_clf.fit(X, categories)
        self.subcategory_clf.fit(X, subcategories)
        self.priority_clf.fit(X, priorities)
        self.sentiment_clf.fit(X, sentiments)
        self.urgency_clf.fit(X, urgencies)
        self.department_clf.fit(X, departments)

        self.actions_required_mapping = {item["subcategory"]: item["action_required"] for item in data}
        self.response_templates_mapping = {item["subcategory"]: item["response_template"] for item in data}

    def predict(self, text: str) -> str:
        X_test = self.vectorizer.transform([text])
        return self.category_clf.predict(X_test)[0]

    def predict_detailed(self, text: str) -> Dict[str, Any]:
        X_test = self.vectorizer.transform([text])

        category = self.category_clf.predict(X_test)[0]
        subcategory = self.subcategory_clf.predict(X_test)[0]
        priority = self.priority_clf.predict(X_test)[0]
        sentiment = self.sentiment_clf.predict(X_test)[0]
        urgency = self.urgency_clf.predict(X_test)[0]
        department = self.department_clf.predict(X_test)[0]

        action_required = self.actions_required_mapping.get(subcategory, "inceleme")
        response_template = self.response_templates_mapping.get(subcategory, f"{category}_standard")

        category_confidence = np.max(self.category_clf.predict_proba(X_test))
        subcategory_confidence = np.max(self.subcategory_clf.predict_proba(X_test))
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


if __name__ == "__main__":
    analyzer = MailAnalyzer("training_data.json")
    test_mail = "Siparişim bozuk geldi!"
    print("Basit tahmin:", analyzer.predict(test_mail))

    detailed_result = analyzer.predict_detailed(test_mail)
    print("Detaylı tahmin:")
    for key, value in detailed_result.items():
        print(f"  {key}: {value}")