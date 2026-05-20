import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import os

class AcademicRecommender:
    def __init__(self, resources_csv='resources.csv'):
        if not os.path.exists(resources_csv):
            raise FileNotFoundError(f"Error: The file '{resources_csv}' was not found.")
            
        self.df = pd.read_csv(resources_csv)
        self._preprocess_data()
        self._train_vectorizer()

    def _preprocess_data(self):
        self.df = self.df.fillna('')
        self.df['features'] = (
            self.df['title'].str.lower() + ' ' +
            self.df['topic'].str.lower() + ' ' +
            self.df['level'].str.lower() + ' ' +
            self.df['type'].str.lower() + ' ' +
            self.df['tags'].str.lower()
        )
        self.df['features'] = self.df['features'].apply(lambda x: re.sub(r'\s+', ' ', x).strip())

    def _train_vectorizer(self):
        self.tfidf_vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.df['features'])

    def recommend(self, query, top_n=10):
        processed_query = query.lower()
        query_vec = self.tfidf_vectorizer.transform([processed_query])
        cosine_similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = cosine_similarities.argsort()[-top_n:][::-1]
        
        recommendations = self.df.iloc[top_indices].copy()
        recommendations['similarity_score'] = cosine_similarities[top_indices]
        
        if 'paid' not in recommendations.columns:
            recommendations['paid'] = False 
        
        return recommendations[['title', 'topic', 'level', 'type', 'url', 'paid', 'similarity_score']].to_dict(orient='records')

    def get_personalized_recommendations(self, user_id, top_n=5):
        try:
            bookmarks_df = pd.read_csv('bookmarks.csv')
            user_bookmarks = bookmarks_df[bookmarks_df['user_id'] == int(user_id)]
        except (FileNotFoundError, pd.errors.EmptyDataError):
            return []

        if user_bookmarks.empty:
            return []

        bookmarked_titles = user_bookmarks['resource_title'].tolist()
        bookmarked_features = self.df[self.df['title'].isin(bookmarked_titles)]['features']
    
        if bookmarked_features.empty:
            return []

        user_profile_query = ' '.join(bookmarked_features)
        recommendations = self.recommend(user_profile_query, top_n=top_n + len(bookmarked_titles))
        personalized_recs = [rec for rec in recommendations if rec['title'] not in bookmarked_titles]
    
        return personalized_recs[:top_n]