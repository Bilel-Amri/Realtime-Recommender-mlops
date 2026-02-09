"""
Training Pipeline Test

Tests the ML training pipeline:
1. Dataset availability
2. Model training
3. Embedding extraction
4. FAISS index creation
5. Evaluation metrics

Usage:
    python test_training.py

This will train a model and verify all components work correctly.
"""

import sys
from pathlib import Path
import time

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def print_header(text):
    print("\n" + "="*80)
    print(text)
    print("="*80)

def check_dependencies():
    """Check if required packages are installed."""
    print_header("Checking Dependencies")
    
    required = {
        'numpy': 'numpy',
        'pandas': 'pandas',
        'implicit': 'implicit',
        'faiss': 'faiss-cpu',
        'sklearn': 'scikit-learn',
        'mlflow': 'mlflow'
    }
    
    missing = []
    
    for module, package in required.items():
        try:
            __import__(module)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies installed")
    return True


def check_dataset():
    """Check if dataset is available."""
    print_header("Checking Dataset")
    
    data_dir = Path("data/processed")
    
    required_files = [
        "interactions.csv",
        "users.csv",
        "items.csv",
        "train.csv",
        "test.csv"
    ]
    
    if not data_dir.exists():
        print(f"❌ Directory not found: {data_dir}")
        print("\nDownload dataset:")
        print("  cd data && python download_dataset.py")
        return False
    
    missing = []
    for filename in required_files:
        filepath = data_dir / filename
        if filepath.exists():
            size_mb = filepath.stat().st_size / (1024 ** 2)
            print(f"✅ {filename} ({size_mb:.2f} MB)")
        else:
            print(f"❌ {filename} - NOT FOUND")
            missing.append(filename)
    
    if missing:
        print(f"\n❌ Missing files: {', '.join(missing)}")
        print("\nDownload dataset:")
        print("  cd data && python download_dataset.py")
        return False
    
    print("\n✅ Dataset ready")
    return True


