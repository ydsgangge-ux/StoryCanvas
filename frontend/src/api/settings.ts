export interface LLMConfig {
  provider: string;
  configs: Record<string, Record<string, string>>;
  available_models?: Record<string, string[]>;
  image_provider?: string;
  image_configs?: Record<string, Record<string, string>>;
}

export async function getSettings(): Promise<LLMConfig> {
  const res = await fetch('/api/settings');
  if (!res.ok) throw new Error('获取设置失败');
  return res.json();
}

export async function saveSettings(provider: string, configs: Record<string, Record<string, string>>, imageProvider?: string, imageConfigs?: Record<string, Record<string, string>>): Promise<void> {
  const body: any = { provider, configs };
  if (imageProvider !== undefined) body.image_provider = imageProvider;
  if (imageConfigs !== undefined) body.image_configs = imageConfigs;
  const res = await fetch('/api/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('保存设置失败');
}

export async function getOllamaModels(): Promise<string[]> {
  const res = await fetch('/api/settings/ollama-models');
  if (!res.ok) return [];
  const data = await res.json();
  return data.models || [];
}

export async function testConnection(provider: string, configs: Record<string, Record<string, string>>): Promise<{ success: boolean; response?: string; error?: string }> {
  const res = await fetch('/api/settings/test-connection', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, configs }),
  });
  return res.json();
}
