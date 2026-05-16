import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore';
import { useT } from '../i18n/useT';
import { t as ti } from '../i18n';
import { StoryCard } from '../types/canvas';

interface StoryCardPickerProps {
  projectId: string;
  onClose: () => void;
}

const CATEGORY_KEYS: Record<string, string> = {
  A: 'storycard.cat_goal', B: 'storycard.cat_relation', C: 'storycard.cat_mystery',
  D: 'storycard.cat_survival', E: 'storycard.cat_growth', F: 'storycard.cat_world', G: 'storycard.cat_special',
};

const CATEGORY_COLORS: Record<string, string> = {
  A: '#4A90D9', B: '#FF69B4', C: '#E8873A',
  D: '#E74C3C', E: '#50C878', F: '#7B68EE', G: '#FFD700',
};

const StoryCardPicker: React.FC<StoryCardPickerProps> = ({ projectId, onClose }) => {
  const { storyCards, loadStoryCards, applyStoryCards, isLoading } = useProjectStore();
  const [selectedPrimary, setSelectedPrimary] = useState<string | null>(null);
  const [selectedSecondary, setSelectedSecondary] = useState<string[]>([]);

  useEffect(() => {
    loadStoryCards();
  }, []);

  const groupedCards: Record<string, StoryCard[]> = {};
  storyCards.forEach((card) => {
    if (!groupedCards[card.category]) groupedCards[card.category] = [];
    groupedCards[card.category].push(card);
  });

  const handleCardClick = (cardId: string) => {
    if (selectedPrimary === cardId) {
      setSelectedPrimary(null);
    } else {
      setSelectedPrimary(cardId);
    }
  };

  const handleSecondaryToggle = (cardId: string) => {
    if (selectedSecondary.includes(cardId)) {
      setSelectedSecondary(selectedSecondary.filter((id) => id !== cardId));
    } else {
      setSelectedSecondary([...selectedSecondary, cardId]);
    }
  };

  const handleApply = async () => {
    if (!selectedPrimary) return;
    await applyStoryCards(projectId, selectedPrimary, selectedSecondary);
    onClose();
  };

  return (
    <div className="story-card-picker-overlay">
      <div className="story-card-picker">
        <div className="story-card-picker-header">
          <h2>{ti('storycard.title')}</h2>
          <p>{ti('storycard.desc')}</p>
        </div>
        <div className="story-card-grid">
          {Object.entries(groupedCards).map(([category, cards]) => (
            <div key={category} style={{ gridColumn: '1 / -1' }}>
              <div style={{
                fontSize: 13, fontWeight: 600, color: CATEGORY_COLORS[category] || '#fff',
                marginBottom: 8, paddingLeft: 4,
              }}>
                {ti(CATEGORY_KEYS[category] || category)}
              </div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {cards.map((card) => {
                  const isPrimary = selectedPrimary === card.id;
                  const isSecondary = selectedSecondary.includes(card.id);
                  const isSelected = isPrimary || isSecondary;

                  return (
                    <div
                      key={card.id}
                      className={`story-card-item ${isPrimary ? 'selected' : ''}`}
                      style={{ flex: '1 1 200px', opacity: isPrimary ? 1 : isSecondary ? 0.9 : 0.85 }}
                      onClick={() => handleCardClick(card.id)}
                    >
                      <div className="card-name">{card.name}</div>
                      <div className="card-category">
                        {ti(CATEGORY_KEYS[card.category] || card.category)} · {card.id}
                      </div>
                      <div className="card-desc">{card.description}</div>
                      <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <span className={`card-difficulty difficulty-${card.difficulty}`}>
                          {card.difficulty === 'beginner' ? ti('storycard.beginner') :
                           card.difficulty === 'intermediate' ? ti('storycard.intermediate') :
                           card.difficulty === 'advanced' ? ti('storycard.advanced') : ti('storycard.expert')}
                        </span>
                        {isPrimary && <span style={{ fontSize: 10, color: '#FFD700' }}>★ {ti('storycard.primary')}</span>}
                      </div>
                      {card.reference_works && card.reference_works.length > 0 && (
                        <div style={{ fontSize: 10, color: '#6c6c80', marginTop: 4 }}>
                          {ti('storycard.reference')}: {card.reference_works.join(', ')}
                        </div>
                      )}
                      {selectedPrimary && selectedPrimary !== card.id && (
                        <button
                          className="btn btn-sm btn-ghost"
                          style={{ marginTop: 6, fontSize: 11 }}
                          onClick={(e) => { e.stopPropagation(); handleSecondaryToggle(card.id); }}
                        >
                          {isSecondary ? ti('storycard.cancel_stack') : `+ ${ti('storycard.stack')}`}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <div className="story-card-picker-footer">
          <button className="btn" onClick={onClose}>
            {ti('storycard.blank_canvas')}
          </button>
          <button
            className="btn btn-primary"
            onClick={handleApply}
            disabled={!selectedPrimary || isLoading}
          >
            {isLoading ? ti('storycard.applying') : ti('storycard.apply', { count: selectedSecondary.length + (selectedPrimary ? 1 : 0) })}
          </button>
        </div>
      </div>
    </div>
  );
};

export default StoryCardPicker;