def test_training():
    """Test model training."""
    print_header("Training Model")
    
    try:
        # Import training pipeline
        sys.path.insert(0, str(Path(__file__).parent / "training"))
        from train_embeddings import RecommenderTrainingPipeline
        
        print("Initializing training pipeline...")
        pipeline = RecommenderTrainingPipeline(
            data_dir="./data/processed",
            model_dir="./models",
            embedding_dim=64
        )
        
        print("Loading dataset...")
        interactions, users, items = pipeline.load_data()
        
        print(f"✅ Loaded:")
        print(f"   - {len(interactions)} interactions")
        print(f"   - {len(users)} users")
        print(f"   - {len(items)} items")
        
        # Load train/test split
        import pandas as pd
        train_data = pd.read_csv("./data/processed/train.csv")
        test_data = pd.read_csv("./data/processed/test.csv")
        
        print(f"\nTrain/Test Split:")
        print(f"   - Train: {len(train_data)} samples")
        print(f"   - Test: {len(test_data)} samples")
        
        print("\n🔄 Training embedding model (this may take 30-60 seconds)...")
        start_time = time.time()
        
        model = pipeline.train_embedding_model(train_data)
        
        training_time = time.time() - start_time
        
        print(f"✅ Training complete in {training_time:.1f} seconds")
        
        # Check embeddings
        stats = model.get_stats()
        print(f"\nModel Statistics:")
        print(f"   - Users: {stats['n_users']}")
        print(f"   - Items: {stats['n_items']}")
        print(f"   - Embedding dim: {stats['embedding_dim']}")
        
        print("\n🔄 Evaluating model...")
        metrics = pipeline.evaluate_model(test_data)
        
        print(f"\n📊 Evaluation Metrics:")
        for metric, value in metrics.items():
            print(f"   - {metric}: {value:.4f}")
        
        # Check if metrics are reasonable
        precision = metrics.get('precision@10', 0)
        if precision > 0.10:
            print(f"\n✅ Precision@10 = {precision:.4f} (GOOD - better than baseline 0.02)")
        elif precision > 0.05:
            print(f"\n⚠️  Precision@10 = {precision:.4f} (OK - better than random)")
        else:
            print(f"\n❌ Precision@10 = {precision:.4f} (LOW - check model)")
        
        print("\n🔄 Creating FAISS vector store...")
        vector_store = pipeline.populate_vector_store(items)
        
        vector_stats = vector_store.get_statistics()
        print(f"✅ Vector store created:")
        print(f"   - Items indexed: {vector_stats['total_items']}")
        print(f"   - Index type: {vector_stats['index_type']}")
        
        print("\n🔄 Saving model artifacts...")
        pipeline.save_artifacts()
        
        # Check saved files
        model_dir = Path("models")
        saved_files = list(model_dir.glob("*"))
        print(f"✅ Saved {len(saved_files)} files to {model_dir}/")
        for f in saved_files:
            size_mb = f.stat().st_size / (1024 ** 2)
            print(f"   - {f.name} ({size_mb:.2f} MB)")
        
        print("\n" + "="*80)
        print("✅ TRAINING PIPELINE TEST PASSED")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_loading():
    """Test loading saved model."""
    print_header("Testing Model Loading")
    
    try:
        from backend.app.models.embedding_model import MatrixFactorizationModel
        from backend.app.services.vector_store import FAISSVectorStore
        
        print("Loading embedding model...")
        model_path = Path("models/embedding_model.pkl")
        
        if not model_path.exists():
            print(f"❌ Model not found: {model_path}")
            print("   Train model first with: python test_training.py")
            return False
        
        model = MatrixFactorizationModel.load(str(model_path))
        print("✅ Embedding model loaded")
        
        # Test getting embeddings
        print("\nTesting embedding retrieval...")
        user_emb = model.get_user_embedding("1")
        if user_emb is not None:
            print(f"✅ User embedding shape: {user_emb.shape}")
        
        item_emb = model.get_item_embedding("1")
        if item_emb is not None:
            print(f"✅ Item embedding shape: {item_emb.shape}")
        
        # Test recommendations
        print("\nTesting recommendations...")
        recs = model.recommend_for_user("1", n=5)
        print(f"✅ Generated {len(recs)} recommendations")
        for i, (item_id, score) in enumerate(recs[:5]):
            print(f"   {i+1}. {item_id} (score: {score:.4f})")
        
        print("\nLoading vector store...")
        vector_path = Path("models/vector_store")
        
        if not vector_path.with_suffix('.faiss').exists():
            print(f"❌ Vector store not found: {vector_path}")
            return False
        
        vector_store = FAISSVectorStore.load(str(vector_path))
        print("✅ Vector store loaded")
        
        stats = vector_store.get_statistics()
        print(f"   - Items indexed: {stats['total_items']}")
        
        print("\n✅ MODEL LOADING TEST PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Model loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all training tests."""
    print("\n" + "="*80)
    print("🧪 ML TRAINING PIPELINE - TEST SUITE")
    print("="*80)
    
    # Test 1: Dependencies
    if not check_dependencies():
        print("\n❌ TESTS ABORTED - Install missing dependencies")
        return False
    
    # Test 2: Dataset
    if not check_dataset():
        print("\n❌ TESTS ABORTED - Download dataset first")
        return False
    
    # Test 3: Training
    if not test_training():
        print("\n❌ TRAINING TEST FAILED")
        return False
    
    # Test 4: Model Loading
    if not test_model_loading():
        print("\n❌ MODEL LOADING TEST FAILED") 
        return False
    
    # Success
    print("\n" + "="*80)
    print("🎉 ALL TRAINING TESTS PASSED")
    print("="*80)
    print("\n✅ Model trained successfully")
    print("✅ Embeddings extracted")
    print("✅ Vector store created")
    print("✅ Artifacts saved")
    print("✅ Model loading works")
    
    print("\n📋 Next Steps:")
    print("1. Start backend: cd backend && uvicorn app.main:app --reload")
    print("2. Test API: python test_system.py")
    print("3. Integrate trained model into backend for real learning")
    
    print("\n" + "="*80)
    
    return True


if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
