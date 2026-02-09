#!/usr/bin/env python3
"""Quick training script to run inside Docker container"""

import sys
import os

# Add backend to path
sys.path.insert(0, '/app')

# Import training pipeline
import pandas as pd
import numpy as np
from implicit.als import AlternatingLeastSquares
import pickle
import faiss
from scipy.sparse import csr_matrix

print("Loading data...")
interactions = pd.read_csv('/app/data/processed/interactions.csv')
items = pd.read_csv('/app/data/processed/items.csv')

print(f"Loaded {len(interactions)} interactions and {len(items)} items")

# Create user-item matrix
print("Creating user-item matrix...")
user_ids = interactions['user_idx'].unique()
item_ids = interactions['item_idx'].unique()

user_id_map = {id: idx for idx, id in enumerate(user_ids)}
item_id_map = {id: idx for idx, id in enumerate(item_ids)}

rows = interactions['user_idx'].map(user_id_map).values
cols = interactions['item_idx'].map(item_id_map).values
data = interactions['engagement'].values

user_item_matrix = csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(item_ids)))

# Train model
print("Training ALS model (this takes ~30 seconds)...")
model = AlternatingLeastSquares(
    factors=64,
    iterations=20,
    regularization=0.01,
    random_state=42
)

model.fit(user_item_matrix)
print("Training complete!")

# Extract embeddings
user_embeddings = model.user_factors
item_embeddings = model.item_factors

print(f"User embeddings shape: {user_embeddings.shape}")
print(f"Item embeddings shape: {item_embeddings.shape}")

# Save model
print("Saving model...")
os.makedirs('/app/models', exist_ok=True)

model_data = {
    'model': model,
    'user_id_map': user_id_map,
    'item_id_map': item_id_map,
    'user_embeddings': user_embeddings,
    'item_embeddings': item_embeddings,
    'num_users': len(user_ids),
    'num_items': len(item_ids),
}

with open('/app/models/embedding_model.pkl', 'wb') as f:
    pickle.dump(model_data, f)

print("Model saved to /app/models/embedding_model.pkl")

# Create FAISS index
print("Creating FAISS index...")
os.makedirs('/app/models/vector_store', exist_ok=True)

# Normalize embeddings for cosine similarity
item_embeddings_norm = item_embeddings / np.linalg.norm(item_embeddings, axis=1, keepdims=True)

# Create index
dimension = item_embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
index.add(item_embeddings_norm.astype('float32'))

# Save index
faiss.write_index(index, '/app/models/vector_store/items.index')

# Save item ID mapping
with open('/app/models/vector_store/item_ids.pkl', 'wb') as f:
    pickle.dump(list(item_ids), f)

print("FAISS index saved to /app/models/vector_store/")

print("\n✅ Training complete! Model ready to use.")
print("\nModel metrics (approximate):")
print("  - Embedding dimensions: 64")
print(f"  - Number of users: {len(user_ids)}")
print(f"  - Number of items: {len(item_ids)}")
print(f"  - Training interactions: {len(interactions)}")
