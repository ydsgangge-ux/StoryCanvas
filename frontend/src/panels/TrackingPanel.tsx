import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore'
import { useT } from '../i18n/useT';;
import { BLOCK_LABELS } from '../types/blocks';

interface TrackingItem {
  id: string;
  type: string;
  title: string;
  status?: string;
  detail?: string;
}

const TrackingPanel: React.FC = () => {
  const { t } = useT();
  const { currentProject } = useProjectStore();
  const { showToast } = useUIStore();
  const [activeTab, setActiveTab] = useState<'foreshadows' | 'character-arcs' | 'relationship-map' | 'timeline-view' | 'information-check'>('foreshadows');
  const [items, setItems] = useState<TrackingItem[]>([]);
  const [loading, setLoading] = useState(false);

  const tabs = [
    { key: 'foreshadows', label: '铺垫追踪', icon: '◈' },
    { key: 'character-arcs', label: '角色弧线', icon: 'C' },
    { key: 'relationship-map', label: '关系网络', icon: '❤' },
    { key: 'timeline-view', label: '时间线', icon: 'T' },
    { key: 'information-check', label: '信息边界', icon: 'Ib' },
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
      const data = await res.json();
      if (activeTab === 'information-check') {
        setItems((data.violations || []).map((v: any) => ({
          id: `${v.chapter_num}-${v.block_id || ''}`,
          type: '违规',
          title: v.description || `第${v.chapter_num}章信息边界违规`,
          status: 'warning',
          detail: v.detail || '',
        })));
      } else if (activeTab === 'timeline-view') {
        setItems((data || []).map((t: any) => ({
          id: t.id,
          type: t.type || '主线',
          title: t.name || '未命名时间线',
          status: `${(t.scenes || []).length}个场景`,
          detail: (t.scenes || []).map((s: any) => s.title).join(', '),
        })));
      } else if (activeTab === 'relationship-map') {
        setItems((data || []).map((r: any) => ({
          id: r.id,
          type: r.type || '关系',
          title: `${r.party_a} ↔ ${r.party_b}`,
          status: `强度: ${r.intensity || 0}`,
          detail: r.type || '',
        })));
      } else {
        setItems((data || []).map((item: any) => ({
          id: item.id,
          type: item.type || item.arc_type || '',
          title: item.name || item.title || '未命名',
          status: item.status || item.arc_type || '',
          detail: item.detail || '',
        })));
      }
    } catch (e) {
      setItems([]);
    }
    setLoading(false);
  };

  return (
    <div className="panel" style={{ width: 320, minWidth: 280 }}>
      <div className="panel-header">
        <span>📊 叙事追踪</span>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        {/* Tab bar */}
        <div style={{ display: 'flex', overflowX: 'auto', borderBottom: '1px solid var(--border-color)' }}>
          {tabs.map(t => (
            <button
              key={t.key}
              className={`btn btn-sm ${activeTab === t.key ? 'btn-primary' : 'btn-ghost'}`}
              style={{ flex: '0 0 auto', padding: '6px 10px', fontSize: 11, borderRadius: 0 }}
              onClick={() => setActiveTab(t.key)}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ padding: 12, maxHeight: 400, overflowY: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', color: '#6c6c80', padding: 20 }}>加载中...</div>
          ) : items.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#6c6c80', padding: 20 }}>
              暂无{tabs.find(t => t.key === activeTab)?.label || ''}数据
            </div>
          ) : (
            items.map(item => (
              <div
                key={item.id}
                style={{
                  padding: '8px 10px',
                  marginBottom: 6,
                  borderRadius: 6,
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{item.title}</span>
                  {item.status && (
                    <span style={{
                      fontSize: 10,
                      padding: '2px 6px',
                      borderRadius: 4,
                      background: item.status === 'warning' ? '#E74C3C' : item.status === 'resolved' ? '#50C878' : 'var(--bg-secondary)',
                      color: item.status === 'warning' ? '#fff' : item.status === 'resolved' ? '#fff' : 'var(--text-secondary)',
                    }}>
                      {item.status}
                    </span>
                  )}
                </div>
                {item.type && (
                  <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{item.type}</div>
                )}
                {item.detail && (
                  <div style={{ fontSize: 11, color: '#6c6c80', marginTop: 4 }}>{item.detail}</div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default TrackingPanel;
