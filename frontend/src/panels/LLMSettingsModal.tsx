import React, { useEffect, useState } from 'react';
import * as settingsApi from '../api/settings';
import { t } from '../i18n';

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
      { key: 'model', label: t('llm.model'), type: 'select', placeholder: t('llm.select_or_input_model'), options: ['deepseek-chat', 'deepseek-reasoner'], editable: true },
      { key: 'base_url', label: t('llm.api_url'), type: 'url', placeholder: 'https://api.deepseek.com/v1' },
    ],
  },
  {
    label: 'OpenAI',
    value: 'openai',
    isLocal: false,
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-...' },
      { key: 'model', label: t('llm.model'), type: 'select', placeholder: t('llm.select_or_input_model'), options: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo', 'o1', 'o1-mini', 'o3-mini'], editable: true },
      { key: 'base_url', label: t('llm.api_url'), type: 'url', placeholder: 'https://api.openai.com/v1' },
    ],
  },
  {
    label: 'Claude (Anthropic)',
    value: 'claude',
    isLocal: false,
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-ant-...' },
      { key: 'model', label: t('llm.model'), type: 'select', placeholder: t('llm.select_or_input_model'), options: ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022'], editable: true },
      { key: 'base_url', label: t('llm.api_url'), type: 'url', placeholder: 'https://api.anthropic.com' },
    ],
  },
  {
    label: 'Gemini (Google)',
    value: 'gemini',
    isLocal: false,
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: t('llm.input_gemini_key') },
      { key: 'model', label: t('llm.model'), type: 'select', placeholder: t('llm.select_or_input_model'), options: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-2.0-pro'], editable: true },
    ],
  },
  {
    label: t('llm.ollama_local'),
    value: 'ollama',
    isLocal: true,
    fields: [
      { key: 'base_url', label: t('llm.service_url'), type: 'url', placeholder: 'http://localhost:11434' },
      { key: 'model', label: t('llm.model'), type: 'select', placeholder: t('llm.select_or_input_local_model'), options: ['llama3.1', 'llama3.2', 'qwen2.5', 'mistral', 'mixtral', 'gemma2', 'deepseek-r1'], editable: true },
    ],
  },
  {
    label: t('llm.relay_station'),
    value: 'relay',
    isLocal: false,
    fields: [
      { key: 'base_url', label: t('llm.api_url'), type: 'url', placeholder: 'https://your-relay.com/v1' },
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: t('llm.optional') },
      { key: 'model', label: t('llm.model_name'), type: 'text', placeholder: 'gpt-4o / deepseek-chat / ...' },
    ],
  },
  {
    label: t('llm.custom_openai_compat'),
    value: 'custom',
    isLocal: false,
    fields: [
      { key: 'base_url', label: t('llm.api_url'), type: 'url', placeholder: 'https://your-api.com/v1' },
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: t('llm.optional') },
      { key: 'model', label: t('llm.model_name'), type: 'text', placeholder: t('llm.input_model_name') },
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
          🤖 {t('llm.title')}
        </h2>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <span className="loading-spinner" /> {t('common.loading')}
          </div>
        ) : (
          <>
            {/* Provider Selection */}
            <div className="form-group">
              <label className="form-label">{t('llm.select_provider')}</label>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {PROVIDERS.map((p) => (
                  <button
                    key={p.value}
                    className={`btn btn-sm ${selectedProvider === p.value ? 'btn-primary' : ''}`}
                    onClick={() => setSelectedProvider(p.value)}
                    style={{ fontSize: 12 }}
                  >
                    {p.label}
                    {p.isLocal && <span style={{ fontSize: 10, opacity: 0.7 }}> {t('llm.local')}</span>}
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
                              <option value="__custom__">{t('llm.custom')}: {value}</option>
                            )}
                            {options.map((opt) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                            {field.editable && <option value="__custom__">✏️ {t('llm.custom_input')}...</option>}
                          </select>
                          {field.editable && (
                            <input
                              className="form-input"
                              type="text"
                              value={!options.includes(value) && value ? value : ''}
                              onChange={(e) => handleFieldChange(selectedProvider, field.key, e.target.value)}
                              placeholder={t('llm.input_custom_model')}
                              style={{ width: 140, display: !options.includes(value) && value ? 'block' : value === '' ? 'block' : 'none' }}
                            />
                          )}
                          {selectedProvider === 'ollama' && field.key === 'model' && (
                            <button
                              className="btn btn-sm"
                              onClick={handleRefreshOllamaModels}
                              title={t('llm.refresh_local_models')}
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
                              title={t('llm.show_hide')}
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
                {testing ? <><span className="loading-spinner" style={{ width: 12, height: 12 }} /> {t('llm.testing')}</> : `🔄 ${t('llm.test_connection')}`}
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
                    ? `✓ ${t('llm.connection_success')}: ${testResult.response || ''}`
                    : `✗ ${t('llm.connection_failed')}: ${testResult.error || t('llm.unknown_error')}`}
                </div>
              )}
            </div>

            {/* Footer */}
            <div style={{ marginTop: 20, display: 'flex', gap: 8, justifyContent: 'flex-end', borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
              <button className="btn" onClick={onClose}>{t('common.cancel')}</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? t('llm.saving') : `💾 ${t('common.save')}`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default LLMSettingsModal;
