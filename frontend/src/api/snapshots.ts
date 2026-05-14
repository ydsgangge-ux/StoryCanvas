export interface SnapshotItem {
  id: string;
  snapshot_type: string;
  label: string | null;
  created_at: string;
  word_count: number;
  block_count: number;
}

export async function getSnapshots(projectId: string, type?: string): Promise<SnapshotItem[]> {
  let url = `/api/projects/${projectId}/snapshots`;
  if (type) url += `?snapshot_type=${type}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('获取快照列表失败');
  return res.json();
}

export async function createCheckpoint(projectId: string, label: string): Promise<any> {
  const res = await fetch(`/api/projects/${projectId}/snapshots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label }),
  });
  if (!res.ok) throw new Error('创建检查点失败');
  return res.json();
}

export async function restoreSnapshot(projectId: string, snapshotId: string): Promise<any> {
  const res = await fetch(`/api/projects/${projectId}/snapshots/${snapshotId}/restore`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('回滚失败');
  return res.json();
}

export async function deleteSnapshot(projectId: string, snapshotId: string): Promise<void> {
  const res = await fetch(`/api/projects/${projectId}/snapshots/${snapshotId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('删除快照失败');
}

export async function checkIntegrity(projectId: string): Promise<any> {
  const res = await fetch(`/api/projects/${projectId}/integrity`);
  return res.json();
}
