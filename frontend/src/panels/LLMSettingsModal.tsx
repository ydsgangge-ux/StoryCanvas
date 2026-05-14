import React, { useEffect, useState } from 'react';
import * as settingsApi from '../api/settings';

interface ProviderConfig {
  label: string;
  value: string;
  fields: ConfigField[];
  isLocal: boolean;
}

interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'password' | 'select' | 'url';
  placeholder: string;
  options?: string[];
  editable?: boolean;  // Allow custom input even for select type
}

const PROVIDERS: ProviderConfig[] = [
  {
    label: 'DeepSeek',
    value: 'deepseek',
    isLocal: false,
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-...' },
      { key: 'model', label: '模型', type: 'select', placeholder: '选择或输入模型', options: ['deepseek-chat', 'deepseek-reasoner'], editable: true },
      { key: 'base_url', label: 'API 地址', type: 'url', placeholder: 'https://api.deepseek.com/v1' },
    ],
  },
  {
    label: 'OpenAI',
    value: 'openai',
    isLocal: false,
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-...' },
      { key: 'model', label: '模型', type: 'select', placeholder: '选择或输入模型', options: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo', 'o1', 'o1-mini', 'o3-mini'], editable: true },
      { key: 'base_url', label: 'API 地址', type: 'url', placeholder: 'https://api.openai.com/v1' },
    ],
  },
  {
    label: 'Claude (Anthropic)',
    value: 'claude',
    isLocal: false,
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-ant-...' },
      { key: 'model', label: '模型', type: 'select', placeholder: '选择或输入模型', options: ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022'], editable: true },
      { key: 'base_url', label: 'API 地址', type: 'url', placeholder: 'https://api.anthropic.com' },
    ],
  },
  {
    label: 'Gemini (Google)',
    value: 'gemini',
    isLocal: false,
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: '输入 Gemini API Key' },
      { key: 'model', label: '模型', type: 'select', placeholder: '选择或输入模型', options: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-2.0-pro'], editable: true },
    ],
  },
  {
    label: 'Ollama (本地)',
    value: 'ollama',
    isLocal: true,
    fields: [
      { key: 'base_url', label: '服务地址', type: 'url', placeholder: 'http://localhost:11434' },
      { key: 'model', label: '模型', type: 'select', placeholder: '选择或输入本地模型', options: ['llama3.1', 'llama3.2', 'qwen2.5', 'mistral', 'mixtral', 'gemma2', 'deepseek-r1'], editable: true },
    ],
  },
  {
    label: '自定义 (OpenAI兼容)',
    value: 'custom',
    isLocal: false,
    fields: [
      { key: 'base_url', label: 'API 地址', type: 'url', placeholder: 'https://your-api.com/v1' },
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: '可选' },
      { key: 'model', label: '模型名称', type: 'text', placeholder: '输入模型名称' },
    ],
  },
];

interface LLMSettingsModalProps {
  onClose: () => void;
  onSave: () => void;
}

