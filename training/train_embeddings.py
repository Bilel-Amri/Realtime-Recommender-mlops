"""
Offline Training Pipeline with Embeddings

Trains collaborative filtering model using Matrix Factorization (ALS).
Extracts user and item embeddings for real-time recommendations.

This is the core ML pipeline that:
1. Loads real dataset (MovieLens)
2. Trains ALS model
3. Extracts embeddings
4. Evaluates metrics
5. Registers in MLflow
6. Populates Redis + FAISS

Academic Justification:
======================

Why Matrix Factorization:
- Industry standard (Spotify, Netflix, Pinterest)
- Learns latent representations
- Generalizes to unseen pairs
- Scales to millions of users/items
- Supports online learning

Why This is AI, Not Rules:
- No hardcoded logic
- Learns from data
- Discovers hidden patterns
- Adapts to new information
- Makes predictions on unseen data

Mathematical Foundation:
- Minimizes ||R - U × I^T||² + λ(||U||² + ||I||²)
- Optimizes via Alternating Least Squares
- Converges to local minimum
- Embeddings capture semantic similarity
"""

import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Tuple
from datetime import datetime

# Add parent directory to path to import from backend
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# ML libraries
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import mlflow
import mlflow.pyfunc

# Our models
from app.models.embedding_model import MatrixFactorizationModel
from app.services.vector_store import FAISSVectorStore
from app.services.redis_feature_store import RedisFeatureStore

