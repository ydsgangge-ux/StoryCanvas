import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore';
import { useT } from '../i18n/useT';
import { t as ti } from '../i18n';

interface TrackingItem {
  id: string;
  type: string;
  title: string;
  status?: string;
  detail?: string;
  extra?: Record<string, string>;
}

const STATUS_COLORS: Record<string, string> = {
  open: '#F39C12',
  planted: '#4A90D9',
  resolved: '#50C878',
  expired: '#E74C3C',
  warning: '#E74C3C',
  critical: '#E74C3C',
};

const TrackingPanel: React.FC = () => {
  const { t } = useT();
  const { currentProject } = useProjectStore();
  const { showToast } = useUIStore();
  const [activeTab, setActiveTab] = useState<'foreshadows' | 'character-arcs' | 'relationship-map' | 'timeline-view' | 'information-check'>('foreshadows');
  const [items, setItems] = useState<TrackingItem[]>([]);
  const [loading, setLoading] = useState(false);

  const tabs = [
    { key: 'foreshadows', labelKey: 'tracking.foreshadows', icon: '◈' },
    { key: 'character-arcs', labelKey: 'tracking.character_arcs', icon: '↗' },
    { key: 'relationship-map', labelKey: 'tracking.relationship_map', icon: '⟷' },
    { key: 'timeline-view', labelKey: 'tracking.timeline_view', icon: '⏤' },
    { key: 'information-check', labelKey: 'tracking.information_check', icon: '⚠' },
  ] as const;

  useEffect(() => {
    if (currentProject) {
      fetchTrackingData();
    }
  }, [currentProject, activeTab]);

  const fetchTrackingData = async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/projects/${currentProject.id}/${activeTab}`);
      if (!res.ok) {
        setItems([]);
        setLoading(false);
        return;
      }
      const data = await res.json();

      if (activeTab === 'foreshadows') {
        const raw = Array.isArray(data) ? data : [];
        setItems(raw.map((item: any) => ({
          id: item.id,
          type: item.type === 'HOOK' ? t('tracking.hook') : t('tracking.foreshadow'),
          title: item.title || t('tracking.unnamed'),
          status: item.status || 'open',
          detail: item.description || '',
          extra: {
            ...(item.urgency ? { [t('tracking.urgency')]: item.urgency } : {}),
            ...(item.plant_chapter ? { [t('tracking.plant_chapter')]: String(item.plant_chapter) } : {}),
            ...(item.payoff_chapter ? { [t('tracking.payoff_chapter')]: String(item.payoff_chapter) } : {}),
          },
        })));
      } else if (activeTab === 'character-arcs') {
        const raw = Array.isArray(data) ? data : [];
        setItems(raw.map((item: any) => ({
          id: item.id,
          type: item.arc_type || t('tracking.unset'),
          title: item.name || t('tracking.unnamed'),
          status: item.arc_type || '',
          detail: [
            item.start_state ? `${t('tracking.start_state')}: ${item.start_state}` : '',
            item.end_state ? `${t('tracking.end_state')}: ${item.end_state}` : '',
          ].filter(Boolean).join(' → '),
          extra: item.keystone_moments ? { [t('tracking.keystone')]: item.keystone_moments } : {},
        })));
      } else if (activeTab === 'relationship-map') {
        const raw = Array.isArray(data) ? data : [];
        setItems(raw.map((r: any) => ({
          id: r.id,
          type: r.type || t('tracking.relation'),
          title: `${r.party_a || '?'} ↔ ${r.party_b || '?'}`,
          status: r.intensity ? t('tracking.intensity', { value: r.intensity }) : '',
          detail: [r.dynamic, r.evolution].filter(Boolean).join(' | '),
        })));
      } else if (activeTab === 'timeline-view') {
        const raw = Array.isArray(data) ? data : [];
        setItems(raw.map((tl: any) => ({
          id: tl.id,
          type: tl.type === 'main' ? t('tracking.mainline') : (tl.type || t('tracking.subline')),
          title: tl.name || t('tracking.unnamed_timeline'),
          status: t('tracking.scene_count', { count: (tl.scenes || []).length }),
          detail: (tl.scenes || []).map((s: any) => s.title || `Ch.${s.chapter_pos || '?'}`).join(', '),
        })));
      } else if (activeTab === 'information-check') {
        const violations = data.violations || [];
        setItems(violations.map((v: any) => ({
          id: `${v.chapter_num}-${v.character || ''}-${v.info || ''}`.replace(/\s/g, '_'),
          type: v.character_name ? `${t('tracking.character')}: ${v.character_name}` : t('tracking.violation'),
          title: v.sentence ? `「${v.sentence.substring(0, 40)}${v.sentence.length > 40 ? '...' : ''}」` : (v.info || t('tracking.chapter_violation', { chapter: v.chapter_num })),
          status: v.severity || 'warning',
          detail: v.info ? `${t('tracking.sensitive_info')}: ${v.info}` : '',
          extra: { [t('tracking.chapter')]: String(v.chapter_num) },
        })));
      }
    } catch (e) {
      setItems([]);
    }
    setLoading(false);
  };

  const getStatusColor = (status?: string) => {
    if (!status) return 'var(--bg-secondary)';
    return STATUS_COLORS[status] || 'var(--bg-secondary)';
  };

  const getStatusLabel = (status?: string) => {
    if (!status) return '';
    const key = `tracking.status_${status}`;
    const translated = ti(key);
    return translated === key ? status : translated;
  };

  return (
    <div className="panel" style={{ width: 340, minWidth: 280 }}>
      <div className="panel-header">
        <span>📊 {t('tracking.title')}</span>
        <button className="btn btn-sm btn-ghost" onClick={fetchTrackingData} disabled={loading} title={t('tracking.refresh')}>
          ↻
        </button>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        <div style={{ display: 'flex', overflowX: 'auto', borderBottom: '1px solid var(--border-color)' }}>
          {tabs.map(tabItem => (
            <button
              key={tabItem.key}
              className={`btn btn-sm ${activeTab === tabItem.key ? 'btn-primary' : 'btn-ghost'}`}
              style={{ flex: '0 0 auto', padding: '6px 10px', fontSize: 11, borderRadius: 0, whiteSpace: 'nowrap' }}
              onClick={() => setActiveTab(tabItem.key)}
            >
              {tabItem.icon} {t(tabItem.labelKey)}
            </button>
          ))}
        </div>

        <div style={{ padding: 12, maxHeight: 500, overflowY: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', color: '#6c6c80', padding: 20 }}>
              <span className="loading-spinner" /> {t('common.loading')}
            </div>
          ) : items.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#6c6c80', padding: 20 }}>
              {t('tracking.no_data', { tab: t(tabs.find(tabItem => tabItem.key === activeTab)?.labelKey || '') })}
            </div>
          ) : (
            <>
              <div style={{ fontSize: 11, color: '#888', marginBottom: 8 }}>
                {t('tracking.total_items', { count: items.length })}
              </div>
              {items.map(item => (
                <div
                  key={item.id}
                  style={{
                    padding: '8px 10px',
                    marginBottom: 6,
                    borderRadius: 6,
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderLeft: `3px solid ${getStatusColor(item.status)}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.title}</span>
                    {item.status && (
                      <span style={{
                        fontSize: 10,
                        padding: '2px 6px',
                        borderRadius: 4,
                        background: getStatusColor(item.status),
                        color: '#fff',
                        flexShrink: 0,
                        marginLeft: 6,
                      }}>
                        {getStatusLabel(item.status)}
                      </span>
                    )}
                  </div>
                  {item.type && (
                    <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{item.type}</div>
                  )}
                  {item.detail && (
                    <div style={{ fontSize: 11, color: '#6c6c80', marginTop: 4, lineHeight: 1.4 }}>{item.detail}</div>
                  )}
                  {item.extra && Object.keys(item.extra).length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                      {Object.entries(item.extra).map(([k, v]) => (
                        <span key={k} style={{ fontSize: 10, padding: '1px 5px', borderRadius: 3, background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                          {k}: {v}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrackingPanel;