const LLMSettingsModal: React.FC<LLMSettingsModalProps> = ({ onClose, onSave }) => {
  const [selectedProvider, setSelectedProvider] = useState('deepseek');
  const [configs, setConfigs] = useState<Record<string, Record<string, string>>>({});
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; response?: string; error?: string } | null>(null);
  const [ollamaLoading, setOllamaLoading] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await settingsApi.getSettings();
      setSelectedProvider(data.provider || 'deepseek');

      // Merge saved configs with default values
      const merged: Record<string, Record<string, string>> = {};
      for (const p of PROVIDERS) {
        merged[p.value] = {
          ...getDefaultConfig(p.value),
          ...(data.configs?.[p.value] || {}),
        };
      }
      setConfigs(merged);

      // Load Ollama models if available
      try {
        const models = await settingsApi.getOllamaModels();
        if (models.length > 0) {
          setOllamaModels(models);
        }
      } catch { /* ignore */ }
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
    setLoading(false);
  };

  const getDefaultConfig = (provider: string): Record<string, string> => {
    const p = PROVIDERS.find((x) => x.value === provider);
    if (!p) return {};
    const cfg: Record<string, string> = {};
    for (const f of p.fields) {
      cfg[f.key] = '';
    }
    // Set default URLs
    if (provider === 'deepseek') cfg.base_url = 'https://api.deepseek.com/v1';
    if (provider === 'openai') cfg.base_url = 'https://api.openai.com/v1';
    if (provider === 'claude') cfg.base_url = 'https://api.anthropic.com';
    if (provider === 'ollama') cfg.base_url = 'http://localhost:11434';
    return cfg;
  };

  const handleFieldChange = (provider: string, key: string, value: string) => {
    setConfigs((prev) => ({
      ...prev,
      [provider]: { ...(prev[provider] || {}), [key]: value },
    }));
  };

  const handleRefreshOllamaModels = async () => {
    setOllamaLoading(true);
    try {
      const models = await settingsApi.getOllamaModels();
      setOllamaModels(models);
    } catch { /* ignore */ }
    setOllamaLoading(false);
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await settingsApi.testConnection(selectedProvider, {
        [selectedProvider]: configs[selectedProvider] || {},
      });
      setTestResult(result);
    } catch (e: any) {
      setTestResult({ success: false, error: e.message });
    }
    setTesting(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await settingsApi.saveSettings(selectedProvider, configs);
      onSave();
      onClose();
    } catch (e: any) {
      setTestResult({ success: false, error: e.message });
    }
    setSaving(false);
  };

  const currentProvider = PROVIDERS.find((p) => p.value === selectedProvider);
  const currentConfig = configs[selectedProvider] || {};

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ width: 560 }}>
        <h2 style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
          🤖 大模型设置
        </h2>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <span className="loading-spinner" /> 加载中...
          </div>
        ) : (
          <>
            {/* Provider Selection */}
            <div className="form-group">
              <label className="form-label">选择提供商</label>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {PROVIDERS.map((p) => (
                  <button
                    key={p.value}
                    className={`btn btn-sm ${selectedProvider === p.value ? 'btn-primary' : ''}`}
                    onClick={() => setSelectedProvider(p.value)}
                    style={{ fontSize: 12 }}
                  >
                    {p.label}
                    {p.isLocal && <span style={{ fontSize: 10, opacity: 0.7 }}> 本地</span>}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ height: 1, background: 'var(--border-color)', margin: '12px 0' }} />

            {/* Config Fields */}
            {currentProvider && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {currentProvider.fields.map((field) => {
                  const value = currentConfig[field.key] || '';
                  const isPassword = field.type === 'password';
                  const isSelect = field.type === 'select';
                  const isUrl = field.type === 'url';

                  // For Ollama, dynamically add fetched models to options
                  let options = field.options || [];
                  if (selectedProvider === 'ollama' && field.key === 'model' && ollamaModels.length > 0) {
                    options = [...new Set([...ollamaModels, ...options])];
                  }

                  return (
                    <div className="form-group" key={field.key} style={{ marginBottom: 0 }}>
                      <label className="form-label">{field.label}</label>
                      {isSelect && options.length > 0 ? (
                        <div style={{ display: 'flex', gap: 4 }}>
                          <select
                            className="form-select"
                            value={options.includes(value) ? value : '__custom__'}
                            onChange={(e) => {
                              if (e.target.value !== '__custom__') {
                                handleFieldChange(selectedProvider, field.key, e.target.value);
                              }
                            }}
                            style={{ flex: 1 }}
                          >
                            {value && !options.includes(value) && (
                              <option value="__custom__">自定义: {value}</option>
                            )}
                            {options.map((opt) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                            {field.editable && <option value="__custom__">✏️ 自定义输入...</option>}
                          </select>
                          {field.editable && (
                            <input
                              className="form-input"
                              type="text"
                              value={!options.includes(value) && value ? value : ''}
                              onChange={(e) => handleFieldChange(selectedProvider, field.key, e.target.value)}
                              placeholder="输入自定义模型名"
                              style={{ width: 140, display: !options.includes(value) && value ? 'block' : value === '' ? 'block' : 'none' }}
                            />
                          )}
                          {selectedProvider === 'ollama' && field.key === 'model' && (
                            <button
                              className="btn btn-sm"
                              onClick={handleRefreshOllamaModels}
                              title="刷新本地模型列表"
                            >
                              {ollamaLoading ? <span className="loading-spinner" style={{ width: 12, height: 12 }} /> : '⟳'}
                            </button>
                          )}
                        </div>
                      ) : (
                        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                          <input
                            className="form-input"
                            type={isPassword ? (isSelect ? 'text' : 'password') : 'text'}
                            value={value}
                            onChange={(e) => handleFieldChange(selectedProvider, field.key, e.target.value)}
                            placeholder={field.placeholder}
                            style={{ flex: 1 }}
                          />
                          {isPassword && value && (
                            <button
                              className="btn btn-sm btn-ghost"
                              onClick={() => {
                                const el = document.querySelector(`[data-field="${field.key}"]`) as HTMLInputElement;
                                if (el) el.type = el.type === 'password' ? 'text' : 'password';
                              }}
                              title="显示/隐藏"
                            >
                              👁
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Test Connection */}
            <div style={{ marginTop: 16, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                className="btn"
                onClick={handleTestConnection}
                disabled={testing}
              >
                {testing ? <><span className="loading-spinner" style={{ width: 12, height: 12 }} /> 测试中...</> : '🔄 测试连接'}
              </button>

              {testResult && (
                <div style={{
                  fontSize: 12,
                  padding: '6px 10px',
                  borderRadius: 6,
                  background: testResult.success ? 'rgba(80, 200, 120, 0.15)' : 'rgba(231, 76, 60, 0.15)',
                  color: testResult.success ? '#50C878' : '#E74C3C',
                  flex: 1,
                  maxWidth: '100%',
                  wordBreak: 'break-all',
                }}>
                  {testResult.success
                    ? `✓ 连接成功: ${testResult.response || ''}`
                    : `✗ 连接失败: ${testResult.error || '未知错误'}`}
                </div>
              )}
            </div>

            {/* Footer */}
            <div style={{ marginTop: 20, display: 'flex', gap: 8, justifyContent: 'flex-end', borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
              <button className="btn" onClick={onClose}>取消</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? '保存中...' : '💾 保存'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default LLMSettingsModal;