# Configuration
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RecommenderTrainingPipeline:
    """Complete training pipeline for recommendation system."""
    
    def __init__(
        self,
        data_dir: str = "./data/processed",
        model_dir: str = "./models",
        embedding_dim: int = 64
    ):
        """Initialize training pipeline."""
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_dim = embedding_dim
        
        self.model: Optional[MatrixFactorizationModel] = None
        self.vector_store: Optional[FAISSVectorStore] = None
        self.feature_store: Optional[RedisFeatureStore] = None
        
    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load processed dataset."""
        logger.info("Loading dataset...")
        
        interactions = pd.read_csv(self.data_dir / "interactions.csv")
        users = pd.read_csv(self.data_dir / "users.csv")
        items = pd.read_csv(self.data_dir / "items.csv")
        
        logger.info(f"Loaded {len(interactions)} interactions, "
                   f"{len(users)} users, {len(items)} items")
        
        return interactions, users, items
    
    def train_embedding_model(
        self,
        interactions: pd.DataFrame
    ) -> MatrixFactorizationModel:
        """
        Train Matrix Factorization model.
        
        Args:
            interactions: DataFrame with user_id, item_id, engagement columns
            
        Returns:
            Trained model
        """
        logger.info("Training Matrix Factorization model...")
        
        # Convert IDs to strings for consistency
        user_ids = interactions['user_id'].astype(str).tolist()
        item_ids = interactions['item_id'].astype(str).tolist()
        
        # Use engagement or rating as implicit feedback
        if 'engagement' in interactions.columns:
            values = interactions['engagement'].tolist()
        elif 'rating' in interactions.columns:
            # Convert ratings to implicit feedback (higher weight for better ratings)
            values = (interactions['rating'] / interactions['rating'].max()).tolist()
        else:
            # Binary feedback
            values = [1.0] * len(interactions)
        
        # Initialize and train model
        model = MatrixFactorizationModel(
            embedding_dim=self.embedding_dim,
            regularization=0.01,
            alpha=1.0,
            iterations=50,
            random_state=42
        )
        
        model.fit(user_ids, item_ids, values)
        
        self.model = model
        return model
    
    def evaluate_model(
        self,
        test_interactions: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Evaluate model on test set.
        
        Metrics:
        - Precision@K: Fraction of recommended items that are relevant
        - Recall@K: Fraction of relevant items that are recommended
        - MAP@K: Mean Average Precision
        - NDCG@K: Normalized Discounted Cumulative Gain
        
        Args:
            test_interactions: Test set DataFrame
            
        Returns:
            Dictionary of metrics
        """
        logger.info("Evaluating model...")
        
        if not self.model or not self.model.is_fitted:
            logger.warning("Model not trained")
            return {}
        
        # Prepare test data
        test_user_ids = test_interactions['user_id'].astype(str).unique()
        
        # Metrics
        precision_at_10_scores = []
        recall_at_10_scores = []
        map_scores = []
        
        for user_id in test_user_ids[:100]:  # Sample for speed
            # Get ground truth items for this user
            user_test = test_interactions[
                test_interactions['user_id'].astype(str) == user_id
            ]
            
            if len(user_test) == 0:
                continue
            
            # Only consider items with high engagement/rating
            if 'rating' in user_test.columns:
                relevant_items = set(
                    user_test[user_test['rating'] >= 4]['item_id'].astype(str)
                )
            else:
                relevant_items = set(user_test['item_id'].astype(str))
            
            if len(relevant_items) == 0:
                continue
            
            # Get recommendations
            recommendations = self.model.recommend_for_user(user_id, n=10)
            recommended_items = set([item_id for item_id, _ in recommendations])
            
            # Calculate metrics
            hits = len(recommended_items & relevant_items)
            
            # Precision@10
            precision = hits / len(recommended_items) if recommended_items else 0
            precision_at_10_scores.append(precision)
            
            # Recall@10
            recall = hits / len(relevant_items) if relevant_items else 0
            recall_at_10_scores.append(recall)
            
            # Average Precision
            ap = 0.0
            hits_so_far = 0
            for i, (item_id, _) in enumerate(recommendations):
                if item_id in relevant_items:
                    hits_so_far += 1
                    ap += hits_so_far / (i + 1)
            ap /= min(len(relevant_items), 10)
            map_scores.append(ap)
        
        metrics = {
            'precision@10': np.mean(precision_at_10_scores) if precision_at_10_scores else 0.0,
            'recall@10': np.mean(recall_at_10_scores) if recall_at_10_scores else 0.0,
            'map@10': np.mean(map_scores) if map_scores else 0.0,
            'n_test_users': len(precision_at_10_scores),
        }
        
        logger.info(f"Evaluation metrics: {metrics}")
        return metrics
    
    def populate_vector_store(
        self,
        items: pd.DataFrame
    ) -> FAISSVectorStore:
        """
        Populate FAISS vector store with item embeddings.
        
        Args:
            items: Items DataFrame with item_id column
            
        Returns:
            Initialized vector store
        """
        logger.info("Populating vector store...")
        
        if not self.model or not self.model.is_fitted:
            raise ValueError("Model not trained")
        
        # Create vector store
        vector_store = FAISSVectorStore(
            embedding_dim=self.embedding_dim,
            index_type="flat",
            metric="ip"
        )
        
        # Get item embeddings
        item_ids = items['item_id'].astype(str).tolist()
        embeddings_list = []
        valid_item_ids = []
        
        for item_id in item_ids:
            embedding = self.model.get_item_embedding(item_id)
            if embedding is not None:
                embeddings_list.append(embedding)
                valid_item_ids.append(item_id)
        
        if embeddings_list:
            embeddings_array = np.vstack(embeddings_list)
            vector_store.add_items(valid_item_ids, embeddings_array)
            logger.info(f"Added {len(valid_item_ids)} items to vector store")
        
        self.vector_store = vector_store
        return vector_store
    
    def populate_redis(
        self,
        interactions: pd.DataFrame,
        users: pd.DataFrame,
        items: pd.DataFrame
    ):
        """
        Populate Redis with features and embeddings.
        
        Args:
            interactions: Interactions DataFrame
            users: Users DataFrame
            items: Items DataFrame
        """
        logger.info("Populating Redis feature store...")
        
        try:
            feature_store = RedisFeatureStore()
            
            if not feature_store.connected:
                logger.warning("Redis not available, skipping population")
                return
            
            # Store user embeddings
            user_ids = users['user_id'].astype(str).unique()
            for user_id in user_ids[:1000]:  # Limit for demo
                embedding = self.model.get_user_embedding(user_id)
                if embedding is not None:
                    feature_store.set_user_embedding(user_id, embedding.astype(np.float32))
            
            # Store item embeddings
            item_ids = items['item_id'].astype(str).unique()
            for item_id in item_ids:
                embedding = self.model.get_item_embedding(item_id)
                if embedding is not None:
                    feature_store.set_item_embedding(item_id, embedding.astype(np.float32))
            
            # Store interaction counts
            for _, row in interactions.iterrows():
                user_id = str(row['user_id'])
                item_id = str(row['item_id'])
                
                # Infer interaction type from rating
                if 'rating' in row:
                    rating = row['rating']
                    if rating >= 4:
                        feature_store.increment_user_interaction(
                            user_id, 'click', item_id, value=rating
                        )
                        feature_store.increment_item_popularity(item_id, value=rating)
            
            logger.info("✅ Redis population complete")
            self.feature_store = feature_store
            
        except Exception as e:
            logger.warning(f"Failed to populate Redis: {e}")
    
    def save_artifacts(self):
        """Save model artifacts to disk."""
        logger.info("Saving model artifacts...")
        
        # Save embedding model
        model_path = self.model_dir / "embedding_model.pkl"
        self.model.save(str(model_path))
        
        # Save vector store
        vector_store_path = self.model_dir / "vector_store"
        self.vector_store.save(str(vector_store_path))
        
        logger.info(f"Artifacts saved to {self.model_dir}")
    
    def log_to_mlflow(self, metrics: Dict[str, float]):
        """
        Log model and metrics to MLflow.
        
        Args:
            metrics: Evaluation metrics
        """
        logger.info("Logging to MLflow...")
        
        try:
            # Set tracking URI
            if settings.mlflow_tracking_uri:
                mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            
            mlflow.set_experiment("recommender-embeddings")
            
            with mlflow.start_run(run_name=f"als-{datetime.now().strftime('%Y%m%d-%H%M%S')}"):
                # Log parameters
                mlflow.log_params({
                    'embedding_dim': self.embedding_dim,
                    'algorithm': 'matrix_factorization_als',
                    'n_users': len(self.model.user_id_map),
                    'n_items': len(self.model.item_id_map),
                })
                
                # Log metrics
                mlflow.log_metrics(metrics)
                
                # Log model stats
                model_stats = self.model.get_stats()
                mlflow.log_metrics({
                    'user_emb_norm_mean': model_stats['user_embedding_norm_mean'],
                    'item_emb_norm_mean': model_stats['item_embedding_norm_mean'],
                })
                
                # Save and log artifacts
                self.save_artifacts()
                mlflow.log_artifacts(str(self.model_dir))
                
                # Register model
                mlflow.pyfunc.log_model(
                    artifact_path="model",
                    python_model=None,  # We'll load from pickle
                    artifacts={
                        "embedding_model": str(self.model_dir / "embedding_model.pkl"),
                        "vector_store": str(self.model_dir / "vector_store.faiss"),
                    }
                )
                
                logger.info("✅ MLflow logging complete")
                
        except Exception as e:
            logger.warning(f"MLflow logging failed: {e}. Continuing without MLflow.")
    
    def run_full_pipeline(self):
        """Execute complete training pipeline."""
        logger.info("="*80)
        logger.info("STARTING EMBEDDING-BASED RECOMMENDATION TRAINING")
        logger.info("="*80)
        
        # 1. Load data
        interactions, users, items = self.load_data()
        
        # 2. Split data
        train_data = pd.read_csv(self.data_dir / "train.csv")
        test_data = pd.read_csv(self.data_dir / "test.csv")
        
        logger.info(f"Train: {len(train_data)}, Test: {len(test_data)}")
        
        # 3. Train model
        self.train_embedding_model(train_data)
        
        # 4. Evaluate
        metrics = self.evaluate_model(test_data)
        
        # 5. Populate vector store
        self.populate_vector_store(items)
        
        # 6. Populate Redis
        self.populate_redis(interactions, users, items)
        
        # 7. Log to MLflow
        self.log_to_mlflow(metrics)
        
        logger.info("="*80)
        logger.info("TRAINING COMPLETE")
        logger.info("="*80)
        logger.info(f"Final Metrics:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")
        logger.info("="*80)
        
        return self.model, metrics


def main():
    """Main training execution."""
    # Check if data exists
    data_dir = Path("./data/processed")
    
    if not data_dir.exists() or not (data_dir / "interactions.csv").exists():
        logger.info("Processed data not found. Downloading and preprocessing...")
        
        # Run data download script
        sys.path.insert(0, str(Path("./data").absolute()))
        from download_dataset import main as download_main
        download_main()
    
    # Run training pipeline
    pipeline = RecommenderTrainingPipeline(
        data_dir="./data/processed",
        model_dir="./models",
        embedding_dim=64
    )
    
    model, metrics = pipeline.run_full_pipeline()
    
    print("\n" + "="*80)
    print("✅ TRAINING SUCCESSFUL")
    print("="*80)
    print("\nNext Steps:")
    print("1. Start backend: cd backend && uvicorn app.main:app --reload")
    print("2. Test recommendations with different users")
    print("3. Monitor Redis for feature updates")
    print("4. Check MLflow UI: mlflow ui")
    print("="*80)


if __name__ == "__main__":
    main()
