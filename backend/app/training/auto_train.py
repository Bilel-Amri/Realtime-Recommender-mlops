"""
Automatic model training on startup.
Runs only if model file doesn't exist.
"""
import os
import sys
from pathlib import Path
import structlog
import time

logger = structlog.get_logger(__name__)

def should_train_model() -> bool:
    """Check if we need to train the model."""
    model_path = os.getenv("MODEL_PATH", "/app/models/embedding_model.pkl")
    exists = Path(model_path).exists()
    
    if exists:
        file_size = Path(model_path).stat().st_size
        logger.info("model_found", path=model_path, size_kb=file_size//1024)
        return False
    else:
        logger.warning("model_not_found", path=model_path)
        return True

def train_model():
    """Train the recommendation model."""
    logger.info("starting_automatic_training")
    
    # Import the training pipeline
    # Assuming the training script is in the parent directory of 'app' or similar structure
    # Based on previous exploration, training script might effectively be what we used in quick_train.py
    # But let's look for existing training logic or adapt quick_train.py logic here if needed.
    # The user has `training/train_embeddings.py` likely in the root or `backend/training`?
    # Let's check file structure first to be sure where `train_embeddings.py` is.
    
    # For now, I'll use a robust approach that tries to find the training script.
    # We know `quick_train.py` worked. 
    
    # Let's try to import from the project's training module if it exists, otherwise use a simplified embedded pipeline
    
    try:
        # Try finding the training script in expected locations
        training_path = Path(__file__).parent.parent.parent / "training"
        if training_path.exists():
             sys.path.insert(0, str(training_path))
             
        # Check if we can import RecommenderTrainingPipeline
        try:
             from train_embeddings import RecommenderTrainingPipeline
             pipeline = RecommenderTrainingPipeline()
             pipeline.run_full_pipeline()
             logger.info("automatic_training_completed_via_pipeline")
             return True
        except ImportError:
             logger.warning("could_not_import_training_pipeline_using_fallback")
             
        # Fallback: Use the logic I verified in quick_train.py
        # This is safer because I know it works
        
        import pandas as pd
        import numpy as np
        import implicit
        import pickle
        import faiss
        from scipy.sparse import csr_matrix
        
        data_dir = Path("/app/data/processed")
        model_dir = Path("/app/models")
        
        # Load data
        interactions = pd.read_csv(data_dir / "interactions.csv")
        users = pd.read_csv(data_dir / "users.csv")
        items = pd.read_csv(data_dir / "items.csv")
        
        # Create mappings
        user_ids = users['user_id'].unique()
        item_ids = items['item_id'].unique()
        user_to_idx = {uid: i for i, uid in enumerate(user_ids)}
        item_to_idx = {iid: i for i, iid in enumerate(item_ids)}
        
        # Create sparse matrix
        rows = [user_to_idx[uid] for uid in interactions['user_id']]
        cols = [item_to_idx[iid] for iid in interactions['item_id']]
        data = np.ones(len(interactions))
        user_item_matrix = csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(item_ids)))
        
        # Train model
        model = implicit.als.AlternatingLeastSquares(
            factors=64,
            iterations=20,
            regularization=0.01,
            random_state=42
        )
        model.fit(user_item_matrix)
        
        # Save artifacts
        model_data = {
            'user_factors': model.user_factors,
            'item_factors': model.item_factors,
            'user_to_idx': user_to_idx,
            'item_to_idx': item_to_idx,
            'user_ids': user_ids,
            'item_ids': item_ids
        }
        
        with open(model_dir / 'embedding_model.pkl', 'wb') as f:
            pickle.dump(model_data, f)
            
        # Create Vector Store
        item_factors = model.item_factors
        if hasattr(item_factors, 'to_numpy'):
             item_factors = item_factors.to_numpy()
             
        index = faiss.IndexFlatIP(64)
        index.add(item_factors.astype('float32'))
        
        vector_store_path = model_dir / 'vector_store'
        vector_store_path.mkdir(exist_ok=True)
        faiss.write_index(index, str(vector_store_path / 'items.index'))
        
        logger.info("automatic_training_completed_fallback")
        return True
        
    except Exception as e:
        logger.error("training_failed", error=str(e))
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    if should_train_model():
        train_model()
    else:
        logger.info("model_exists_skipping_training")
