# Dataset Selection & Justification

## Selected Dataset: MovieLens-100K

**Source**: https://grouplens.org/datasets/movielens/100k/
**Direct Download**: https://files.grouplens.org/datasets/movielens/ml-100k.zip

### Domain Choice: Movie Recommendations

**Why MovieLens:**
- Industry-standard benchmark dataset (used by Netflix, Hulu)
- Clean, well-structured data (ready for ML)
- Manageable size (100K ratings, ~5MB compressed)
- Fast training (<60 seconds on laptop)
- Clear user-item interactions
- Rich metadata (genres, timestamps)
- Suitable for academic + industry demonstration

### Dataset Characteristics

```
Users:        943 unique users
Items:        1,682 movies
Interactions: 100,000 ratings
Ratings:      1-5 stars (explicit feedback)
Timespan:     1997-1998 (temporal data)
Genres:       19 genres (Action, Comedy, Drama, etc.)
Sparsity:     93.7% sparse (realistic cold-start scenario)
```

### Features Available

**User Features:**
- User ID
- Historical interaction patterns
- Rating distribution
- Category preferences
- Temporal activity patterns

**Item Features:**
- Movie ID
- Title
- Release date
- Genres (19 categories: Action, Comedy, Drama, etc.)
- Popularity metrics (view count, avg rating)
- IMDB URL (optional metadata)

**Interaction Features:**
- Rating score (explicit feedback)
- Review text (sentiment analysis)
- Purchase timestamp
- Dwell time proxy (review length)

### Why This Dataset Matches Requirements

1. **Real Data**: Actual Amazon transactions, not synthetic
2. **Scale**: Large enough to demonstrate ML performance
3. **Variety**: Multiple product categories for diversity
4. **Temporal**: Timestamps enable online learning simulation
5. **Hybrid Signals**: Both implicit (views) and explicit (ratings)
6. **Industry Relevance**: Direct Amazon use case
7. **Academic Validity**: Widely used in research papers

### Preprocessing Pipeline

```
Raw Data (CSV/JSON)
    ↓
Data Cleaning
    ↓
User/Item Encoding
    ↓
Temporal Split (train/test)
    ↓
Feature Engineering
    ↓
Redis + Vector DB Population
```

### Why Not Amazon/Larger Datasets?

**MovieLens-100K is optimal for this project:**
- **Fast Training**: 30-60 seconds vs hours for large datasets
- **Easy Setup**: Single download, no API keys needed
- **Academic Standard**: Used in 1000+ research papers
- **Demo-Friendly**: Quick iteration, instant results
- **Scales Well**: Same algorithms work for millions of items

**Alternative Datasets** (if needed):
- **MovieLens-1M**: 1M ratings (10x larger)
- **MovieLens-25M**: 25M ratings (250x larger)
- **Amazon Reviews**: 10M+ ratings (requires preprocessing)
- **Spotify Music**: 1M+ tracks (requires API access)

This provides flexibility while maintaining real data requirements and fast iteration.
