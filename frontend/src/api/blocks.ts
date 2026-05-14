import { BlockData, BlockType, ConnectionData } from '../types/blocks';

const API_BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '请求失败');
  }
  return res.json();
}

// Projects
export async function listProjects(): Promise<any[]> {
  return request('/projects');
}

export async function createProject(title: string, genre?: string, chapter_count?: number): Promise<any> {
  return request('/projects', {
    method: 'POST',
    body: JSON.stringify({ title, genre, chapter_count }),
  });
}

export async function getProject(id: string): Promise<any> {
  return request(`/projects/${id}`);
}

export async function deleteProject(id: string): Promise<void> {
  await request(`/projects/${id}`, { method: 'DELETE' });
}

// Blocks
export async function getBlocks(projectId: string, type?: string): Promise<BlockData[]> {
  let url = `/projects/${projectId}/blocks`;
  if (type) url += `?type=${type}`;
  return request(url);
}

export async function createBlock(projectId: string, data: Partial<BlockData>): Promise<any> {
  return request(`/projects/${projectId}/blocks`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateBlock(projectId: string, blockId: string, data: Partial<BlockData>): Promise<void> {
  await request(`/projects/${projectId}/blocks/${blockId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteBlock(projectId: string, blockId: string): Promise<void> {
  await request(`/projects/${projectId}/blocks/${blockId}`, { method: 'DELETE' });
}

export async function batchCreateBlocks(projectId: string, blocks: Partial<BlockData>[]): Promise<any> {
  return request(`/projects/${projectId}/blocks/batch`, {
    method: 'POST',
    body: JSON.stringify(blocks),
  });
}

export async function batchMoveBlocks(projectId: string, moves: { id: string; canvas_x: number; canvas_y: number }[]): Promise<void> {
  await request(`/projects/${projectId}/blocks/batch-move`, {
    method: 'PUT',
    body: JSON.stringify(moves),
  });
}

// Connections
export async function getConnections(projectId: string): Promise<ConnectionData[]> {
  return request(`/projects/${projectId}/connections`);
}

export async function createConnection(projectId: string, data: { from_block: string; to_block: string; conn_type: string; label?: string; chapter_hint?: string }): Promise<any> {
  return request(`/projects/${projectId}/connections`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deleteConnection(projectId: string, connId: string): Promise<void> {
  await request(`/projects/${projectId}/connections/${connId}`, { method: 'DELETE' });
}

// Canvas layout
export async function getCanvasLayout(projectId: string): Promise<any> {
  return request(`/projects/${projectId}/canvas-layout`);
}

export async function saveCanvasLayout(projectId: string, layout: any): Promise<void> {
  await request(`/projects/${projectId}/canvas-layout`, {
    method: 'PUT',
    body: JSON.stringify(layout),
  });
}

// Progress
export async function getProgress(projectId: string): Promise<any> {
  return request(`/projects/${projectId}/progress`);
}

// Story cards
export async function getStoryCards(): Promise<any[]> {
  return request('/story-cards');
}

export async function applyStoryCards(projectId: string, primary: string, secondary: string[]): Promise<any> {
  return request(`/projects/${projectId}/apply-story-cards`, {
    method: 'POST',
    body: JSON.stringify({ primary, secondary }),
  });
}
