import React, { useEffect, useState } from 'react';
import * as snapshotsApi from '../api/snapshots';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore';
import { useT } from '../i18n/useT';
import { t as ti } from '../i18n';

interface SnapshotHistoryPanelProps {
  onClose: () => void;
}

const SnapshotHistoryPanel: React.FC<SnapshotHistoryPanelProps> = ({ onClose }) => {
  const { currentProject } = useProjectStore();
  const { showToast } = useUIStore();
  const [snapshots, setSnapshots] = useState<snapshotsApi.SnapshotItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [newCheckpointLabel, setNewCheckpointLabel] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [restoring, setRestoring] = useState<string | null>(null);

  useEffect(() => {
    if (currentProject) loadSnapshots();
  }, [currentProject?.id]);

  const loadSnapshots = async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const data = await snapshotsApi.getSnapshots(currentProject.id);
      setSnapshots(data);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
    setLoading(false);
  };

  const handleCreateCheckpoint = async () => {
    if (!currentProject || !newCheckpointLabel.trim()) return;
    try {
      await snapshotsApi.createCheckpoint(currentProject.id, newCheckpointLabel.trim());
      showToast(ti('snapshot.checkpoint_saved', { label: newCheckpointLabel }));
      setNewCheckpointLabel('');
      setShowCreateForm(false);
      loadSnapshots();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleRestore = async (snapId: string, label: string) => {
    if (!currentProject) return;
    if (!confirm(ti('snapshot.confirm_restore', { label: label || ti('snapshot.this_version') }))) return;
    setRestoring(snapId);
    try {
      await snapshotsApi.restoreSnapshot(currentProject.id, snapId);
      showToast(ti('snapshot.restored_to', { label: label || ti('snapshot.snapshot') }));
      // Reload project
      const { loadProject } = useProjectStore.getState();
      await loadProject(currentProject.id);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
    setRestoring(null);
  };

  const handleDelete = async (snapId: string) => {
    if (!currentProject) return;
    if (!confirm(ti('snapshot.confirm_delete'))) return;
    try {
      await snapshotsApi.deleteSnapshot(currentProject.id, snapId);
      showToast(ti('snapshot.checkpoint_deleted'));
      loadSnapshots();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const checkpoints = snapshots.filter((s) => s.snapshot_type === 'checkpoint');
  const autoSnapshots = snapshots.filter((s) => s.snapshot_type === 'auto');

  return (
    <div className="panel" style={{ width: 340, minWidth: 340 }}>
      <div className="panel-header">
        <span>⏱ {ti('snapshot.title')}</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn btn-sm" onClick={() => setShowCreateForm(!showCreateForm)}>
            📸 {ti('snapshot.checkpoint')}
          </button>
          <button className="btn btn-sm btn-ghost" onClick={onClose}>✕</button>
        </div>
      </div>
      <div className="panel-body" style={{ padding: '8px 12px' }}>
        {/* Create checkpoint form */}
        {showCreateForm && (
          <div style={{ marginBottom: 12, padding: 8, background: 'var(--bg-primary)', borderRadius: 6 }}>
            <label className="form-label">{ti('snapshot.checkpoint_name')}</label>
            <div style={{ display: 'flex', gap: 4 }}>
              <input
                className="form-input"
                value={newCheckpointLabel}
                onChange={(e) => setNewCheckpointLabel(e.target.value)}
                placeholder={ti('snapshot.checkpoint_placeholder')}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateCheckpoint()}
                style={{ flex: 1 }}
                autoFocus
              />
              <button className="btn btn-sm btn-primary" onClick={handleCreateCheckpoint}>{ti('common.save')}</button>
            </div>
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: 'center', padding: 20, color: '#6c6c80' }}>
            <span className="loading-spinner" /> {ti('common.loading')}
          </div>
        ) : snapshots.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 20, color: '#6c6c80', fontSize: 13 }}>
            {ti('snapshot.no_snapshots')}
          </div>
        ) : (
          <>
            {/* Checkpoints */}
            {checkpoints.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#FFD700', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
                  📌 {ti('snapshot.checkpoints_permanent')}
                </div>
                {checkpoints.map((s) => (
                  <SnapshotItem
                    key={s.id}
                    snapshot={s}
                    onRestore={() => handleRestore(s.id, s.label || ti('snapshot.unnamed'))}
                    onDelete={() => handleDelete(s.id)}
                    isRestoring={restoring === s.id}
                  />
                ))}
              </div>
            )}

            {/* Auto snapshots */}
            {autoSnapshots.length > 0 && (
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#4A90D9', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
                  🕐 {ti('snapshot.auto_saves', { count: autoSnapshots.length })}
                </div>
                {autoSnapshots.map((s) => (
                  <SnapshotItem
                    key={s.id}
                    snapshot={s}
                    onRestore={() => handleRestore(s.id, s.label || ti('snapshot.auto_save', { time: formatTime(s.created_at) }))}
                    isRestoring={restoring === s.id}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

interface SnapshotItemProps {
  snapshot: snapshotsApi.SnapshotItem;
  onRestore: () => void;
  onDelete?: () => void;
  isRestoring: boolean;
}

const SnapshotItem: React.FC<SnapshotItemProps> = ({ snapshot, onRestore, onDelete, isRestoring }) => {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div className="tracking-item" style={{ position: 'relative', cursor: 'default' }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 500, color: '#e0e0e0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {snapshot.label || (snapshot.snapshot_type === 'auto' ? ti('snapshot.auto_save_short') : ti('snapshot.unnamed_checkpoint'))}
        </div>
        <div style={{ fontSize: 10, color: '#6c6c80' }}>
          {formatTime(snapshot.created_at)}
          {snapshot.block_count > 0 && ` · ${ti('snapshot.block_count', { count: snapshot.block_count })}`}
          {snapshot.word_count > 0 && ` · ${ti('snapshot.word_count', { count: snapshot.word_count })}`}
        </div>
      </div>
      <button
        className="btn btn-sm btn-ghost"
        onClick={() => setShowMenu(!showMenu)}
        style={{ fontSize: 14 }}
      >
        ⋯
      </button>

      {showMenu && (
        <>
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 10 }}
            onClick={() => setShowMenu(false)} />
          <div style={{
            position: 'absolute', right: 4, top: 28, zIndex: 11,
            background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
            borderRadius: 6, padding: 4, minWidth: 120, boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
          }}>
            <div className="menu-item" onClick={() => { setShowMenu(false); onRestore(); }}
              style={{ padding: '6px 10px', cursor: 'pointer', borderRadius: 4, fontSize: 12 }}>
              {isRestoring ? ti('snapshot.restoring') : `↩ ${ti('snapshot.restore_to_version')}`}
            </div>
            {snapshot.snapshot_type === 'checkpoint' && onDelete && (
              <div className="menu-item" onClick={() => { setShowMenu(false); onDelete(); }}
                style={{ padding: '6px 10px', cursor: 'pointer', borderRadius: 4, fontSize: 12, color: '#E74C3C' }}>
                🗑 {ti('common.delete')}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

function formatTime(isoStr: string): string {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hour = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${month}-${day} ${hour}:${min}`;
  } catch {
    return isoStr.substring(0, 16);
  }
}

export default SnapshotHistoryPanel;
