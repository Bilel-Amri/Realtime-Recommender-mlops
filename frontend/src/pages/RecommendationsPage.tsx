// Real-Time Recommendation System - Interactive Learning Simulator
import React,  { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { recommendationApi, eventsApi } from '../services/api';
import type { RecommendationItem, EventType } from '../types';

const RecommendationsPage: React.FC = () => {
  const [userId, setUserId] = useState<string>('');
  const [numRecommendations, setNumRecommendations] = useState<number>(10);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [requestMeta, setRequestMeta] = useState<{
    modelVersion: string;
    modelStage: string;
    generationTime: number;
    coldStart: boolean;
    cached: boolean;
  } | null>(null);
  const [interactions, setInteractions] = useState<Array<{
    item_id: string;
    event_type: string;
    value?: number;
    timestamp: Date;
  }>>([]);
  const [isLearning, setIsLearning] = useState(false);
  const [selectedRating, setSelectedRating] = useState<{[key: string]: number}>({});

  const recommendMutation = useMutation({
    mutationFn: (data: { user_id: string; num_recommendations: number }) =>
      recommendationApi.getRecommendations({
        user_id: data.user_id,
        num_recommendations: data.num_recommendations,
      }),
    onSuccess: (data) => {
      setRecommendations(data.recommendations);
      setRequestMeta({
        modelVersion: data.model_version,
        modelStage: data.model_stage,
        generationTime: data.generation_time_ms,
        coldStart: data.cold_start,
        cached: data.cached,
      });
    },
    onError: (error: Error) => {
      console.error('Recommendation failed:', error);
    },
  });

  const eventMutation = useMutation({
    mutationFn: (data: { user_id: string; item_id: string; event_type: string; value?: number }) =>
      eventsApi.logEvent({
        user_id: data.user_id,
        item_id: data.item_id,
        event_type: data.event_type as EventType,
        value: data.value,
      }),
    onSuccess: (_, variables) => {
      console.log(`Logged ${variables.event_type} for ${variables.item_id}`);
      
      // Track interaction
      setInteractions(prev => [...prev, {
        item_id: variables.item_id,
        event_type: variables.event_type,
        value: variables.value,
        timestamp: new Date()
      }]);
      
      // Show learning indicator
      setIsLearning(true);
      
      // Auto-refresh recommendations after interaction
      setTimeout(() => {
        recommendMutation.mutate({ 
          user_id: variables.user_id, 
          num_recommendations: numRecommendations 
        });
        setIsLearning(false);
      }, 800);
    },
    onError: (error) => {
      console.error('Event logging failed:', error);
      setIsLearning(false);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim()) return;
    setInteractions([]); // Reset interactions for new user
    recommendMutation.mutate({ user_id: userId, num_recommendations: numRecommendations });
  };

  const handleView = (item: RecommendationItem) => {
    if (userId && !eventMutation.isPending) {
      eventMutation.mutate({
        user_id: userId,
        item_id: item.item_id,
        event_type: 'view',
      });
    }
  };

  const handleLike = (item: RecommendationItem) => {
    if (userId && !eventMutation.isPending) {
      eventMutation.mutate({
        user_id: userId,
        item_id: item.item_id,
        event_type: 'like',
      });
    }
  };

  const handleRating = (item: RecommendationItem, rating: number) => {
    if (userId && !eventMutation.isPending) {
      eventMutation.mutate({
        user_id: userId,
        item_id: item.item_id,
        event_type: 'rating',
        value: rating,
      });
    }
  };

  const handleExampleUser = (exampleId: string) => {
    setUserId(exampleId);
    recommendMutation.mutate({ user_id: exampleId, num_recommendations: numRecommendations });
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }} className="fade-in">
      {/* Hero Section */}
      <div style={{
        textAlign: 'center',
        marginBottom: 'var(--spacing-2xl)',
        padding: 'var(--spacing-xl)',
      }}>
        <h1 style={{
          fontSize: '3rem',
          fontWeight: 800,
          marginBottom: 'var(--spacing-md)',
          letterSpacing: '-1px'
        }} className="text-gradient">
          🧪 User Interaction Simulator
        </h1>
        <p style={{
          fontSize: '1.1rem',
          color: 'var(--text-secondary)',
          maxWidth: '700px',
          margin: '0 auto',
          lineHeight: '1.6'
        }}>
          Experience real-time machine learning in action. Interact with recommended items and watch the system learn from your behavior instantly.
        </p>
      </div>

      {/* Learning Status Banner */}
      {isLearning && (
        <div style={{
          background: 'linear-gradient(90deg, rgba(99, 102, 241, 0.2), rgba(236, 72, 153, 0.2))',
          border: '1px solid var(--color-primary)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--spacing-md)',
          marginBottom: 'var(--spacing-lg)',
          textAlign: 'center',
          animation: 'pulse 1.5s ease-in-out infinite',
        }}>
          <span style={{ fontSize: '1.1rem', fontWeight: 600 }}>
            🧠 Learning from your interaction...
          </span>
        </div>
      )}

      {/* Interaction History */}
      {interactions.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--spacing-xl)', background: 'rgba(99, 102, 241, 0.05)' }}>
          <h3 style={{ marginBottom: 'var(--spacing-md)', fontSize: '1.1rem', fontWeight: 600 }}>
            📊 Your Interactions ({interactions.length})
          </h3>
          <div style={{
            display: 'flex',
            gap: 'var(--spacing-sm)',
            flexWrap: 'wrap',
            maxHeight: '150px',
            overflowY: 'auto'
          }}>
            {interactions.slice().reverse().map((interaction, idx) => (
              <div key={idx} style={{
                padding: '0.5rem 0.75rem',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                border: '1px solid var(--border-color)',
              }}>
                <span style={{ fontWeight: 600 }}>
                  {interaction.event_type === 'view' && '👁 View'}
                  {interaction.event_type === 'like' && '👍 Like'}
                  {interaction.event_type === 'rating' && `⭐ ${interaction.value}/5`}
                </span>
                {' → '}
                <span style={{ color: 'var(--text-muted)' }}>{interaction.item_id}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input Card */}
      <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
        <form onSubmit={handleSubmit}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto auto',
            gap: 'var(--spacing-md)',
            alignItems: 'end'
          }}>
            <div>
              <label style={{
                display: 'block',
                marginBottom: 'var(--spacing-xs)',
                color: 'var(--text-secondary)',
                fontSize: '0.875rem',
                fontWeight: 500
              }}>
                User ID
              </label>
              <input
                type="text"
                placeholder="Enter your user ID..."
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                disabled={recommendMutation.isPending}
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label style={{
                 display: 'block',
                marginBottom: 'var(--spacing-xs)',
                color: 'var(--text-secondary)',
                fontSize: '0.875rem',
                fontWeight: 500
              }}>
                Count
              </label>
              <select
                value={numRecommendations}
                onChange={(e) => setNumRecommendations(Number(e.target.value))}
                disabled={recommendMutation.isPending}
              >
                <option value={5}>5 items</option>
                <option value={10}>10 items</option>
                <option value={20}>20 items</option>
                <option value={50}>50 items</option>
              </select>
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={recommendMutation.isPending}
              style={{ whiteSpace: 'nowrap' }}
            >
              {recommendMutation.isPending ? '⏳ Loading...' : '✨ Get Recommendations'}
            </button>
          </div>
        </form>

        {/* Example Users */}
        <div style={{ marginTop: 'var(--spacing-lg)', display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginRight: 'var(--spacing-xs)' }}>
            Try examples:
          </span>
          {['user_123', 'new_user_456', 'active_user_789'].map((exampleId) => (
            <button
              key={exampleId}
              onClick={() => handleExampleUser(exampleId)}
              disabled={recommendMutation.isPending}
              style={{
                padding: '0.375rem 0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '0.8rem',
                transition: 'all var(--transition-base)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-primary)';
                e.currentTarget.style.color = 'var(--text-primary)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.color = 'var(--text-secondary)';
              }}
            >
              {exampleId}
            </button>
          ))}
        </div>
      </div>

      {/* Metadata Card */}
      {requestMeta && (
        <div className="card" style={{
          marginBottom: 'var(--spacing-xl)',
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(236, 72, 153, 0.1) 100%)',
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: 'var(--spacing-md)'
          }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Model Version
              </div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{requestMeta.modelVersion}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Stage
              </div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{requestMeta.modelStage}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Generation Time
              </div>
              <div style={{ fontWeight: 600, color: 'var(--color-success)' }}>
                {requestMeta.generationTime.toFixed(2)}ms
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Type
              </div>
              <div style={{ fontWeight: 600 }}>
                {requestMeta.coldStart ? '❄️ Cold Start' : '🔥 Personalized'}
              </div>
            </div>
            {requestMeta.cached && (
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  Source
                </div>
                <div style={{ fontWeight: 600, color: 'var(--color-warning)' }}>⚡ Cached</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Results Section */}
      <div className="card">
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          marginBottom: 'var(--spacing-lg)',
          color: 'var(--text-primary)'
        }}>
          Recommended Items
        </h2>

        {recommendMutation.isPending && (
          <div style={{ textAlign: 'center', padding: 'var(--spacing-2xl)' }}>
            <div className="loading" style={{
              width: '100%',
              height: '200px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.1rem',
              color: 'var(--text-secondary)'
            }}>
              Generating personalized recommendations...
            </div>
          </div>
        )}

        {!recommendMutation.isPending && recommendations.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: 'var(--spacing-2xl)',
            color: 'var(--text-muted)'
          }}>
            <div style={{ fontSize: '3rem', marginBottom: 'var(--spacing-md)' }}>🎯</div>
            <p style={{ fontSize: '1.1rem' }}>Enter a user ID to get personalized recommendations</p>
          </div>
        )}

        {!recommendMutation.isPending && recommendations.length > 0 && (
          <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
            {recommendations.map((item) => (
              <div
                key={item.item_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: 'var(--spacing-lg)',
                  background: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--border-color)',
                  transition: 'all var(--transition-base)',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-color-hover)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-xl)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {/* Rank Badge */}
                <div style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  background: 'var(--gradient-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 'bold',
                  fontSize: '1.2rem',
                  marginRight: 'var(--spacing-lg)',
                  boxShadow: 'var(--shadow-glow)',
                  color: 'white'
                }}>
                  {item.rank}
                </div>

                {/* Item Info */}
                <div style={{ flex: 1 }}>
                  <div style={{
                    fontWeight: 600,
                    fontSize: '1.1rem',
                    color: 'var(--text-primary)',
                    marginBottom: '0.25rem'
                  }}>
                    {item.item_id}
                  </div>
                  {item.reason && (
                    <div style={{
                      fontSize: '0.875rem',
                      color: 'var(--text-muted)',
                      marginTop: '0.25rem'
                    }}>
                      {item.reason}
                    </div>
                  )}
                  {item.metadata && (
                    <div style={{
                      display: 'flex',
                      gap: 'var(--spacing-md)',
                      marginTop: 'var(--spacing-xs)',
                      fontSize: '0.75rem',
                      color: 'var(--text-muted)'
                    }}>
                      {Object.entries(item.metadata).map(([key, value]) => (
                        <span key={key}>
                          {key}: {String(value)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Score */}
                <div style={{
                  textAlign: 'right',
                  marginLeft: 'var(--spacing-lg)',
                  marginRight: 'var(--spacing-lg)'
                }}>
                  <div style={{
                    fontSize: '1.75rem',
                    fontWeight: 'bold',
                    background: 'var(--gradient-primary)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text'
                  }}>
                    {(item.score * 100).toFixed(1)}%
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    relevance
                  </div>
                </div>

                {/* Interaction Buttons */}
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--spacing-xs)',
                  minWidth: '180px'
                }}>
                  {/* View Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleView(item);
                    }}
                    disabled={eventMutation.isPending || isLearning}
                    style={{
                      padding: '0.4rem 0.8rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid #6366f1',
                      background: 'transparent',
                      color: '#6366f1',
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: '0.75rem',
                      transition: 'all 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.3rem'
                    }}
                    onMouseEnter={(e) => {
                      if (!eventMutation.isPending && !isLearning) {
                        e.currentTarget.style.background = '#6366f1';
                        e.currentTarget.style.color = 'white';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = '#6366f1';
                    }}
                  >
                    👁 View Item
                  </button>

                  {/* Like Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleLike(item);
                    }}
                    disabled={eventMutation.isPending || isLearning}
                    style={{
                      padding: '0.4rem 0.8rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid #10b981',
                      background: 'transparent',
                      color: '#10b981',
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: '0.75rem',
                      transition: 'all 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.3rem'
                    }}
                    onMouseEnter={(e) => {
                      if (!eventMutation.isPending && !isLearning) {
                        e.currentTarget.style.background = '#10b981';
                        e.currentTarget.style.color = 'white';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = '#10b981';
                    }}
                  >
                    👍 Like
                  </button>

                  {/* Rating Selector */}
                  <div style={{
                    display: 'flex',
                    gap: '0.2rem',
                    justifyContent: 'center'
                  }}>
                    {[1, 2, 3, 4, 5].map((rating) => (
                      <button
                        key={rating}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedRating({...selectedRating, [item.item_id]: rating});
                          handleRating(item, rating);
                        }}
                        disabled={eventMutation.isPending || isLearning}
                        style={{
                          padding: '0.3rem',
                          width: '30px',
                          height: '30px',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid #f59e0b',
                          background: selectedRating[item.item_id] === rating ? '#f59e0b' : 'transparent',
                          color: selectedRating[item.item_id] === rating ? 'white' : '#f59e0b',
                          cursor: 'pointer',
                          fontSize: '0.9rem',
                          transition: 'all 0.2s',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                        onMouseEnter={(e) => {
                          if (!eventMutation.isPending && !isLearning) {
                            e.currentTarget.style.background = '#f59e0b';
                            e.currentTarget.style.color = 'white';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (selectedRating[item.item_id] !== rating) {
                            e.currentTarget.style.background = 'transparent';
                            e.currentTarget.style.color = '#f59e0b';
                          }
                        }}
                        title={`Rate ${rating} stars`}
                      >
                        ⭐
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Instructions Card */}
      {recommendations.length > 0 && (
        <div className="card" style={{
          marginTop: 'var(--spacing-xl)',
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%)',
          border: '1px solid rgba(16, 185, 129, 0.3)'
        }}>
          <h3 style={{ marginBottom: 'var(--spacing-md)', fontSize: '1.1rem', fontWeight: 600 }}>
            💡 How It Works
          </h3>
          <ul style={{ 
            paddingLeft: 'var(--spacing-lg)', 
            color: 'var(--text-secondary)',
            lineHeight: '1.8'
          }}>
            <li>👁 <strong>View</strong>: Indicates interest in an item</li>
            <li>👍 <strong>Like</strong>: Strong positive signal</li>
            <li>⭐ <strong>Rating</strong>: Provide detailed feedback (1-5 stars)</li>
            <li>🧠 After each interaction, the system learns and updates recommendations</li>
            <li>🔄 Watch how recommendations change based on your behavior!</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default RecommendationsPage;
