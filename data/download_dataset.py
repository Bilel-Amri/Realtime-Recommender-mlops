"""
Dataset Download and Preprocessing Script

Downloads MovieLens or Amazon dataset and prepares it for the recommendation system.
For demonstration, we'll use MovieLens-100K (smaller, faster, publicly accessible).
"""

import os
import zipfile
import urllib.request
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetDownloader:
    """Downloads and prepares recommendation dataset."""
    
    def __init__(self, data_dir: str = "./raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def download_movielens(self, size="100k"):
        """
        Download MovieLens dataset.
        
        Args:
            size: "100k", "1m", or "25m"
        """
        urls = {
            "100k": "https://files.grouplens.org/datasets/movielens/ml-100k.zip",
            "1m": "https://files.grouplens.org/datasets/movielens/ml-1m.zip",
            "25m": "https://files.grouplens.org/datasets/movielens/ml-25m.zip"
        }
        
        if size not in urls:
            raise ValueError(f"Invalid size. Choose from {list(urls.keys())}")
        
        url = urls[size]
        zip_path = self.data_dir / f"ml-{size}.zip"
        extract_dir = self.data_dir / f"ml-{size}"
        
        # Download
        if not zip_path.exists():
            logger.info(f"Downloading MovieLens-{size} from {url}...")
            urllib.request.urlretrieve(url, zip_path)
            logger.info(f"Downloaded to {zip_path}")
        
        # Extract
        if not extract_dir.exists():
            logger.info(f"Extracting to {extract_dir}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.data_dir)
            logger.info("Extraction complete")
        
        return extract_dir


class DataPreprocessor:
    """Preprocesses raw dataset for recommendation system."""
    
    def __init__(self, raw_dir: Path, output_dir: str = "./processed"):
        self.raw_dir = raw_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def preprocess_movielens_100k(self):
        """Preprocess MovieLens-100K dataset."""
        logger.info("Preprocessing MovieLens-100K...")
        
        # Load ratings
        ratings_file = self.raw_dir / "ml-100k" / "u.data"
        ratings = pd.read_csv(
            ratings_file,
            sep='\t',
            names=['user_id', 'item_id', 'rating', 'timestamp'],
            encoding='latin-1'
        )
        
        # Load movies
        movies_file = self.raw_dir / "ml-100k" / "u.item"
        movies = pd.read_csv(
            movies_file,
            sep='|',
            names=['item_id', 'title', 'release_date', 'video_release_date', 'imdb_url',
                   'unknown', 'Action', 'Adventure', 'Animation', 'Children', 'Comedy',
                   'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror',
                   'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western'],
            encoding='latin-1',
            engine='python'
        )
        
        # Load users
        users_file = self.raw_dir / "ml-100k" / "u.user"
        users = pd.read_csv(
            users_file,
            sep='|',
            names=['user_id', 'age', 'gender', 'occupation', 'zip_code'],
            encoding='latin-1'
        )
        
        logger.info(f"Loaded {len(ratings)} ratings, {len(movies)} movies, {len(users)} users")
        
        # Create interactions dataframe
        interactions = ratings.copy()
        interactions['timestamp'] = pd.to_datetime(interactions['timestamp'], unit='s')
        
        # Normalize user/item IDs to start from 0
        user_mapping = {old: new for new, old in enumerate(ratings['user_id'].unique())}
        item_mapping = {old: new for new, old in enumerate(ratings['item_id'].unique())}
        
        interactions['user_idx'] = interactions['user_id'].map(user_mapping)
        interactions['item_idx'] = interactions['item_id'].map(item_mapping)
        
        # Convert ratings to implicit feedback (1 if rating >= 4, 0 otherwise)
        interactions['implicit_feedback'] = (interactions['rating'] >= 4).astype(int)
        
        # Add engagement score (normalized rating)
        interactions['engagement'] = interactions['rating'] / 5.0
        
        # Process item features
        genre_cols = ['unknown', 'Action', 'Adventure', 'Animation', 'Children', 'Comedy',
                      'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror',
                      'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western']
        
        items = movies[['item_id', 'title'] + genre_cols].copy()
        items['item_idx'] = items['item_id'].map(item_mapping)
        
        # Calculate popularity
        item_popularity = interactions.groupby('item_idx').size().reset_index(name='popularity')
        items = items.merge(item_popularity, on='item_idx', how='left')
        items['popularity'] = items['popularity'].fillna(0)
        
        # Process user features
        users['user_idx'] = users['user_id'].map(user_mapping)
        
        # Calculate user activity
        user_activity = interactions.groupby('user_idx').size().reset_index(name='activity_count')
        users = users.merge(user_activity, on='user_idx', how='left')
        users['activity_count'] = users['activity_count'].fillna(0)
        
        # Encode categorical features
        users['gender_encoded'] = users['gender'].map({'M': 0, 'F': 1})
        users['occupation_encoded'] = users['occupation'].astype('category').cat.codes
        
        # Save processed files
        interactions_path = self.output_dir / "interactions.csv"
        items_path = self.output_dir / "items.csv"
        users_path = self.output_dir / "users.csv"
        mappings_path = self.output_dir / "mappings.csv"
        
        interactions.to_csv(interactions_path, index=False)
        items.to_csv(items_path, index=False)
        users.to_csv(users_path, index=False)
        
        # Save mappings for reverse lookup
        mappings = pd.DataFrame({
            'original_user_id': list(user_mapping.keys()),
            'user_idx': list(user_mapping.values())
        })
        mappings.to_csv(mappings_path, index=False)
        
        logger.info(f"Saved processed data to {self.output_dir}")
        logger.info(f"  - Interactions: {len(interactions)}")
        logger.info(f"  - Items: {len(items)}")
        logger.info(f"  - Users: {len(users)}")
        
        # Create temporal split (80% train, 20% test)
        interactions_sorted = interactions.sort_values('timestamp')
        split_idx = int(len(interactions_sorted) * 0.8)
        
        train = interactions_sorted.iloc[:split_idx]
        test = interactions_sorted.iloc[split_idx:]
        
        train.to_csv(self.output_dir / "train.csv", index=False)
        test.to_csv(self.output_dir / "test.csv", index=False)
        
        logger.info(f"Created temporal split: {len(train)} train, {len(test)} test")
        
        return {
            'interactions': interactions,
            'items': items,
            'users': users,
            'train': train,
            'test': test
        }


def main():
    """Main execution."""
    # Download dataset
    downloader = DatasetDownloader(data_dir="./data/raw")
    raw_dir = downloader.download_movielens(size="100k")
    
    # Preprocess
    preprocessor = DataPreprocessor(raw_dir=Path("./data/raw"), output_dir="./data/processed")
    data = preprocessor.preprocess_movielens_100k()
    
    # Print statistics
    print("\n" + "="*80)
    print("DATASET STATISTICS")
    print("="*80)
    print(f"Total Users: {data['users']['user_idx'].nunique()}")
    print(f"Total Items: {data['items']['item_idx'].nunique()}")
    print(f"Total Interactions: {len(data['interactions'])}")
    print(f"Sparsity: {1 - len(data['interactions']) / (data['users']['user_idx'].nunique() * data['items']['item_idx'].nunique()):.4f}")
    print(f"Avg Ratings per User: {len(data['interactions']) / data['users']['user_idx'].nunique():.2f}")
    print(f"Avg Ratings per Item: {len(data['interactions']) / data['items']['item_idx'].nunique():.2f}")
    print("\nTrain/Test Split:")
    print(f"  Train: {len(data['train'])} interactions")
    print(f"  Test: {len(data['test'])} interactions")
    print("="*80)


if __name__ == "__main__":
    main()
